#!/usr/bin/env python3
"""首次全量数据拉取脚本 — 拉取沪深300成分股历史数据。

Usage:
    cd backend && python scripts/bootstrap_data.py
"""

import asyncio
import sys
import os

# Ensure backend is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from app.services.data_sync_service import data_sync_service

    print("=" * 60)
    print("  A股数据初始化 — 沪深300全量拉取")
    print("=" * 60)

    # Step 1: Sync CSI 300 constituents
    print("\n[1/4] 同步沪深300成分股列表...")
    result = await data_sync_service.sync_csi300_constituents()
    if not result.get("success"):
        print(f"  ❌ 失败: {result.get('error')}")
        sys.exit(1)
    print(f"  ✅ 成功: {result['total']} 只成分股 (新增 {result['new']})")

    # Step 2: Full K-line sync
    print("\n[2/4] 全量拉取历史日K线数据 (可能需要 30-60 分钟)...")
    from app.database import AsyncSessionLocal
    from app.models.stock import Stock
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        stocks = await db.execute(
            select(Stock).where(Stock.in_csi300.is_(True))
        )
        stock_list = stocks.scalars().all()

    total = len(stock_list)
    success = 0
    failed = 0

    for i, stock in enumerate(stock_list):
        result = await data_sync_service.sync_daily_bars_full(stock.symbol)
        if result.get("success"):
            success += 1
            # Update last_synced_date
            from datetime import date
            async with AsyncSessionLocal() as db:
                db_stock = await db.get(Stock, stock.id)
                if db_stock:
                    db_stock.last_synced_date = date.today()
                    await db.commit()
        else:
            failed += 1
            print(f"  ⚠️  {stock.symbol} {stock.name} 失败: {result.get('error', '')[:60]}")

        if (i + 1) % 10 == 0 or i + 1 == total:
            print(f"  进度: {i+1}/{total} (成功 {success}, 失败 {failed})")

    print(f"\n  K线同步完成: {success} 成功, {failed} 失败")

    # Step 3: Fundamentals
    print("\n[3/4] 拉取基本面数据...")
    result = await data_sync_service.sync_fundamentals()
    print(f"  ✅ 基本面: {result.get('cached', 0)}/{result.get('total', 0)} 缓存成功")

    # Step 4: Validate
    print("\n[4/4] 数据完整性校验...")
    result = await data_sync_service.validate_data_integrity()
    print(f"  ✅ 校验完成: {result['total']} 只股票, {result['warnings']} 条警告")

    print("\n" + "=" * 60)
    print("  ✅ 数据初始化完成！可以开始训练模型了。")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
