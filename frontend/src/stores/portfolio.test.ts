import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { portfolioApi } from '@/api/portfolio'
import { usePortfolioStore } from './portfolio'

vi.mock('@/api/portfolio', () => ({
  portfolioApi: {
    getSetupStatus: vi.fn(),
    completeSetup: vi.fn(),
    getPortfolio: vi.fn(),
    updateProfile: vi.fn(),
    reconcileHoldings: vi.fn(),
    recordCashMovement: vi.fn(),
  },
}))

const setupStatus = {
  complete: true,
  has_profile: true,
  has_portfolio: true,
  missing: [],
}

function portfolio(updatedAt = '2026-07-19T09:00:00+08:00') {
  return {
    profile: {
      id: 'profile-1',
      version: 1,
      is_active: true,
      investment_horizon_days: 120,
      risk_level: 'balanced',
      max_drawdown: 0.15,
      max_stock_weight: 0.08,
      max_industry_weight: 0.25,
      min_cash_ratio: 0.1,
      max_daily_turnover: 0.3,
      created_at: '2026-07-19T08:00:00+08:00',
      updated_at: updatedAt,
    },
    summary: {
      id: 'portfolio-1',
      currency: 'CNY',
      cash: '100000.0001',
      market_value: '0',
      total_asset: '100000.0001',
      exposure: 0,
      target_exposure: null,
      valuation_date: null,
      last_confirmed_at: updatedAt,
      updated_at: updatedAt,
    },
    positions: [],
    valuation_warnings: [],
    updated_at: updatedAt,
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => {
    resolve = done
  })
  return { promise, resolve }
}

describe('usePortfolioStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('keeps the last successful portfolio when a refresh fails', async () => {
    vi.mocked(portfolioApi.getPortfolio)
      .mockResolvedValueOnce({ data: portfolio() } as never)
      .mockRejectedValueOnce(new Error('网络不可用'))
    const store = usePortfolioStore()

    await store.loadPortfolio()
    const lastSuccessful = store.portfolio
    await expect(store.loadPortfolio()).rejects.toThrow('网络不可用')

    expect(store.portfolio).toBe(lastSuccessful)
    expect(store.error).toBe('网络不可用')
  })

  it('refreshes setup status and portfolio after setup succeeds', async () => {
    const refreshed = portfolio('2026-07-19T10:00:00+08:00')
    vi.mocked(portfolioApi.completeSetup).mockResolvedValue({ data: portfolio() } as never)
    vi.mocked(portfolioApi.getSetupStatus).mockResolvedValue({ data: setupStatus } as never)
    vi.mocked(portfolioApi.getPortfolio).mockResolvedValue({ data: refreshed } as never)
    const store = usePortfolioStore()

    await store.completeSetup({
      profile: portfolio().profile,
      total_capital: '100000.0001',
      cash: '100000.0001',
      positions: [],
    } as never)

    expect(portfolioApi.getSetupStatus).toHaveBeenCalledOnce()
    expect(portfolioApi.getPortfolio).toHaveBeenCalledOnce()
    expect(store.setupStatus).toEqual(setupStatus)
    expect(store.portfolio).toEqual(refreshed)
  })

  it('stays loading until all concurrent requests settle', async () => {
    const setupRequest = deferred<never>()
    const portfolioRequest = deferred<never>()
    vi.mocked(portfolioApi.getSetupStatus).mockReturnValue(setupRequest.promise)
    vi.mocked(portfolioApi.getPortfolio).mockReturnValue(portfolioRequest.promise)
    const store = usePortfolioStore()

    const first = store.loadSetupStatus()
    const second = store.loadPortfolio()
    expect(store.loading).toBe(true)

    setupRequest.resolve({ data: setupStatus } as never)
    await first
    expect(store.loading).toBe(true)

    portfolioRequest.resolve({ data: portfolio() } as never)
    await second
    expect(store.loading).toBe(false)
  })
})
