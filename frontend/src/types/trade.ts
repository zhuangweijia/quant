export interface Order {
  id: string;
  strategy_id: string | null;
  symbol: string;
  market: string;
  side: string;
  order_type: string;
  qty: number;
  price: number | null;
  status: string;
  filled_qty: number;
  filled_price: number | null;
  commission: number;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Position {
  id: string;
  strategy_id: string | null;
  symbol: string;
  market: string;
  qty: number;
  avg_price: number;
  market_value?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
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
