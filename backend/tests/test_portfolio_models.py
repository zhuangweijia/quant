import ast
from pathlib import Path

from app.models.advice import AdviceItem, DailyAdvice
from app.models.execution import ExecutionMutation, ExecutionRecord
from app.models.investment_profile import InvestmentProfile
from app.models.portfolio import Portfolio, PortfolioEvent, PortfolioSnapshot, Position


def test_phase_one_tables_and_unique_contracts():
    assert InvestmentProfile.__tablename__ == "investment_profiles"
    assert Portfolio.__tablename__ == "portfolios"
    assert Position.__tablename__ == "portfolio_positions"
    assert PortfolioEvent.__tablename__ == "portfolio_events"
    assert PortfolioSnapshot.__tablename__ == "portfolio_snapshots"
    assert DailyAdvice.__tablename__ == "daily_advices"
    assert AdviceItem.__tablename__ == "advice_items"
    assert ExecutionRecord.__tablename__ == "execution_records"
    assert ExecutionMutation.__tablename__ == "execution_mutations"
    assert Portfolio.__table__.c.currency.default.arg == "CNY"
    assert InvestmentProfile.__table__.c.is_active.default.arg is True
    assert DailyAdvice.__table__.c.status.default.arg == "ready"
    assert ExecutionRecord.__table__.c.revision.default.arg == 0


def test_money_and_weight_columns_keep_decimal_precision():
    assert str(Portfolio.__table__.c.cash.type) == "NUMERIC(20, 4)"
    assert str(Position.__table__.c.total_cost.type) == "NUMERIC(20, 4)"
    assert str(InvestmentProfile.__table__.c.max_drawdown.type) == "NUMERIC(8, 6)"
    assert str(AdviceItem.__table__.c.target_weight.type) == "NUMERIC(10, 8)"


def test_daily_advice_persists_non_null_progressive_constraint_codes():
    column = DailyAdvice.__table__.c.constraint_violations

    assert column.nullable is False
    assert column.default.arg(None) == []


def test_portfolio_event_cash_delta_migration_is_required():
    migration_path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "c2d4e6f8a0b1_add_portfolio_decision_domain.py"
    )
    tree = ast.parse(migration_path.read_text(encoding="utf-8"))
    cash_delta_column = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Column"
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "cash_delta"
    )
    nullable = next(
        keyword.value.value
        for keyword in cash_delta_column.keywords
        if keyword.arg == "nullable" and isinstance(keyword.value, ast.Constant)
    )

    assert nullable is False
