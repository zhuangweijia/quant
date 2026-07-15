class AppError(Exception):
    def __init__(self, code: int, message: str, detail: str = ""):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class StrategyLoadError(AppError):
    def __init__(self, detail: str):
        super().__init__(400, "策略加载失败", detail)


class InsufficientFundsError(AppError):
    def __init__(self):
        super().__init__(400, "资金不足")


class RiskCheckFailedError(AppError):
    def __init__(self, reason: str):
        super().__init__(403, "风控拦截", reason)


class MarketClosedError(AppError):
    def __init__(self, market: str):
        super().__init__(400, "市场未开盘", f"{market} 市场当前不在交易时段")


class OrderNotFoundError(AppError):
    def __init__(self, order_id: str):
        super().__init__(404, "订单不存在", order_id)


class StrategyNotFoundError(AppError):
    def __init__(self, strategy_id: str):
        super().__init__(404, "策略不存在", strategy_id)


class DuplicateUsernameError(AppError):
    def __init__(self, username: str):
        super().__init__(409, "用户名已存在", username)


class InvalidCredentialsError(AppError):
    def __init__(self):
        super().__init__(401, "用户名或密码错误")


class AccountLockedError(AppError):
    def __init__(self):
        super().__init__(423, "账号已锁定，请稍后重试")


class TokenExpiredError(AppError):
    def __init__(self):
        super().__init__(401, "Token 已过期")


class InvalidTokenError(AppError):
    def __init__(self):
        super().__init__(401, "无效的 Token")
