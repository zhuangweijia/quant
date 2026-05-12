from app.schemas.common import ResponseBase, PageRequest, PageResponse
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    RefreshRequest,
    UserResponse,
    ChangePasswordRequest,
)
from app.schemas.strategy import (
    StrategyCreate,
    StrategyUpdate,
    StrategyListItem,
    StrategyDetail,
)
from app.schemas.trade import OrderRequest, OrderResponse, PositionResponse
from app.schemas.backtest import (
    BacktestRunRequest,
    BacktestResultListItem,
    BacktestResultDetail,
)
from app.schemas.market import KlineRequest, KlineData, SymbolInfo
from app.schemas.risk import (
    RiskRuleCreate,
    RiskRuleUpdate,
    RiskRuleResponse,
    AlertResponse,
)
from app.schemas.dashboard import (
    DashboardOverview,
    EquityCurvePoint,
    StrategyRankItem,
)
