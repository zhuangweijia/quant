import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { adviceApi } from '@/api/advice'
import { portfolioApi } from '@/api/portfolio'
import { usePortfolioStore } from '@/stores/portfolio'
import type {
  AdviceItemResponse,
  AdviceTodayResponse,
  DailyAdviceResponse,
} from '@/types/advice'
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

const unchangedItem: AdviceItemResponse = {
  ...pendingItem,
  id: 'item-2',
  symbol: '000002',
  name: '万科A',
  action: 'hold',
  target_quantity: 0,
  delta_quantity: 0,
  target_weight: 0,
}

type AvailableToday = Extract<
  AdviceTodayResponse,
  { advice: DailyAdviceResponse }
>

function today(items: AdviceItemResponse[] = [pendingItem]): AvailableToday {
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
      items,
      error_code: null,
      error_message: null,
    },
    error_code: null,
    error_message: null,
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((done, fail) => {
    resolve = done
    reject = fail
  })
  return { promise, resolve, reject }
}

async function flushMicrotasks() {
  for (let index = 0; index < 10; index += 1) await Promise.resolve()
}

describe('useAdviceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
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

  it('drops advice when generation returns the not-generated state', async () => {
    const notGenerated: DailyAdviceResponse = {
      ...today().advice,
      status: 'not_generated',
    }
    vi.mocked(adviceApi.generate).mockResolvedValue({ data: notGenerated } as never)
    const store = useAdviceStore()

    await store.generate()

    expect(store.today).toEqual({
      state: 'not_generated',
      setup_required: false,
      advice: null,
      error_code: null,
      error_message: null,
    })
  })

  it('replaces one item before concurrently reloading today and portfolio', async () => {
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
    const refreshedToday: AdviceTodayResponse = {
      ...today([executedItem, unchangedItem]),
      state: 'handled',
      advice: {
        ...today([executedItem, unchangedItem]).advice,
        status: 'handled',
      },
    }
    const todayReload = deferred<never>()
    const portfolioReload = deferred<never>()
    vi.mocked(adviceApi.getToday).mockReturnValue(todayReload.promise)
    const portfolioStore = usePortfolioStore()
    const loadPortfolio = vi
      .spyOn(portfolioStore, 'loadPortfolio')
      .mockReturnValue(portfolioReload.promise)
    const store = useAdviceStore()
    store.today = today([pendingItem, unchangedItem])
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

    let settled = false
    const pending = store.updateExecution('item-1', payload).finally(() => {
      settled = true
    })
    await flushMicrotasks()

    expect(adviceApi.updateExecution).toHaveBeenCalledWith(
      'item-1',
      payload,
      '00000000-0000-4000-8000-000000000001',
    )
    expect(adviceApi.getToday).toHaveBeenCalledOnce()
    expect(loadPortfolio).toHaveBeenCalledOnce()
    expect(store.today?.advice?.items[0]).toEqual(executedItem)
    expect(store.today?.advice?.items[1]).toEqual(unchangedItem)
    expect(store.today?.state).toBe('handled')
    expect(settled).toBe(false)

    todayReload.resolve({ data: refreshedToday } as never)
    await flushMicrotasks()
    expect(settled).toBe(false)

    portfolioReload.resolve(undefined as never)
    await pending

    expect(store.today).toEqual(refreshedToday)
    expect(store.loading).toBe(false)
  })

  it.each([
    ['today refresh fails', true, false],
    ['portfolio refresh fails', false, true],
    ['both refreshes fail', true, true],
  ])(
    'keeps a successful execution when %s',
    async (_case, failToday, failPortfolio) => {
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
          revision: 4,
          created_at: '2026-07-19T09:35:00+08:00',
          updated_at: '2026-07-19T09:36:00+08:00',
        },
      }
      const executionResponse = { item: executedItem, advice_state: 'handled' as const }
      vi.mocked(adviceApi.updateExecution).mockResolvedValue({ data: executionResponse } as never)
      const refreshedToday: AdviceTodayResponse = {
        ...today([executedItem, unchangedItem]),
        state: 'handled',
        advice: {
          ...today([executedItem, unchangedItem]).advice,
          status: 'handled',
        },
      }
      const todayReload = deferred<never>()
      const portfolioReload = deferred<never>()
      vi.mocked(adviceApi.getToday).mockReturnValue(todayReload.promise)
      vi.spyOn(portfolioApi, 'getPortfolio').mockReturnValue(portfolioReload.promise)
      const store = useAdviceStore()
      const portfolioStore = usePortfolioStore()
      store.today = today([pendingItem, unchangedItem])
      const payload = {
        disposition: 'executed' as const,
        quantity: 100,
        price: '10.1001',
        fee: '5.0001',
        executed_at: '2026-07-19T09:35:00+08:00',
        reason: '',
        expected_revision: 3,
        acknowledge_outside_advice: false,
      }

      let outcome: { ok: boolean; value?: unknown; error?: unknown } | null = null
      const observed = store.updateExecution('item-1', payload).then(
        value => { outcome = { ok: true, value } },
        error => { outcome = { ok: false, error } },
      )
      await flushMicrotasks()

      expect(adviceApi.getToday).toHaveBeenCalledOnce()
      expect(portfolioApi.getPortfolio).toHaveBeenCalledOnce()
      expect(store.today?.advice?.items[0]).toEqual(executedItem)
      expect(store.today?.advice?.items[0].execution?.revision).toBe(4)
      expect(store.loading).toBe(true)
      expect(portfolioStore.loading).toBe(true)

      if (!failToday && failPortfolio) {
        portfolioReload.reject(new Error('持仓刷新失败'))
      } else if (failToday) {
        todayReload.reject(new Error('今日刷新失败'))
      } else {
        todayReload.resolve({ data: refreshedToday } as never)
      }
      await flushMicrotasks()
      expect(outcome).toBeNull()

      if (!failToday && failPortfolio) {
        todayReload.resolve({ data: refreshedToday } as never)
      } else if (failPortfolio) {
        portfolioReload.reject(new Error('持仓刷新失败'))
      } else {
        portfolioReload.resolve({ data: {} } as never)
      }
      await observed

      expect(outcome).toEqual({ ok: true, value: executionResponse })
      expect(store.error).toBe('执行已记录，但刷新最新状态失败，请重试刷新')
      expect(store.loading).toBe(false)
      expect(portfolioStore.loading).toBe(false)
      if (failToday) {
        expect(store.today?.advice?.items[0]).toEqual(executedItem)
      }
    },
  )

  it('rejects a failed execution API request without applying or refreshing', async () => {
    vi.mocked(adviceApi.updateExecution).mockRejectedValue(new Error('执行保存失败'))
    const getToday = vi.mocked(adviceApi.getToday)
    const getPortfolio = vi.spyOn(portfolioApi, 'getPortfolio')
    const store = useAdviceStore()
    const portfolioStore = usePortfolioStore()
    store.today = today([pendingItem, unchangedItem])

    await expect(store.updateExecution('item-1', {
      disposition: 'executed',
      quantity: 100,
      price: '10.1001',
      fee: '5.0001',
      executed_at: '2026-07-19T09:35:00+08:00',
      reason: '',
      expected_revision: 0,
      acknowledge_outside_advice: false,
    })).rejects.toThrow('执行保存失败')

    expect(store.today?.advice?.items[0]).toEqual(pendingItem)
    expect(getToday).not.toHaveBeenCalled()
    expect(getPortfolio).not.toHaveBeenCalled()
    expect(store.error).toBe('执行保存失败')
    expect(store.loading).toBe(false)
    expect(portfolioStore.loading).toBe(false)
  })
})
