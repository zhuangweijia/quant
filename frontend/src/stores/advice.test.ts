import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { adviceApi } from '@/api/advice'
import { usePortfolioStore } from '@/stores/portfolio'
import type { AdviceItemResponse, AdviceTodayResponse } from '@/types/advice'
import { useAdviceStore } from './advice'

vi.mock('@/api/advice', () => ({
  adviceApi: {
    getToday: vi.fn(),
    generate: vi.fn(),
    updateExecution: vi.fn(),
  },
}))

const pendingItem: AdviceItemResponse = {
  id: 'item-1',
  symbol: '000001',
  name: '平安银行',
  industry: '银行',
  action: 'buy',
  status: 'pending',
  current_quantity: 0,
  target_quantity: 100,
  delta_quantity: 100,
  current_average_cost: null,
  current_weight: 0,
  target_weight: 0.1,
  reference_price: '10.0001',
  price_tolerance: 0.02,
  score: 0.8,
  rank: 1,
  confidence: 'high',
  positive_factors: [],
  risks: [],
  invalidation_conditions: [],
  constraint_notes: [],
  execution: null,
}

function today(item: AdviceItemResponse = pendingItem): AdviceTodayResponse {
  return {
    state: 'ready',
    setup_required: false,
    advice: {
      id: 'advice-1',
      signal_date: '2026-07-18',
      version: 1,
      status: 'ready',
      model_version: 'model-v1',
      data_date: '2026-07-18',
      current_exposure: 0,
      target_exposure: 0.1,
      current_cash: '100000.0001',
      estimated_cash: '99000.0001',
      total_asset: '100000.0001',
      generated_at: '2026-07-18T17:00:00+08:00',
      portfolio_updated_at: '2026-07-18T16:00:00+08:00',
      stale_warnings: [],
      constraint_violations: [],
      items: [item],
      error_code: null,
      error_message: null,
    },
    error_code: null,
    error_message: null,
  }
}

describe('useAdviceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('keeps the last successful today state when a refresh fails', async () => {
    vi.mocked(adviceApi.getToday)
      .mockResolvedValueOnce({ data: today() } as never)
      .mockRejectedValueOnce(new Error('建议服务不可用'))
    const store = useAdviceStore()

    await store.loadToday()
    const lastSuccessful = store.today
    await expect(store.loadToday()).rejects.toThrow('建议服务不可用')

    expect(store.today).toBe(lastSuccessful)
    expect(store.error).toBe('建议服务不可用')
  })

  it('uses a store-generated idempotency key and reloads today and portfolio', async () => {
    const executedItem: AdviceItemResponse = {
      ...pendingItem,
      status: 'executed',
      execution: {
        id: 'execution-1',
        disposition: 'executed',
        quantity: 100,
        price: '10.1001',
        fee: '5.0001',
        executed_at: '2026-07-19T09:35:00+08:00',
        reason: '',
        within_price_band: true,
        revision: 1,
        created_at: '2026-07-19T09:35:00+08:00',
        updated_at: '2026-07-19T09:35:00+08:00',
      },
    }
    vi.spyOn(crypto, 'randomUUID').mockReturnValue(
      '00000000-0000-4000-8000-000000000001',
    )
    vi.mocked(adviceApi.updateExecution).mockResolvedValue({
      data: { item: executedItem, advice_state: 'handled' },
    } as never)
    vi.mocked(adviceApi.getToday).mockResolvedValue({
      data: {
        ...today(executedItem),
        state: 'handled',
        advice: { ...today(executedItem).advice, status: 'handled' },
      },
    } as never)
    const portfolioStore = usePortfolioStore()
    const loadPortfolio = vi.spyOn(portfolioStore, 'loadPortfolio').mockResolvedValue(
      undefined as never,
    )
    const store = useAdviceStore()
    store.today = today()
    const payload = {
      disposition: 'executed' as const,
      quantity: 100,
      price: '10.1001',
      fee: '5.0001',
      executed_at: '2026-07-19T09:35:00+08:00',
      reason: '',
      expected_revision: 0,
      acknowledge_outside_advice: false,
    }

    await store.updateExecution('item-1', payload)

    expect(adviceApi.updateExecution).toHaveBeenCalledWith(
      'item-1',
      payload,
      '00000000-0000-4000-8000-000000000001',
    )
    expect(adviceApi.getToday).toHaveBeenCalledOnce()
    expect(loadPortfolio).toHaveBeenCalledOnce()
    expect(store.today?.advice?.items[0]).toEqual(executedItem)
    expect(store.today?.state).toBe('handled')
  })
})
