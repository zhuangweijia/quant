import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { usePortfolioStore } from '@/stores/portfolio'
import type {
  InvestmentProfileResponse,
  PortfolioResponse,
} from '@/types/portfolio'
import PortfolioView from './PortfolioView.vue'

const mounted: VueWrapper[] = []

function profile(version = 1): InvestmentProfileResponse {
  return {
    id: `profile-${version}`,
    version,
    is_active: true,
    investment_horizon_days: 120,
    risk_level: 'balanced',
    max_drawdown: 0.15,
    max_stock_weight: 0.08,
    max_industry_weight: 0.25,
    min_cash_ratio: 0.1,
    max_daily_turnover: 0.3,
    created_at: '2026-07-18T08:00:00+08:00',
    updated_at: '2026-07-18T09:00:00+08:00',
  }
}

function portfolio(
  updatedAt = '2026-07-19T09:00:00+08:00',
  positions: PortfolioResponse['positions'] = [
    {
      id: 'position-1',
      symbol: '000001',
      name: '平安银行',
      industry: '银行',
      quantity: 300,
      average_cost: '10.0001',
      latest_close: '11.2500',
      price_date: '2026-07-18',
      market_value: '3375.0000',
      unrealized_pnl: '374.9700',
      current_weight: 0.03375,
      target_weight: 0.05,
      valuation_warning: '该股票使用上一交易日收盘价',
    },
    {
      id: 'position-2',
      symbol: '000002',
      name: '万科A',
      industry: null,
      quantity: 100,
      average_cost: '8.50',
      latest_close: '0',
      price_date: null,
      market_value: '0',
      unrealized_pnl: '-850.00',
      current_weight: 0,
      target_weight: null,
      valuation_warning: '缺少最新估值',
    },
  ],
): PortfolioResponse {
  return {
    profile: profile(),
    summary: {
      id: 'portfolio-1',
      currency: 'CNY',
      cash: '96625.1234',
      market_value: '3375.0000',
      total_asset: '100000.1234',
      exposure: 0.03375,
      target_exposure: 0.6,
      valuation_date: '2026-07-18',
      last_confirmed_at: '2026-07-19T08:30:00+08:00',
      updated_at: updatedAt,
    },
    positions,
    valuation_warnings: ['组合中有一只股票缺少当日行情'],
    updated_at: updatedAt,
  }
}

function mountView(): VueWrapper {
  const wrapper = mount(PortfolioView, { attachTo: document.body })
  mounted.push(wrapper)
  return wrapper
}

function installPortfolioLoad(value: PortfolioResponse = portfolio()) {
  const store = usePortfolioStore()
  const load = vi.spyOn(store, 'loadPortfolio').mockImplementation(async () => {
    store.portfolio = value
    return value
  })
  return { store, load }
}

function getElement<T extends Element = HTMLElement>(selector: string): T {
  const element = document.querySelector<T>(selector)
  if (!element) throw new Error(`Missing element ${selector}`)
  return element
}

async function setInput(selector: string, value: string) {
  const input = getElement<HTMLInputElement | HTMLSelectElement>(selector)
  input.value = value
  input.dispatchEvent(new Event('input', { bubbles: true }))
  input.dispatchEvent(new Event('change', { bubbles: true }))
  await flushPromises()
}

async function click(selector: string) {
  getElement<HTMLElement>(selector).click()
  await flushPromises()
}

describe('PortfolioView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    for (const wrapper of mounted.splice(0)) wrapper.unmount()
    document.body.innerHTML = ''
    vi.restoreAllMocks()
  })

  it('shows loading before the initial portfolio request settles', async () => {
    const store = usePortfolioStore()
    let resolve!: (value: PortfolioResponse) => void
    vi.spyOn(store, 'loadPortfolio').mockReturnValue(
      new Promise(done => { resolve = done }),
    )

    const wrapper = mountView()
    expect(wrapper.text()).toContain('正在加载持仓')

    const loaded = portfolio()
    store.portfolio = loaded
    resolve(loaded)
    await flushPromises()
    expect(wrapper.text()).not.toContain('正在加载持仓')
  })

  it('shows request errors separately from an empty portfolio', async () => {
    const store = usePortfolioStore()
    vi.spyOn(store, 'loadPortfolio').mockRejectedValue(new Error('网络不可用'))
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('网络不可用')
    expect(wrapper.text()).not.toContain('暂无持仓')
    expect(wrapper.find('[data-testid="portfolio-retry"]').exists()).toBe(true)
  })

  it('shows an empty workspace separately from a valid cash-only portfolio', async () => {
    const store = usePortfolioStore()
    vi.spyOn(store, 'loadPortfolio').mockRejectedValue(
      new ApiError('投资组合尚未初始化', undefined, 404),
    )
    const wrapper = mountView()
    await flushPromises()

    expect(store.portfolio).toBeNull()
    expect(wrapper.text()).toContain('尚未建立投资组合')
    expect(wrapper.text()).not.toContain('暂无持仓')
  })

  it('test_cash_only_portfolio_is_not_request_error', async () => {
    const cashOnly = portfolio('2026-07-19T09:00:00+08:00', [])
    cashOnly.valuation_warnings = []
    installPortfolioLoad(cashOnly)
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('暂无持仓')
    expect(wrapper.text()).toContain('96625.1234')
    expect(wrapper.text()).not.toContain('加载持仓失败')
    expect(wrapper.find('[data-testid="portfolio-retry"]').exists()).toBe(false)
  })

  it('test_renders_summary_totals', async () => {
    installPortfolioLoad()
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.get('h1').text()).toBe('持仓')
    expect(wrapper.text()).toContain('100000.1234')
    expect(wrapper.text()).toContain('96625.1234')
    expect(wrapper.text()).toContain('3375.0000')
    expect(wrapper.text()).toContain('3.38%')
    expect(wrapper.text()).toContain('2026-07-18')
    expect(wrapper.text()).toContain('2026-07-19T08:30:00+08:00')
  })

  it('renders every position field, null targets, and valuation warnings inline', async () => {
    installPortfolioLoad()
    const wrapper = mountView()
    await flushPromises()

    for (const text of [
      '000001', '平安银行', '银行', '300', '10.0001', '11.2500',
      '3375.0000', '374.9700', '3.38%', '5.00%',
      '组合中有一只股票缺少当日行情', '该股票使用上一交易日收盘价',
      '缺少最新估值',
    ]) expect(wrapper.text()).toContain(text)
    expect(wrapper.get('[data-testid="position-target-000002"]').text()).toBe('—')
  })

  it('test_profile_edit_creates_new_version', async () => {
    const { store } = installPortfolioLoad()
    const update = vi.spyOn(store, 'updateProfile').mockResolvedValue(profile(2))
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[data-testid="portfolio-profile-edit"]').trigger('click')
    await setInput('#profile-horizon-days', '240')
    await setInput('#profile-max-drawdown', '20')
    await setInput('#profile-max-stock-weight', '10')
    await setInput('#profile-max-industry-weight', '30')
    await setInput('#profile-min-cash-ratio', '15')
    await setInput('#profile-max-daily-turnover', '40')
    await click('[data-testid="profile-submit"]')

    expect(update).toHaveBeenCalledWith({
      investment_horizon_days: 240,
      risk_level: 'balanced',
      max_drawdown: 0.2,
      max_stock_weight: 0.1,
      max_industry_weight: 0.3,
      min_cash_ratio: 0.15,
      max_daily_turnover: 0.4,
    })
    expect(wrapper.text()).toContain('画像版本 2')
  })

  it('profile errors keep values and show structured detail', async () => {
    const { store } = installPortfolioLoad()
    vi.spyOn(store, 'updateProfile').mockRejectedValue(
      new ApiError('画像保存失败', { reason: '约束范围不允许' }, 422),
    )
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[data-testid="portfolio-profile-edit"]').trigger('click')
    await setInput('#profile-horizon-days', '240')
    await click('[data-testid="profile-submit"]')

    expect(document.body.textContent).toContain('画像保存失败')
    expect(document.body.textContent).toContain('约束范围不允许')
    expect(getElement<HTMLInputElement>('#profile-horizon-days').value).toBe('240')
  })

  it('test_reconcile_sends_current_updated_at', async () => {
    const opened = portfolio('2026-07-19T09:00:00+08:00')
    const { store } = installPortfolioLoad(opened)
    const reconcile = vi.spyOn(store, 'reconcileHoldings').mockResolvedValue(opened)
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[data-testid="portfolio-reconcile"]').trigger('click')
    store.portfolio = portfolio('2026-07-19T10:00:00+08:00')
    await setInput('#portfolio-cash', '96625.12340001')
    await click('[data-testid="reconcile-submit"]')

    expect(reconcile).toHaveBeenCalledWith({
      expected_updated_at: '2026-07-19T09:00:00+08:00',
      cash: '96625.12340001',
      positions: [
        { symbol: '000001', quantity: 300, average_cost: '10.0001' },
        { symbol: '000002', quantity: 100, average_cost: '8.50' },
      ],
    })
  })

  it('test_conflict_refreshes_without_dropping_edits', async () => {
    const initial = portfolio('2026-07-19T09:00:00+08:00')
    const latest = portfolio('2026-07-19T10:00:00+08:00')
    const store = usePortfolioStore()
    const load = vi.spyOn(store, 'loadPortfolio')
      .mockImplementationOnce(async () => { store.portfolio = initial; return initial })
      .mockImplementationOnce(async () => { store.portfolio = latest; return latest })
    const reconcile = vi.spyOn(store, 'reconcileHoldings')
      .mockRejectedValueOnce(
        new ApiError('组合已更新', { current_updated_at: latest.updated_at }, 409),
      )
      .mockResolvedValueOnce(latest)
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[data-testid="portfolio-reconcile"]').trigger('click')
    await setInput('#portfolio-cash', '95555.0001')
    await setInput('#holding-cost-0', '10.9999')
    await click('[data-testid="reconcile-submit"]')

    expect(reconcile).toHaveBeenCalledOnce()
    expect(load).toHaveBeenCalledTimes(2)
    expect(document.body.textContent).toContain('核对差异后重试')
    expect(document.body.textContent).toContain(latest.updated_at)
    expect(getElement<HTMLInputElement>('#portfolio-cash').value).toBe('95555.0001')
    expect(getElement<HTMLInputElement>('#holding-cost-0').value).toBe('10.9999')

    await click('[data-testid="reconcile-adopt-latest"]')
    expect(reconcile).toHaveBeenCalledOnce()
    expect(getElement<HTMLInputElement>('#portfolio-cash').value).toBe('95555.0001')
    expect(getElement<HTMLInputElement>('#holding-cost-0').value).toBe('10.9999')
    await click('[data-testid="reconcile-submit"]')

    expect(reconcile).toHaveBeenCalledTimes(2)
    expect(reconcile).toHaveBeenNthCalledWith(2, {
      expected_updated_at: latest.updated_at,
      cash: '95555.0001',
      positions: [
        { symbol: '000001', quantity: 300, average_cost: '10.9999' },
        { symbol: '000002', quantity: 100, average_cost: '8.50' },
      ],
    })
  })

  it('test_cash_movement_requires_positive_amount', async () => {
    const { store } = installPortfolioLoad()
    const record = vi.spyOn(store, 'recordCashMovement').mockResolvedValue(portfolio())
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[data-testid="portfolio-cash-movement"]').trigger('click')
    await setInput('#cash-amount', ' 1.00 ')
    await click('[data-testid="cash-movement-submit"]')

    expect(document.body.textContent).toContain('请输入规范的正数金额')
    expect(record).not.toHaveBeenCalled()
    expect(getElement<HTMLInputElement>('#cash-amount').value).toBe(' 1.00 ')
  })

  it('sends an exact cash amount and converts local occurrence time to aware ISO', async () => {
    const { store } = installPortfolioLoad()
    const record = vi.spyOn(store, 'recordCashMovement').mockResolvedValue(portfolio())
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[data-testid="portfolio-cash-movement"]').trigger('click')
    await setInput('#cash-kind', 'fee')
    await setInput('#cash-amount', '5.00010000')
    await setInput('#cash-occurred-at', '2026-07-19T10:30')
    await setInput('#cash-note', '手工费用')
    await click('[data-testid="cash-movement-submit"]')

    expect(record).toHaveBeenCalledWith({
      kind: 'fee',
      amount: '5.00010000',
      occurred_at: new Date('2026-07-19T10:30').toISOString(),
      note: '手工费用',
    })
  })

  it('cash movement errors keep values and show detail', async () => {
    const { store } = installPortfolioLoad()
    vi.spyOn(store, 'recordCashMovement').mockRejectedValue(
      new ApiError('现金流水保存失败', { available_cash: '1.0001' }, 422),
    )
    const wrapper = mountView()
    await flushPromises()

    await wrapper.get('[data-testid="portfolio-cash-movement"]').trigger('click')
    await setInput('#cash-amount', '5.0001')
    await setInput('#cash-occurred-at', '2026-07-19T10:30')
    await click('[data-testid="cash-movement-submit"]')

    expect(document.body.textContent).toContain('现金流水保存失败')
    expect(document.body.textContent).toContain('1.0001')
    expect(getElement<HTMLInputElement>('#cash-amount').value).toBe('5.0001')
  })
})
