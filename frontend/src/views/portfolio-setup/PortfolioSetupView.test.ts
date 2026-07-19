import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { usePortfolioStore } from '@/stores/portfolio'
import PortfolioSetupView from './PortfolioSetupView.vue'

const DRAFT_KEY = 'quant-desk:portfolio-setup:v1'
const push = vi.fn()

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))

function mountView() {
  return mount(PortfolioSetupView, { attachTo: document.body })
}

function validStoredDraft(): Record<string, any> {
  return {
    version: 1,
    currentStep: 2,
    profile: {
      investmentHorizonDays: '240',
      riskLevel: 'conservative',
      maxDrawdown: '10',
      maxStockWeight: '5',
      maxIndustryWeight: '20',
      minCashRatio: '20',
      maxDailyTurnover: '20',
    },
    totalCapital: '200000.00',
    cash: '150000.00',
    positions: [
      { symbol: '000001', quantity: 100, average_cost: '12.00' },
    ],
  }
}

async function goToConstraints(wrapper: VueWrapper) {
  await wrapper.get('[data-testid="setup-next"]').trigger('click')
}

async function goToHoldings(wrapper: VueWrapper) {
  await goToConstraints(wrapper)
  await wrapper.get('[data-testid="setup-next"]').trigger('click')
}

async function goToConfirmation(wrapper: VueWrapper) {
  await goToHoldings(wrapper)
  await wrapper.get('#total-capital').setValue('100000.0001')
  await wrapper.get('#portfolio-cash').setValue('100000.0001')
  await wrapper.get('[data-testid="setup-next"]').trigger('click')
}

describe('PortfolioSetupView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockReset()
    localStorage.clear()
  })

  afterEach(() => {
    document.body.innerHTML = ''
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('cannot submit until every step is valid', () => {
    const wrapper = mountView()

    expect(wrapper.get('[data-testid="setup-submit"]').attributes('disabled')).toBeDefined()
  })

  it('submits one atomic exact-string setup payload and opens today', async () => {
    const store = usePortfolioStore()
    const completeSetup = vi.spyOn(store, 'completeSetup').mockResolvedValue({} as never)
    const wrapper = mountView()

    await wrapper.get('#risk-level').setValue('balanced')
    await wrapper.get('#horizon-days').setValue('120')
    await wrapper.get('#max-drawdown').setValue('15')
    await goToConstraints(wrapper)
    await wrapper.get('#max-stock-weight').setValue('8')
    await wrapper.get('#max-industry-weight').setValue('25')
    await wrapper.get('#min-cash-ratio').setValue('10')
    await wrapper.get('#max-daily-turnover').setValue('30')
    await wrapper.get('[data-testid="setup-next"]').trigger('click')
    await wrapper.get('#total-capital').setValue('100000.0001')
    await wrapper.get('#portfolio-cash').setValue('90000.0001')
    await wrapper.get('[data-testid="holding-add"]').trigger('click')
    await wrapper.get('#holding-symbol-0').setValue('000001')
    await wrapper.get('#holding-quantity-0').setValue('100')
    await wrapper.get('#holding-cost-0').setValue('10.0001')
    await wrapper.get('[data-testid="setup-next"]').trigger('click')
    await wrapper.get('[data-testid="setup-submit"]').trigger('click')
    await flushPromises()

    expect(completeSetup).toHaveBeenCalledWith({
      profile: {
        investment_horizon_days: 120,
        risk_level: 'balanced',
        max_drawdown: 0.15,
        max_stock_weight: 0.08,
        max_industry_weight: 0.25,
        min_cash_ratio: 0.1,
        max_daily_turnover: 0.3,
      },
      total_capital: '100000.0001',
      cash: '90000.0001',
      positions: [
        { symbol: '000001', quantity: 100, average_cost: '10.0001' },
      ],
    })
    expect(localStorage.getItem(DRAFT_KEY)).toBeNull()
    expect(push).toHaveBeenCalledWith('/today')
  })

  it('test_duplicate_symbols_block_next_step', async () => {
    const wrapper = mountView()
    await goToHoldings(wrapper)
    await wrapper.get('#total-capital').setValue('100000')
    await wrapper.get('#portfolio-cash').setValue('80000')
    await wrapper.get('[data-testid="holding-add"]').trigger('click')
    await wrapper.get('[data-testid="holding-add"]').trigger('click')
    await wrapper.get('#holding-symbol-0').setValue('000001')
    await wrapper.get('#holding-quantity-0').setValue('100')
    await wrapper.get('#holding-cost-0').setValue('10')
    await wrapper.get('#holding-symbol-1').setValue('000001')
    await wrapper.get('#holding-quantity-1').setValue('200')
    await wrapper.get('#holding-cost-1').setValue('11')

    expect(wrapper.text()).toContain('持仓股票代码不能重复')
    expect(wrapper.get('[data-testid="setup-next"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="setup-next"]').trigger('click')
    expect(wrapper.text()).toContain('资金与持仓')
  })

  it('rejects surrounding whitespace without rewriting setup inputs', async () => {
    const store = usePortfolioStore()
    const completeSetup = vi.spyOn(store, 'completeSetup').mockResolvedValue({} as never)
    const wrapper = mountView()
    await goToHoldings(wrapper)
    await wrapper.get('#total-capital').setValue(' 100000.00 ')
    await wrapper.get('#portfolio-cash').setValue(' 90000.00 ')
    await wrapper.get('[data-testid="holding-add"]').trigger('click')
    await wrapper.get('#holding-symbol-0').setValue(' 000001 ')
    await wrapper.get('#holding-quantity-0').setValue('100')
    await wrapper.get('#holding-cost-0').setValue(' 10.00 ')
    await wrapper.get('#holding-symbol-0').trigger('blur')

    expect((wrapper.get('#total-capital').element as HTMLInputElement).value).toBe(
      ' 100000.00 ',
    )
    expect((wrapper.get('#portfolio-cash').element as HTMLInputElement).value).toBe(
      ' 90000.00 ',
    )
    expect((wrapper.get('#holding-symbol-0').element as HTMLInputElement).value).toBe(
      ' 000001 ',
    )
    expect((wrapper.get('#holding-cost-0').element as HTMLInputElement).value).toBe(
      ' 10.00 ',
    )
    expect(wrapper.text()).toContain('总资金必须是大于 0 的十进制数')
    expect(wrapper.text()).toContain('可用现金必须是非负十进制数')
    expect(wrapper.text()).toContain('股票代码必须是六位数字')
    expect(wrapper.text()).toContain('平均成本必须是大于 0 的十进制数')
    expect(wrapper.get('[data-testid="setup-next"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="setup-next"]').trigger('click')
    expect(wrapper.text()).toContain('资金与持仓')
    expect(completeSetup).not.toHaveBeenCalled()
    expect(localStorage.getItem(DRAFT_KEY)).toContain(' 100000.00 ')
  })

  it('restores whitespace exactly and blocks confirmation submit', async () => {
    const store = usePortfolioStore()
    const completeSetup = vi.spyOn(store, 'completeSetup').mockResolvedValue({} as never)
    localStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({
        version: 1,
        currentStep: 3,
        profile: {
          investmentHorizonDays: '120',
          riskLevel: 'balanced',
          maxDrawdown: '15',
          maxStockWeight: '8',
          maxIndustryWeight: '25',
          minCashRatio: '10',
          maxDailyTurnover: '30',
        },
        totalCapital: ' 100000.00 ',
        cash: ' 90000.00 ',
        positions: [
          { symbol: ' 000001 ', quantity: 100, average_cost: ' 10.00 ' },
        ],
      }),
    )
    const wrapper = mountView()

    expect(wrapper.text()).toContain('确认')
    expect(wrapper.get('[data-testid="setup-submit"]').attributes('disabled')).toBeDefined()
    await wrapper.get('[data-testid="setup-submit"]').trigger('click')
    expect(completeSetup).not.toHaveBeenCalled()
    await wrapper.get('[data-testid="setup-back"]').trigger('click')
    expect((wrapper.get('#total-capital').element as HTMLInputElement).value).toBe(
      ' 100000.00 ',
    )
    expect((wrapper.get('#portfolio-cash').element as HTMLInputElement).value).toBe(
      ' 90000.00 ',
    )
    expect((wrapper.get('#holding-symbol-0').element as HTMLInputElement).value).toBe(
      ' 000001 ',
    )
    expect((wrapper.get('#holding-cost-0').element as HTMLInputElement).value).toBe(
      ' 10.00 ',
    )
  })

  it('test_server_valuation_error_keeps_form', async () => {
    const store = usePortfolioStore()
    vi.spyOn(store, 'completeSetup').mockRejectedValue(
      new ApiError('总资金与服务端估值不一致', {
        server_valuation: '99888.8801',
        declared_total_capital: '100000.0001',
      }),
    )
    const wrapper = mountView()
    await goToConfirmation(wrapper)
    await wrapper.get('[data-testid="setup-submit"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('总资金与服务端估值不一致')
    expect(wrapper.text()).toContain('99888.8801')
    await wrapper.get('[data-testid="setup-back"]').trigger('click')
    expect((wrapper.get('#total-capital').element as HTMLInputElement).value).toBe(
      '100000.0001',
    )
    expect(localStorage.getItem(DRAFT_KEY)).toContain('100000.0001')
    expect(push).not.toHaveBeenCalled()
  })

  it('test_back_preserves_entered_values', async () => {
    const wrapper = mountView()
    await goToConstraints(wrapper)
    await wrapper.get('#max-stock-weight').setValue('7.5')
    await wrapper.get('[data-testid="setup-next"]').trigger('click')
    await wrapper.get('#total-capital').setValue('123456.7890')
    await wrapper.get('#portfolio-cash').setValue('123456.7890')
    await wrapper.get('[data-testid="setup-back"]').trigger('click')

    expect((wrapper.get('#max-stock-weight').element as HTMLInputElement).value).toBe('7.5')
    await wrapper.get('[data-testid="setup-next"]').trigger('click')
    expect((wrapper.get('#total-capital').element as HTMLInputElement).value).toBe(
      '123456.7890',
    )
  })

  it('test_saved_draft_restores_current_step', () => {
    localStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({
        version: 1,
        currentStep: 2,
        profile: {
          investmentHorizonDays: '240',
          riskLevel: 'conservative',
          maxDrawdown: '10',
          maxStockWeight: '5',
          maxIndustryWeight: '20',
          minCashRatio: '20',
          maxDailyTurnover: '20',
        },
        totalCapital: '200000.0001',
        cash: '150000.0001',
        positions: [
          { symbol: '000001', quantity: 100, average_cost: '12.0001' },
        ],
      }),
    )

    const wrapper = mountView()

    expect(wrapper.text()).toContain('资金与持仓')
    expect((wrapper.get('#total-capital').element as HTMLInputElement).value).toBe(
      '200000.0001',
    )
    expect((wrapper.get('#holding-symbol-0').element as HTMLInputElement).value).toBe(
      '000001',
    )
  })

  it.each([
    ['conservative', ['10', '5', '20', '20', '20'], '4.5'],
    ['balanced', ['15', '8', '25', '10', '30'], '7.5'],
    ['aggressive', ['25', '12', '35', '5', '50'], '11.5'],
  ] as const)(
    'fills the exact %s risk defaults while leaving constraints editable',
    async (riskLevel, defaults, editedStockWeight) => {
    const wrapper = mountView()

    await wrapper.get('#risk-level').setValue(riskLevel)
    expect((wrapper.get('#max-drawdown').element as HTMLInputElement).value).toBe(defaults[0])
    await goToConstraints(wrapper)
    expect((wrapper.get('#max-stock-weight').element as HTMLInputElement).value).toBe(defaults[1])
    expect((wrapper.get('#max-industry-weight').element as HTMLInputElement).value).toBe(defaults[2])
    expect((wrapper.get('#min-cash-ratio').element as HTMLInputElement).value).toBe(defaults[3])
    expect((wrapper.get('#max-daily-turnover').element as HTMLInputElement).value).toBe(defaults[4])
    await wrapper.get('#max-stock-weight').setValue(editedStockWeight)
    await wrapper.get('[data-testid="setup-back"]').trigger('click')
    await wrapper.get('[data-testid="setup-next"]').trigger('click')
    expect((wrapper.get('#max-stock-weight').element as HTMLInputElement).value).toBe(
      editedStockWeight,
    )
    },
  )

  it.each([
    JSON.stringify({ version: 2, currentStep: 3, token: 'secret', password: 'secret' }),
    '{not-valid-json',
  ])('ignores malformed or wrong-version drafts without restoring secrets', savedDraft => {
    localStorage.setItem(DRAFT_KEY, savedDraft)

    const wrapper = mountView()

    expect(wrapper.text()).toContain('风险与期限')
    expect(wrapper.text()).not.toContain('secret')
    const stored = localStorage.getItem(DRAFT_KEY) ?? ''
    expect(stored).not.toContain('token')
    expect(stored).not.toContain('password')
  })

  it.each([
    ['top-level token', (draft: Record<string, any>) => { draft.token = 'secret-top-token' }],
    ['top-level password', (draft: Record<string, any>) => { draft.password = 'secret-top-password' }],
    ['profile token', (draft: Record<string, any>) => { draft.profile.token = 'secret-profile-token' }],
    ['profile password', (draft: Record<string, any>) => { draft.profile.password = 'secret-profile-password' }],
    ['position token', (draft: Record<string, any>) => { draft.positions[0].token = 'secret-position-token' }],
    ['position password', (draft: Record<string, any>) => { draft.positions[0].password = 'secret-position-password' }],
  ] as const)(
    'rejects and removes a draft with an unknown %s key',
    async (_, addUnknownKey) => {
      const draft = validStoredDraft()
      addUnknownKey(draft)
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))

      const wrapper = mountView()

      expect(wrapper.text()).toContain('风险与期限')
      expect((wrapper.get('#risk-level').element as HTMLSelectElement).value).toBe('balanced')
      expect((wrapper.get('#horizon-days').element as HTMLInputElement).value).toBe('120')
      expect(localStorage.getItem(DRAFT_KEY)).toBeNull()

      await wrapper.get('#horizon-days').setValue('121')
      const nextDraft = localStorage.getItem(DRAFT_KEY) ?? ''
      expect(nextDraft).not.toContain('secret')
      expect(nextDraft).not.toContain('token')
      expect(nextDraft).not.toContain('password')
    },
  )
})
