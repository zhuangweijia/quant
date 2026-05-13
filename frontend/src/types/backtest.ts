export interface BacktestRunRequest {
  strategy_id: string;
  symbol: string;
  market: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  params?: Record<string, any>;
}

export interface BacktestResultListItem {
  id: string;
  strategy_id: string;
  symbol: string;
  start_date: string;
  end_date: string;
  total_return: string | null;
  sharpe_ratio: string | null;
  max_drawdown: string | null;
  trade_count: number | null;
  status: string;
  created_at: string;
}

export interface BacktestResultDetail extends BacktestResultListItem {
  params: Record<string, any> | null;
  initial_capital: string;
  annual_return: string | null;
  sortino_ratio: string | null;
  calmar_ratio: string | null;
  win_rate: string | null;
  profit_factor: string | null;
  avg_holding_period: string | null;
  equity_curve: Record<string, any> | null;
  drawdown_curve: Record<string, any> | null;
  trades: Record<string, any> | null;
  monthly_returns: Record<string, any> | null;
  error_message: string | null;
}
