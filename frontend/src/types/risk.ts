export interface RiskRule {
  id: string;
  name: string;
  rule_type: string;
  scope: string;
  strategy_id: string | null;
  params: Record<string, any>;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface RiskRuleCreateRequest {
  name: string;
  rule_type: string;
  scope: string;
  strategy_id?: string;
  params: Record<string, any>;
}

export interface RiskRuleUpdateRequest {
  name?: string;
  params?: Record<string, any>;
}

export interface Alert {
  id: string;
  rule_id: string;
  rule_name: string;
  level: string;
  message: string;
  is_read: boolean;
  created_at: string;
}
