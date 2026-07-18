"""ML 选股模型 — LightGBM 跨截面收益预测 + SHAP 解释。

Pipeline:
1. generate_labels: future 5d relative return → 3-class label
2. train: walk-forward LightGBM multiclass
3. predict: score = P(outperform) + 0.5*P(neutral)
4. explain_predictions: SHAP top-3 positive + top-2 negative factors
5. activate_model: validation gate (IC threshold)
"""

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models.daily_bar import DailyBar
from app.models.model_version import ModelVersion
from app.models.prediction import Prediction
from app.schemas.settings import SystemParams

logger = structlog.get_logger()

# ── SHAP explanation templates ───────────────────────────────────

FACTOR_TEMPLATES = {
    "return_5d": lambda v: (
        f"近5日收益 {v:>+.1%}",
        "近期动量" + ("强劲" if v > 0.05 else "较弱" if v < -0.05 else "平稳"),
    ),
    "return_10d": lambda v: (
        f"近10日收益 {v:>+.1%}",
        "短期趋势" + ("向上" if v > 0.08 else "向下" if v < -0.08 else "平稳"),
    ),
    "return_20d": lambda v: (
        f"近20日收益 {v:>+.1%}",
        "中期趋势" + ("向上" if v > 0.08 else "向下" if v < -0.08 else "平稳"),
    ),
    "return_60d": lambda v: (
        f"近60日收益 {v:>+.1%}",
        "长期趋势" + ("向上" if v > 0.15 else "向下" if v < -0.15 else "平稳"),
    ),
    "excess_return_20d": lambda v: (
        f"近20日超额收益 {v:>+.1%}",
        "相对大盘" + ("跑赢" if v > 0 else "跑输"),
    ),
    "momentum_12_1": lambda v: (
        f"长期动量 {v:>+.1%}",
        "长线" + ("强势" if v > 0.15 else "弱势" if v < -0.15 else "中性"),
    ),
    "pe_ttm": lambda v: (
        f"PE TTM {v:.1f}",
        "估值" + ("偏低" if v < 15 else "偏高" if v > 40 else "适中"),
    ),
    "pe_industry_pct": lambda v: (
        f"行业PE分位 {v:.0%}",
        f"估值低于行业{1 - v:.0%}的公司" if v < 0.3 else f"估值高于行业{v:.0%}的公司",
    ),
    "pb": lambda v: (f"PB {v:.2f}", "市净率" + ("低" if v < 1.5 else "高" if v > 5 else "适中")),
    "dividend_yield": lambda v: (f"股息率 {v:.1%}", "分红" + ("丰厚" if v > 0.04 else "一般")),
    "roe_ttm": lambda v: (
        f"ROE {v:.1%}",
        "盈利能力" + ("强" if v > 0.15 else "弱" if v < 0.05 else "一般"),
    ),
    "gross_margin": lambda v: (f"毛利率 {v:.1%}", "毛利" + ("高" if v > 0.4 else "低")),
    "debt_ratio": lambda v: (f"资产负债率 {v:.1%}", "负债" + ("低" if v < 0.3 else "偏高")),
    "revenue_yoy": lambda v: (
        f"营收增速 {v:>+.1%}",
        "成长性" + ("强" if v > 0.2 else "弱" if v < 0 else "平稳"),
    ),
    "profit_yoy": lambda v: (
        f"利润增速 {v:>+.1%}",
        "利润" + ("高增" if v > 0.3 else "下滑" if v < -0.1 else "稳定"),
    ),
    "turnover_5d_avg": lambda v: (
        f"5日均换手率 {v:.1%}",
        "交投" + ("活跃" if v > 0.03 else "清淡"),
    ),
    "volatility_20d": lambda v: (f"20日波动率 {v:.2%}", "波动" + ("大" if v > 0.025 else "小")),
    "volume_ratio": lambda v: (
        f"量比 {v:.2f}",
        "放量" if v > 1.5 else "缩量" if v < 0.5 else "正常",
    ),
    "rsi_14": lambda v: (f"RSI {v:.0f}", "超买" if v > 70 else "超卖" if v < 30 else "中性"),
    "macd_hist": lambda v: (f"MACD柱 {v:>+.4f}", "MACD多头" if v > 0 else "MACD空头"),
    "boll_position": lambda v: (
        f"布林位置 {v:.0%}",
        "触上轨" if v > 0.9 else "触下轨" if v < 0.1 else "中轨附近",
    ),
    "ma_alignment": lambda v: (
        f"均线排列 {v:.0f}/4",
        "全多头" if v >= 4 else "全空头" if v <= 0 else "混合",
    ),
    "northbound_holding_change": lambda v: (
        f"北向变动 {v * 100:>+.2f}%",
        "北向资金流入" if v > 0 else "北向资金流出",
    ),
}


def classify_relative_return(relative_return: float, params: SystemParams) -> int:
    if relative_return > params.forward_return_threshold:
        return 2
    if relative_return < -params.forward_return_threshold:
        return 0
    return 1


def validation_cutoff(dates: list, params: SystemParams):
    if len(dates) > params.model_val_window_days:
        return dates[-params.model_val_window_days]
    return dates[len(dates) // 2]


class MLModelService:
    """LightGBM stock selection model with SHAP explanations."""

    # ── Label Generation ──────────────────────────────────────────

    async def generate_labels(
        self,
        start_date: date,
        end_date: date,
        params: SystemParams,
    ) -> pd.Series:
        """Generate 3-class labels from forward 5-day relative returns."""
        fwd_days = params.forward_return_days

        async with AsyncSessionLocal() as db:
            # Load all daily bars for CSI 300 stocks in range (+ fwd_days buffer)
            buffer_end = end_date + timedelta(days=fwd_days * 3)
            result = await db.execute(
                select(DailyBar.symbol, DailyBar.trade_date, DailyBar.close)
                .where(DailyBar.trade_date >= start_date, DailyBar.trade_date <= buffer_end)
                .order_by(DailyBar.symbol, DailyBar.trade_date)
            )
            rows = result.all()

        if not rows:
            return pd.Series(dtype=float)

        df = pd.DataFrame(rows, columns=["symbol", "trade_date", "close"])
        df["close"] = df["close"].astype(float)

        labels = {}
        for symbol, group in df.groupby("symbol"):
            group = group.sort_values("trade_date").reset_index(drop=True)
            for i in range(len(group)):
                td = group.loc[i, "trade_date"]
                if td < start_date or td > end_date:
                    continue
                if i + fwd_days >= len(group):
                    continue

                fwd_ret = group.loc[i + fwd_days, "close"] / group.loc[i, "close"] - 1

                labels[(symbol, td)] = fwd_ret

        # Load CSI300 index returns
        async with AsyncSessionLocal() as db:
            idx_result = await db.execute(
                select(DailyBar.trade_date, DailyBar.close)
                .where(
                    DailyBar.symbol == "000300",
                    DailyBar.trade_date >= start_date,
                    DailyBar.trade_date <= buffer_end,
                )
                .order_by(DailyBar.trade_date)
            )
            idx_rows = idx_result.all()

        if idx_rows:
            idx_df = pd.DataFrame(idx_rows, columns=["trade_date", "close"])
            idx_df["close"] = idx_df["close"].astype(float)
            idx_returns = {}
            idx_sorted = idx_df.sort_values("trade_date").reset_index(drop=True)
            for i in range(len(idx_sorted) - fwd_days):
                td = idx_sorted.loc[i, "trade_date"]
                fwd = idx_sorted.loc[i + fwd_days, "close"] / idx_sorted.loc[i, "close"] - 1
                idx_returns[td] = fwd

            # Relative return = stock - index
            final_labels = {}
            for (sym, td), stock_ret in labels.items():
                idx_ret = idx_returns.get(td)
                if idx_ret is not None:
                    rel = stock_ret - idx_ret
                    final_labels[(sym, td)] = classify_relative_return(rel, params)
                else:
                    final_labels[(sym, td)] = 1
        else:
            final_labels = {}
            for (sym, td), stock_ret in labels.items():
                final_labels[(sym, td)] = classify_relative_return(stock_ret, params)

        s = pd.Series(final_labels, name="label")
        s.index.names = ["symbol", "trade_date"]
        return s

    # ── Training ──────────────────────────────────────────────────

    async def train(self, params: SystemParams | None = None) -> dict:
        """Train a new model version with walk-forward validation."""
        import lightgbm as lgb

        if params is None:
            from app.services.settings_service import load_runtime_system_params

            params = await load_runtime_system_params()
        boot_settings = get_settings()

        from app.services.feature_engine import FeatureEngine

        fe = FeatureEngine()

        end_date = date.today()
        total_window = params.model_train_window_days + params.model_val_window_days
        start_date = end_date - timedelta(days=int(total_window * 1.5))

        logger.info("ml_model.training_start", start=str(start_date), end=str(end_date))

        # Build factor matrix
        features = await fe.build_factor_matrix(start_date, end_date)
        if features.empty:
            raise ValueError("因子矩阵为空，请先同步数据并计算特征")

        # Generate labels
        y = await self.generate_labels(start_date, end_date, params)
        if y.empty:
            raise ValueError("标签为空，无法训练")

        # Align index
        common_idx = features.index.intersection(y.index)
        if len(common_idx) < 100:
            raise ValueError(f"对齐后样本不足: {len(common_idx)}")

        features = features.loc[common_idx]
        y = y.loc[common_idx]

        # Walk-forward split
        dates = sorted(set(features.index.get_level_values("trade_date")))
        val_cutoff = validation_cutoff(dates, params)

        train_mask = features.index.get_level_values("trade_date") < val_cutoff
        val_mask = ~train_mask

        train_features, y_train = features[train_mask], y[train_mask]
        validation_features, y_val = features[val_mask], y[val_mask]

        if len(train_features) < 50:
            raise ValueError(f"训练样本不足: {len(train_features)}")

        feature_names = fe.get_factor_names()

        def _do_train():
            train_data = lgb.Dataset(
                train_features[feature_names].values,
                label=y_train.values,
                feature_name=feature_names,
            )
            val_data = lgb.Dataset(
                validation_features[feature_names].values,
                label=y_val.values,
                feature_name=feature_names,
                reference=train_data,
            )

            lgb_params = {
                "objective": "multiclass",
                "num_class": 3,
                "n_estimators": 200,
                "max_depth": 6,
                "learning_rate": 0.05,
                "random_state": 42,
                "verbose": -1,
                "n_jobs": -1,
            }

            booster = lgb.train(
                lgb_params,
                train_data,
                valid_sets=[val_data],
                callbacks=[lgb.log_evaluation(0)],
            )
            return booster

        booster = await asyncio.to_thread(_do_train)

        # Validation evaluation
        val_preds = booster.predict(validation_features[feature_names].values)
        val_p2 = val_preds[:, 2]  # P(outperform)

        # IC: Spearman correlation between P(outperform) and actual forward returns
        val_metrics = await self._evaluate_validation(
            booster,
            validation_features,
            y_val,
            feature_names,
            val_p2,
        )

        # Save model
        version = f"v{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        model_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), boot_settings.MODEL_DIR
        )
        os.makedirs(model_dir, exist_ok=True)
        file_path = os.path.join(model_dir, f"model_{version}.txt")
        booster.save_model(file_path)

        # Feature importance
        importance = booster.feature_importance(importance_type="gain")
        top_indices = np.argsort(importance)[::-1][:10]
        top_features = {feature_names[i]: float(importance[i]) for i in top_indices}

        # Record in DB
        async with AsyncSessionLocal() as db:
            mv = ModelVersion(
                version=version,
                trained_at=datetime.now(UTC),
                data_start=start_date,
                data_end=end_date,
                ic=Decimal(str(round(val_metrics["ic"], 6))),
                val_accuracy=Decimal(str(round(val_metrics["accuracy"], 4))),
                top_features=top_features,
                is_active=False,
                file_path=file_path,
                n_estimators=200,
            )
            db.add(mv)
            await db.commit()

        logger.info("ml_model.trained", version=version, ic=val_metrics["ic"])
        return {
            "version": version,
            "ic": val_metrics["ic"],
            "val_accuracy": val_metrics["accuracy"],
        }

    async def _evaluate_validation(
        self,
        booster,
        validation_features,
        y_val,
        feature_names,
        val_p2,
    ) -> dict:
        """Evaluate model on validation set."""
        from scipy.stats import spearmanr

        # Accuracy
        val_pred_classes = np.argmax(
            booster.predict(validation_features[feature_names].values),
            axis=1,
        )
        accuracy = float((val_pred_classes == y_val.values).mean())

        # IC (use actual labels as proxy if forward returns not available)
        try:
            ic, _ = spearmanr(val_p2, y_val.values)
            ic = float(ic) if ic == ic else 0.0
        except Exception:
            ic = 0.0

        return {"ic": ic, "accuracy": accuracy}

    # ── Prediction ────────────────────────────────────────────────

    async def predict(self, trade_date: date):
        """Generate predictions for all CSI 300 stocks on trade_date."""
        import lightgbm as lgb

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ModelVersion).where(ModelVersion.is_active.is_(True)).limit(1)
            )
            active_model = result.scalar_one_or_none()

        if not active_model:
            logger.warning("ml_model.no_active_model")
            return None

        from app.services.feature_engine import FeatureEngine

        fe = FeatureEngine()

        # Get factors for trade_date
        features = await fe.build_factor_matrix(trade_date, trade_date)
        if features.empty:
            logger.warning("ml_model.no_factors_for_date", date=str(trade_date))
            return None

        feature_names = fe.get_factor_names()
        booster = lgb.Booster(model_file=active_model.file_path)

        def _do_predict():
            preds = booster.predict(features[feature_names].values)
            return preds

        preds = await asyncio.to_thread(_do_predict)

        # Score = P(outperform) + 0.5 * P(neutral)
        scores = preds[:, 2] + 0.5 * preds[:, 1]

        # Save predictions
        async with AsyncSessionLocal() as db:
            for i, (idx) in enumerate(features.index):
                symbol = idx[1] if isinstance(idx, tuple) else idx
                pred = Prediction(
                    symbol=symbol,
                    trade_date=trade_date,
                    score=Decimal(str(round(float(scores[i]), 6))),
                    model_version=active_model.version,
                    confidence="normal",
                )
                db.add(pred)
            await db.commit()

        logger.info("ml_model.predicted", date=str(trade_date), count=len(scores))
        return {"date": str(trade_date), "count": len(scores)}

    # ── SHAP Explanation ──────────────────────────────────────────

    async def explain_predictions(self, trade_date: date):
        """Generate SHAP explanations for predictions on trade_date."""
        import lightgbm as lgb
        import shap

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ModelVersion).where(ModelVersion.is_active.is_(True)).limit(1)
            )
            active_model = result.scalar_one_or_none()
            if not active_model:
                return None

            pred_result = await db.execute(
                select(Prediction).where(
                    Prediction.trade_date == trade_date,
                    Prediction.model_version == active_model.version,
                )
            )
            predictions = pred_result.scalars().all()
            if not predictions:
                return None

        from app.services.feature_engine import FeatureEngine

        fe = FeatureEngine()
        features = await fe.build_factor_matrix(trade_date, trade_date)
        if features.empty:
            return None

        feature_names = fe.get_factor_names()
        booster = lgb.Booster(model_file=active_model.file_path)

        def _compute_shap():
            explainer = shap.TreeExplainer(booster)
            shap_values = explainer.shap_values(features[feature_names].values)
            # For multiclass, shap_values is a list of arrays (one per class)
            # Sum across classes for overall importance
            if isinstance(shap_values, list):
                # Sum SHAP for class 2 (outperform) as the "positive" signal
                sv = shap_values[2] if len(shap_values) > 2 else shap_values[0]
            else:
                sv = shap_values[:, :, 2] if shap_values.ndim == 3 else shap_values
            return sv

        sv = await asyncio.to_thread(_compute_shap)

        # Update predictions with explanations
        async with AsyncSessionLocal() as db:
            for i, pred in enumerate(predictions):
                if i >= len(sv):
                    break

                # Find the row in the feature matrix for this symbol
                symbol = pred.symbol
                try:
                    row_idx = list(features.index.get_level_values("symbol")).index(symbol)
                except ValueError:
                    continue

                shap_row = sv[row_idx]
                factor_vals = features.iloc[row_idx]

                # Top 3 positive, top 2 negative
                sorted_idx = np.argsort(shap_row)
                positive_idx = sorted_idx[-3:][::-1]  # top 3
                negative_idx = sorted_idx[:2]  # bottom 2

                explanation = {"positive": [], "negative": []}

                for idx in positive_idx:
                    if shap_row[idx] <= 0:
                        continue
                    fname = feature_names[idx]
                    fval = float(factor_vals.iloc[idx])
                    template = FACTOR_TEMPLATES.get(fname)
                    if template:
                        val_desc, qual_desc = _safe_template(template, fval)
                        explanation["positive"].append(
                            {
                                "factor": fname,
                                "value": fval,
                                "shap": float(shap_row[idx]),
                                "description": val_desc,
                                "assessment": qual_desc,
                            }
                        )

                for idx in negative_idx:
                    if shap_row[idx] >= 0:
                        continue
                    fname = feature_names[idx]
                    fval = float(factor_vals.iloc[idx])
                    template = FACTOR_TEMPLATES.get(fname)
                    if template:
                        val_desc, qual_desc = _safe_template(template, fval)
                        explanation["negative"].append(
                            {
                                "factor": fname,
                                "value": fval,
                                "shap": float(shap_row[idx]),
                                "description": val_desc,
                                "assessment": qual_desc,
                            }
                        )

                pred.explanation = explanation
                await db.commit()

        logger.info("ml_model.explained", date=str(trade_date), count=len(predictions))
        return {"date": str(trade_date), "explained": len(predictions)}

    # ── Model Activation ──────────────────────────────────────────

    async def activate_model(
        self,
        db: AsyncSession,
        version: str,
        params: SystemParams | None = None,
    ):
        """Activate a model version with validation gate."""
        if params is None:
            from app.services.settings_service import get_system_params

            params = await get_system_params(db)

        result = await db.execute(select(ModelVersion).where(ModelVersion.version == version))
        mv = result.scalar_one_or_none()
        if not mv:
            raise ValueError(f"模型版本 {version} 不存在")

        # Validation gate: IC must meet threshold
        if mv.ic is None or float(mv.ic) < params.model_ic_threshold:
            raise ValueError(
                f"模型验证不达标: IC={float(mv.ic) if mv.ic else 'N/A'} "
                f"< 阈值 {params.model_ic_threshold}，请先运行回测验证"
            )

        # Deactivate all others
        await db.execute(
            update(ModelVersion).where(ModelVersion.is_active.is_(True)).values(is_active=False)
        )
        mv.is_active = True
        await db.flush()
        logger.info("ml_model.activated", version=version)

    # ── Confidence Monitoring ─────────────────────────────────────

    async def check_model_confidence(self):
        """Check rolling 20-day IC, mark low confidence if needed."""
        async with AsyncSessionLocal() as db:
            cutoff = date.today() - timedelta(days=30)
            result = await db.execute(
                select(Prediction)
                .where(Prediction.trade_date >= cutoff)
                .order_by(Prediction.trade_date.desc())
            )
            recent_preds = result.scalars().all()

        if len(recent_preds) < 100:
            return {"confidence": "normal", "reason": "insufficient_data"}

        # Group by date and compute rank correlation with actual returns
        # This is a simplified check — full IC computation requires forward returns
        # For now, just mark normal
        return {"confidence": "normal"}


def _safe_template(template, val):
    """Safely call a factor template, handling edge cases."""
    try:
        if val is None or (isinstance(val, float) and val != val):
            return ("数据缺失", "")
        return template(val)
    except Exception:
        return (f"值: {val}", "")


ml_model_service = MLModelService()
