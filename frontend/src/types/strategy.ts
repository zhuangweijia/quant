export interface StrategyListItem {
  id: string;
  name: string;
  market: string;
  status: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface StrategyDetail extends StrategyListItem {
  code: string;
  params: Record<string, any> | null;
}

export interface StrategyCreateRequest {
  name: string;
  description?: string;
  code: string;
  params?: Record<string, any>;
  market: string;
}

export interface StrategyUpdateRequest {
  name?: string;
  description?: string;
  code?: string;
  params?: Record<string, any>;
}
