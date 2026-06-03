## ADDED Requirements

### Requirement: Global API rate limiting
系统 SHALL 对所有 API 请求实施每分钟请求次数限制。默认限制为 60 次/分钟，基于客户端 IP 或已认证用户的 user_id 识别身份。

#### Scenario: Normal request within limit
- **WHEN** 客户端在 1 分钟内发送的请求数未超过限制
- **THEN** 请求正常处理，响应头包含 `X-RateLimit-Limit`、`X-RateLimit-Remaining`、`X-RateLimit-Reset`

#### Scenario: Request exceeds global limit
- **WHEN** 客户端在 1 分钟内发送的请求数超过默认限制
- **THEN** 系统返回 HTTP 429 状态码，响应体包含 `{"code": 429, "message": "请求过于频繁，请稍后重试"}`

### Requirement: Trade route specific rate limiting
系统 SHALL 对 `/api/v1/trade/` 路径下的接口实施更严格的限流：10 次/分钟。

#### Scenario: Trade request within limit
- **WHEN** 用户在 1 分钟内发送的交易请求数未超过 10 次
- **THEN** 请求正常处理

#### Scenario: Trade request exceeds limit
- **WHEN** 用户在 1 分钟内发送的交易请求数超过 10 次
- **THEN** 系统返回 HTTP 429 状态码

### Requirement: Backtest route specific rate limiting
系统 SHALL 对 `/api/v1/backtest/run` 接口实施 3 次/分钟的限流。

#### Scenario: Backtest request exceeds limit
- **WHEN** 用户在 1 分钟内发送的回测请求超过 3 次
- **THEN** 系统返回 HTTP 429 状态码

### Requirement: Rate limit response headers
系统 SHALL 在每个 API 响应中包含限流相关头部。

#### Scenario: Response headers present
- **WHEN** 任何 API 请求被处理（无论成功或被限流）
- **THEN** 响应头包含 `X-RateLimit-Limit`（总限制数）、`X-RateLimit-Remaining`（剩余次数）、`X-RateLimit-Reset`（重置时间的 Unix 时间戳）

### Requirement: Health endpoint exempt from rate limiting
系统 SHALL 豁免 `/health` 路径的限流检查。

#### Scenario: Health check not rate limited
- **WHEN** 客户端对 `/health` 发送大量请求
- **THEN** 所有请求正常处理，不受限流影响
