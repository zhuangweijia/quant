export interface Order {
  id: string;
  strategy_id: string | null;
  symbol: string;
  market: string;
  side: string;
  order_type: string;
  qty: string;
  price: string | null;
  status: string;
  filled_qty: string;
  filled_price: string | null;
  commission: string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: string;
  strategy_id: string | null;
  symbol: string;
  market: string;
  qty: string;
  avg_price: string;
  frozen_qty: string;
  updated_at: string;
}

export interface OrderRequest {
  symbol: string;
  market: string;
  side: string;
  order_type: string;
  qty: number;
  price?: number;
  strategy_id?: string;
}

export interface AccountInfo {
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
