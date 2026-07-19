import type { IsoDate, IsoDateTime, Money } from './portfolio'

export type AdviceState =
  | 'not_generated'
  | 'generating'
  | 'ready'
  | 'partially_handled'
  | 'handled'
  | 'expired'
  | 'failed'

export type AdviceAction = 'buy' | 'increase' | 'hold' | 'reduce' | 'exit'
export type AdviceItemStatus = 'pending' | 'executed' | 'partial' | 'skipped' | 'expired'
export type ExecutionDisposition = 'executed' | 'partial' | 'skipped'

export interface ExecutionRecordResponse {
  id: string
  disposition: ExecutionDisposition
  quantity: number
  price: Money | null
  fee: Money
  executed_at: IsoDateTime | null
  reason: string
  within_price_band: boolean
  revision: number
  created_at: IsoDateTime
  updated_at: IsoDateTime
}

export interface AdviceItemResponse {
  id: string
  symbol: string
  name: string
  industry: string | null
  action: AdviceAction
  status: AdviceItemStatus
  current_quantity: number
  target_quantity: number
  delta_quantity: number
  current_average_cost: Money | null
  current_weight: number
  target_weight: number
  reference_price: Money
  price_tolerance: number
  score: number
  rank: number | null
  confidence: string
  positive_factors: string[]
  risks: string[]
  invalidation_conditions: string[]
  constraint_notes: string[]
  execution: ExecutionRecordResponse | null
}

export interface DailyAdviceResponse {
  id: string
  signal_date: IsoDate
  version: number
  status: AdviceState
  model_version: string
  data_date: IsoDate
  current_exposure: number
  target_exposure: number
  current_cash: Money
  estimated_cash: Money
  total_asset: Money
  generated_at: IsoDateTime
  portfolio_updated_at: IsoDateTime
  stale_warnings: string[]
  constraint_violations: string[]
  items: AdviceItemResponse[]
  error_code: string | null
  error_message: string | null
}

interface AdviceTodayBase {
  setup_required: boolean
  error_code: string | null
  error_message: string | null
}

export type AdviceTodayResponse =
  | (AdviceTodayBase & {
      state: 'not_generated'
      advice: null
    })
  | (AdviceTodayBase & {
      state: 'generating' | 'failed'
      advice: DailyAdviceResponse | null
    })
  | (AdviceTodayBase & {
      state: 'ready' | 'partially_handled' | 'handled' | 'expired'
      advice: DailyAdviceResponse
    })

export interface ExecutionUpdateRequest {
  disposition: ExecutionDisposition
  quantity?: number
  price?: Money | null
  fee?: Money
  executed_at?: IsoDateTime | null
  reason?: string
  expected_revision: number
  acknowledge_outside_advice?: boolean
}

export interface ExecutionResponse {
  item: AdviceItemResponse
  advice_state: AdviceState
}
