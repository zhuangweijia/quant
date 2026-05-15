export interface SymbolInfo {
  symbol: string;
  name: string;
  market: string;
}

export interface KlineData {
  timestamp: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
}

export interface TickPrice {
  symbol: string;
  price: string;
  timestamp: string;
}

export interface WatchlistItem {
  id: string;
  symbol: string;
  market: string;
  sort_order: number;
}
