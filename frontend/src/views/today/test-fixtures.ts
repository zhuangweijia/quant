import type {
  AdviceItemResponse,
  DailyAdviceResponse,
  ExecutionRecordResponse,
} from '@/types/advice'

export function execution(
  overrides: Partial<ExecutionRecordResponse> = {},
): ExecutionRecordResponse {
  return {
    id: 'execution-1',
    disposition: 'partial',
    quantity: 50,
    price: '10.2000',
    fee: '1.2500',
    executed_at: '2026-07-19T10:30:00+08:00',
    reason: '部分成交',
    within_price_band: true,
    revision: 3,
    created_at: '2026-07-19T10:31:00+08:00',
    updated_at: '2026-07-19T10:31:00+08:00',
    ...overrides,
  }
}

export function adviceItem(
  overrides: Partial<AdviceItemResponse> = {},
): AdviceItemResponse {
  return {
    id: 'item-1',
    symbol: '000001',
    name: '平安银行',
    industry: '银行',
    action: 'buy',
    status: 'pending',
    current_quantity: 100,
    target_quantity: 300,
    delta_quantity: 200,
    current_average_cost: '9.9000',
    current_weight: 0.1,
    target_weight: 0.25,
    reference_price: '10.1000',
    price_tolerance: 0.03,
    score: 0.8765,
    rank: 2,
    confidence: 'high',
    positive_factors: ['盈利上修', '趋势增强'],
    risks: ['行业波动'],
    invalidation_conditions: ['跌破风险带'],
    constraint_notes: ['受单股权重约束'],
    execution: null,
    ...overrides,
  }
}

export function dailyAdvice(
  overrides: Partial<DailyAdviceResponse> = {},
): DailyAdviceResponse {
  return {
    id: 'advice-1',
    signal_date: '2026-07-18',
    version: 2,
    status: 'ready',
    model_version: 'model-v3',
    data_date: '2026-07-18',
    current_exposure: 0.42,
    target_exposure: 0.58,
    current_cash: '58000.0001',
    estimated_cash: '42000.0099',
    total_asset: '100000.0100',
    generated_at: '2026-07-18T18:30:00+08:00',
    portfolio_updated_at: '2026-07-18T17:00:00+08:00',
    stale_warnings: ['部分行情使用上一交易日数据'],
    constraint_violations: ['turnover_relaxed'],
    items: [adviceItem()],
    error_code: null,
    error_message: null,
    ...overrides,
  }
}
