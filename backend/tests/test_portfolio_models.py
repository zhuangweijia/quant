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
