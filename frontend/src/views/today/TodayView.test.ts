import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useAdviceStore } from '@/stores/advice'
import { useAuthStore } from '@/stores/auth'
import { usePortfolioStore } from '@/stores/portfolio'
import type { AdviceTodayResponse } from '@/types/advice'
import TodayView from './TodayView.vue'
import { dailyAdvice } from './test-fixtures'

const replace = vi.fn()
const subscribe = vi.fn()
const unsubscribe = vi.fn()
const off = vi.fn()
let readyHandler: ((event: unknown) => void) | undefined

vi.mock('vue-router', () => ({ useRouter: () => ({ replace }) }))
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    subscribe,
    unsubscribe,
    onMessage: vi.fn((_type: string, handler: (event: unknown) => void) => {
      readyHandler = handler
      return off
    }),
  }),
}))

const mounted: VueWrapper[] = []

function mountView() {
  const wrapper = mount(TodayView, {
    global: {
      stubs: {
        TodaySummaryCard: { props: ['advice'], template: '<div data-testid="summary">summary</div>' },
        AdviceActionList: { props: ['items'], template: '<div data-testid="actions">actions</div>' },
        ExecutionDialog: { template: '<div data-testid="execution-dialog" />' },
      },
    },
  })
  mounted.push(wrapper)
  return wrapper
}

function state(value: AdviceTodayResponse) {
  const adviceStore = useAdviceStore()
  vi.spyOn(adviceStore, 'loadToday').mockImplementation(async () => {
    adviceStore.today = value
    return value
  })
  return adviceStore
}

describe('TodayView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    readyHandler = undefined
    const authStore = useAuthStore()
    authStore.user = {
      id: 'user-1', username: 'tester', role: 'trader', is_active: true,
      created_at: '2026-07-01T00:00:00+08:00',
    }
  })

  afterEach(() => {
    for (const wrapper of mounted.splice(0)) wrapper.unmount()
    vi.restoreAllMocks()
  })

  it('awaits setup status before concurrently loading today and portfolio', async () => {
    const portfolioStore = usePortfolioStore()
    const adviceStore = useAdviceStore()
    const order: string[] = []
    let resolveSetup!: () => void
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockImplementation(async () => {
      order.push('setup:start')
      await new Promise<void>(resolve => { resolveSetup = resolve })
      portfolioStore.setupStatus = { complete: true, has_profile: true, has_portfolio: true, missing: [] }
      order.push('setup:end')
      return portfolioStore.setupStatus
    })
    vi.spyOn(adviceStore, 'loadToday').mockImplementation(async () => {
      order.push('today')
      adviceStore.today = { state: 'not_generated', setup_required: false, advice: null, error_code: null, error_message: null }
      return adviceStore.today
    })
    vi.spyOn(portfolioStore, 'loadPortfolio').mockImplementation(async () => {
      order.push('portfolio')
      return {} as never
    })

    const wrapper = mountView()
    expect(wrapper.text()).toContain('正在检查组合设置')
    expect(order).toEqual(['setup:start'])
    readyHandler?.({ user_id: 'user-1' })
    await flushPromises()
    expect(order).toEqual(['setup:start'])
    resolveSetup()
    await flushPromises()
    expect(order).toEqual(['setup:start', 'setup:end', 'today', 'portfolio'])
  })

  it.each([
    ['not_generated', '尚未生成今日建议', '生成首份建议'],
    ['generating', '建议生成中', ''],
    ['ready', 'summary', 'actions'],
    ['partially_handled', 'summary', 'actions'],
    ['handled', '今日建议已处理', 'summary'],
    ['expired', '建议已过期', 'summary'],
    ['failed', '模型输入缺失', '重试生成'],
  ] as const)('renders %s without conflating it with an empty list', async (kind, expected, second) => {
    const advice = dailyAdvice({
      status: kind === 'partially_handled' ? 'partially_handled' :
        kind === 'handled' ? 'handled' : kind === 'expired' ? 'expired' :
          kind === 'failed' ? 'failed' : kind === 'generating' ? 'generating' : 'ready',
      error_message: kind === 'failed' ? '模型输入缺失' : null,
    })
    const response = kind === 'not_generated'
      ? { state: kind, setup_required: false, advice: null, error_code: null, error_message: null }
      : { state: kind, setup_required: false, advice, error_code: advice.error_code, error_message: advice.error_message }
    state(response as AdviceTodayResponse)
    const portfolioStore = usePortfolioStore()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: true, has_profile: true, has_portfolio: true, missing: [] },
    )
    vi.spyOn(portfolioStore, 'loadPortfolio').mockResolvedValue({} as never)

    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain(expected)
    if (second) expect(wrapper.text()).toContain(second)
    if (kind === 'generating') expect(wrapper.find('[data-testid="actions"]').exists()).toBe(false)
  })

  it('redirects setup_required exactly once whether it comes from setup or today', async () => {
    const portfolioStore = usePortfolioStore()
    const adviceStore = useAdviceStore()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: false, has_profile: true, has_portfolio: false, missing: ['portfolio'] },
    )
    const todayLoad = vi.spyOn(adviceStore, 'loadToday')
    const portfolioLoad = vi.spyOn(portfolioStore, 'loadPortfolio')
    mountView()
    await flushPromises()
    expect(replace).toHaveBeenCalledOnce()
    expect(replace).toHaveBeenCalledWith('/portfolio/setup')
    expect(todayLoad).not.toHaveBeenCalled()
    expect(portfolioLoad).not.toHaveBeenCalled()

    vi.clearAllMocks()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: true, has_profile: true, has_portfolio: true, missing: [] },
    )
    vi.spyOn(adviceStore, 'loadToday').mockResolvedValue({
      state: 'not_generated', setup_required: true, advice: null,
      error_code: 'setup_required', error_message: '请完成组合设置',
    })
    vi.spyOn(portfolioStore, 'loadPortfolio').mockResolvedValue({} as never)
    mountView()
    await flushPromises()
    expect(replace).toHaveBeenCalledOnce()
    expect(replace).toHaveBeenCalledWith('/portfolio/setup')
  })

  it('shows request errors and retries without rendering not-generated actions', async () => {
    const portfolioStore = usePortfolioStore()
    const adviceStore = useAdviceStore()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: true, has_profile: true, has_portfolio: true, missing: [] },
    )
    const loadToday = vi.spyOn(adviceStore, 'loadToday')
      .mockRejectedValueOnce(new Error('今日服务不可用'))
      .mockImplementationOnce(async () => {
        adviceStore.today = { state: 'not_generated', setup_required: false, advice: null, error_code: null, error_message: null }
        return adviceStore.today
      })
    vi.spyOn(portfolioStore, 'loadPortfolio').mockResolvedValue({} as never)
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('今日服务不可用')
    expect(wrapper.text()).not.toContain('生成首份建议')
    await wrapper.get('[data-testid="today-retry"]').trigger('click')
    await flushPromises()
    expect(loadToday).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('生成首份建议')
  })

  it('generates first advice, retries failures, and filters ready events by current user', async () => {
    const response: AdviceTodayResponse = {
      state: 'not_generated', setup_required: false, advice: null, error_code: null, error_message: null,
    }
    const adviceStore = state(response)
    const portfolioStore = usePortfolioStore()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: true, has_profile: true, has_portfolio: true, missing: [] },
    )
    vi.spyOn(portfolioStore, 'loadPortfolio').mockResolvedValue({} as never)
    const generate = vi.spyOn(adviceStore, 'generate').mockResolvedValue(dailyAdvice())
    const wrapper = mountView()
    await flushPromises()

    expect(subscribe).toHaveBeenCalledWith('advice:ready')
    await wrapper.get('[data-testid="generate-advice"]').trigger('click')
    expect(generate).toHaveBeenCalledWith(false)

    const initialLoads = vi.mocked(adviceStore.loadToday).mock.calls.length
    readyHandler?.({ user_id: 'other-user' })
    readyHandler?.({})
    await flushPromises()
    expect(adviceStore.loadToday).toHaveBeenCalledTimes(initialLoads)
    readyHandler?.({ user_id: 'user-1' })
    await flushPromises()
    expect(adviceStore.loadToday).toHaveBeenCalledTimes(initialLoads + 1)

    wrapper.unmount()
    expect(off).toHaveBeenCalledOnce()
    expect(unsubscribe).toHaveBeenCalledWith('advice:ready')
  })
})
