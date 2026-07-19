import { beforeEach, describe, expect, it, vi } from 'vitest'

import client from './client'
import { portfolioApi } from './portfolio'

vi.mock('./client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}))

describe('portfolioApi', () => {
  beforeEach(() => vi.clearAllMocks())

  it('uses current-user portfolio endpoints without owner identifiers', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: {} } as never)

    await portfolioApi.getSetupStatus()
    await portfolioApi.getPortfolio()

    expect(client.get).toHaveBeenNthCalledWith(1, '/api/v1/portfolio/setup-status')
    expect(client.get).toHaveBeenNthCalledWith(2, '/api/v1/portfolio')
  })

  it('sends exact money strings to portfolio mutation endpoints', async () => {
    vi.mocked(client.post).mockResolvedValue({ data: {} } as never)
    vi.mocked(client.put).mockResolvedValue({ data: {} } as never)
    const profile = {
      investment_horizon_days: 120,
      risk_level: 'balanced' as const,
      max_drawdown: 0.15,
      max_stock_weight: 0.08,
      max_industry_weight: 0.25,
      min_cash_ratio: 0.1,
      max_daily_turnover: 0.3,
    }
    const setup = {
      profile,
      total_capital: '100000.0001',
      cash: '90000.0001',
      positions: [{ symbol: '000001', quantity: 100, average_cost: '10.0001' }],
    }
    const reconcile = {
      expected_updated_at: '2026-07-19T09:00:00+08:00',
      cash: '91000.0001',
      positions: setup.positions,
    }
    const movement = {
      kind: 'fee' as const,
      amount: '5.0001',
      occurred_at: '2026-07-19T10:00:00+08:00',
      note: 'manual fee',
    }

    await portfolioApi.completeSetup(setup)
    await portfolioApi.updateProfile(profile)
    await portfolioApi.reconcileHoldings(reconcile)
    await portfolioApi.recordCashMovement(movement)

    expect(client.post).toHaveBeenNthCalledWith(1, '/api/v1/portfolio/setup', setup)
    expect(client.put).toHaveBeenNthCalledWith(1, '/api/v1/portfolio/profile', profile)
    expect(client.put).toHaveBeenNthCalledWith(2, '/api/v1/portfolio/holdings', reconcile)
    expect(client.post).toHaveBeenNthCalledWith(
      2,
      '/api/v1/portfolio/cash-movements',
      movement,
    )
  })
})
