export interface DashboardOverview {
  total_equity: string;
  cash: string;
  position_value: string;
  daily_pnl: string;
  daily_pnl_pct: string;
  total_pnl: string;
  total_pnl_pct: string;
  running_strategies: number;
  total_strategies: number;
  today_trades: number;
  unread_alerts: number;
  mode: string;
}

export interface EquityCurvePoint {
  date: string;
  equity: number;
  benchmark?: number;
}

export interface StrategyRankItem {
  strategy_id: string;
  strategy_name: string;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
}
