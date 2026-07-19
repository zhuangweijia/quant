export type Money = string
export type IsoDate = string
export type IsoDateTime = string

export type RiskLevel = 'conservative' | 'balanced' | 'aggressive'

export interface InvestmentProfileInput {
  investment_horizon_days: number
  risk_level: RiskLevel
  max_drawdown: number
  max_stock_weight: number
  max_industry_weight: number
  min_cash_ratio: number
  max_daily_turnover: number
}

export interface PositionInput {
  symbol: string
  quantity: number
  average_cost: Money
}

export interface PortfolioSetupRequest {
  profile: InvestmentProfileInput
  total_capital: Money
  cash: Money
  positions?: PositionInput[]
}

export type PortfolioSetupMissing = 'profile' | 'portfolio'

export interface PortfolioSetupStatus {
  complete: boolean
  has_profile: boolean
  has_portfolio: boolean
  missing: PortfolioSetupMissing[]
}

export interface InvestmentProfileResponse extends InvestmentProfileInput {
  id: string
  version: number
  is_active: boolean
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface PortfolioPositionResponse {
  id: string
  symbol: string
  name: string
  industry: string | null
  quantity: number
  average_cost: Money
  latest_close: Money
  price_date: IsoDate | null
  market_value: Money
  unrealized_pnl: Money
  current_weight: number
  target_weight: number | null
  valuation_warning: string | null
}

export interface PortfolioSummaryResponse {
  id: string
  currency: 'CNY'
  cash: Money
  market_value: Money
  total_asset: Money
  exposure: number
  target_exposure: number | null
  valuation_date: IsoDate | null
  last_confirmed_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface HoldingsReconcileRequest {
  expected_updated_at: IsoDateTime
  cash: Money
  positions?: PositionInput[]
}

export type CashMovementKind = 'deposit' | 'withdrawal' | 'fee'

export interface CashMovementRequest {
  kind: CashMovementKind
  amount: Money
  occurred_at: IsoDateTime
  note?: string
}

export interface PortfolioResponse {
  profile: InvestmentProfileResponse
  summary: PortfolioSummaryResponse
  positions: PortfolioPositionResponse[]
  valuation_warnings: string[]
  updated_at: IsoDateTime
}
