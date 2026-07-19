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
const onMessage = vi.fn()
let readyHandler: ((event: unknown) => void) | undefined

vi.mock('vue-router', () => ({ useRouter: () => ({ replace }) }))
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    subscribe,
    unsubscribe,
    onMessage,
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
    subscribe.mockImplementation(() => undefined)
    onMessage.mockImplementation((_type: string, handler: (event: unknown) => void) => {
      readyHandler = handler
      return off
    })
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
    onMessage.mockImplementation((_type: string, handler: (event: unknown) => void) => {
      order.push('handler')
      readyHandler = handler
      return off
    })
    subscribe.mockImplementation(() => { order.push('subscribe') })

    const wrapper = mountView()
    expect(wrapper.text()).toContain('正在检查组合设置')
    expect(order).toEqual(['setup:start'])
    expect(onMessage).not.toHaveBeenCalled()
    expect(subscribe).not.toHaveBeenCalled()
    expect(order).toEqual(['setup:start'])
    resolveSetup()
    await flushPromises()
    expect(order).toEqual([
      'setup:start', 'setup:end', 'handler', 'subscribe', 'today', 'portfolio',
    ])
    expect(onMessage).toHaveBeenCalledOnce()
    expect(subscribe).toHaveBeenCalledOnce()
  })

  it('does not register or clean websocket resources for incomplete setup', async () => {
    const portfolioStore = usePortfolioStore()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: false, has_profile: true, has_portfolio: false, missing: ['portfolio'] },
    )
    const wrapper = mountView()
    await flushPromises()

    expect(onMessage).not.toHaveBeenCalled()
    expect(subscribe).not.toHaveBeenCalled()
    wrapper.unmount()
    expect(off).not.toHaveBeenCalled()
    expect(unsubscribe).not.toHaveBeenCalled()
  })

  it('does not register or fake cleanup when unmounted before setup finishes', async () => {
    const portfolioStore = usePortfolioStore()
    let resolveSetup!: () => void
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockImplementation(async () => {
      await new Promise<void>(resolve => { resolveSetup = resolve })
      return { complete: true, has_profile: true, has_portfolio: true, missing: [] }
    })
    const wrapper = mountView()

    wrapper.unmount()
    expect(off).not.toHaveBeenCalled()
    expect(unsubscribe).not.toHaveBeenCalled()
    resolveSetup()
    await flushPromises()
    expect(onMessage).not.toHaveBeenCalled()
    expect(subscribe).not.toHaveBeenCalled()
  })

  it('does not redirect when pending setup resolves incomplete after unmount', async () => {
    const portfolioStore = usePortfolioStore()
    let resolveSetup!: () => void
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockImplementation(async () => {
      await new Promise<void>(resolve => { resolveSetup = resolve })
      return { complete: false, has_profile: true, has_portfolio: false, missing: ['portfolio'] }
    })
    const wrapper = mountView()

    wrapper.unmount()
    resolveSetup()
    await flushPromises()
    expect(replace).not.toHaveBeenCalled()
    expect(onMessage).not.toHaveBeenCalled()
    expect(subscribe).not.toHaveBeenCalled()
    expect(off).not.toHaveBeenCalled()
    expect(unsubscribe).not.toHaveBeenCalled()
  })

  it('cleans registered websocket resources before redirecting from today setup_required', async () => {
    const portfolioStore = usePortfolioStore()
    const adviceStore = useAdviceStore()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: true, has_profile: true, has_portfolio: true, missing: [] },
    )
    vi.spyOn(adviceStore, 'loadToday').mockResolvedValue({
      state: 'not_generated', setup_required: true, advice: null,
      error_code: 'setup_required', error_message: '请先初始化组合',
    })
    vi.spyOn(portfolioStore, 'loadPortfolio').mockResolvedValue({} as never)
    const wrapper = mountView()
    await flushPromises()

    expect(onMessage).toHaveBeenCalledOnce()
    expect(subscribe).toHaveBeenCalledOnce()
    expect(replace).toHaveBeenCalledWith('/portfolio/setup')
    expect(off).toHaveBeenCalledOnce()
    expect(unsubscribe).toHaveBeenCalledOnce()
    wrapper.unmount()
    expect(off).toHaveBeenCalledOnce()
    expect(unsubscribe).toHaveBeenCalledOnce()
  })

  it('prioritizes today setup_required redirect when the concurrent portfolio load fails', async () => {
    const portfolioStore = usePortfolioStore()
    const adviceStore = useAdviceStore()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: true, has_profile: true, has_portfolio: true, missing: [] },
    )
    vi.spyOn(adviceStore, 'loadToday').mockResolvedValue({
      state: 'not_generated', setup_required: true, advice: null,
      error_code: 'setup_required', error_message: '请先初始化组合',
    })
    vi.spyOn(portfolioStore, 'loadPortfolio').mockRejectedValue(new Error('持仓刷新失败'))
    const wrapper = mountView()
    await flushPromises()

    expect(replace).toHaveBeenCalledWith('/portfolio/setup')
    expect(off).toHaveBeenCalledOnce()
    expect(unsubscribe).toHaveBeenCalledOnce()
    wrapper.unmount()
    expect(off).toHaveBeenCalledOnce()
    expect(unsubscribe).toHaveBeenCalledOnce()
  })

  it('does not redirect from completed requests after unmount', async () => {
    const portfolioStore = usePortfolioStore()
    const adviceStore = useAdviceStore()
    let resolveToday!: (value: AdviceTodayResponse) => void
    let resolvePortfolio!: () => void
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: true, has_profile: true, has_portfolio: true, missing: [] },
    )
    vi.spyOn(adviceStore, 'loadToday').mockReturnValue(
      new Promise(resolve => { resolveToday = resolve }),
    )
    vi.spyOn(portfolioStore, 'loadPortfolio').mockReturnValue(
      new Promise(resolve => { resolvePortfolio = () => resolve({} as never) }),
    )
    const wrapper = mountView()
    await flushPromises()
    expect(onMessage).toHaveBeenCalledOnce()
    expect(subscribe).toHaveBeenCalledOnce()

    wrapper.unmount()
    expect(off).toHaveBeenCalledOnce()
    expect(unsubscribe).toHaveBeenCalledOnce()
    resolveToday({
      state: 'not_generated', setup_required: true, advice: null,
      error_code: 'setup_required', error_message: '请先初始化组合',
    })
    resolvePortfolio()
    await flushPromises()
    expect(replace).not.toHaveBeenCalled()
  })

  it('removes a registered handler when channel subscription throws', async () => {
    const portfolioStore = usePortfolioStore()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: true, has_profile: true, has_portfolio: true, missing: [] },
    )
    subscribe.mockImplementation(() => { throw new Error('订阅失败') })
    const wrapper = mountView()
    await flushPromises()

    expect(onMessage).toHaveBeenCalledOnce()
    expect(subscribe).toHaveBeenCalledOnce()
    expect(off).toHaveBeenCalledOnce()
    expect(unsubscribe).not.toHaveBeenCalled()
    wrapper.unmount()
    expect(off).toHaveBeenCalledOnce()
    expect(unsubscribe).not.toHaveBeenCalled()
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

  it('shows a non-blocking execution refresh warning and retries both latest states', async () => {
    const response: AdviceTodayResponse = {
      state: 'ready', setup_required: false, advice: dailyAdvice(),
      error_code: null, error_message: null,
    }
    const adviceStore = state(response)
    const portfolioStore = usePortfolioStore()
    vi.spyOn(portfolioStore, 'loadSetupStatus').mockResolvedValue(
      { complete: true, has_profile: true, has_portfolio: true, missing: [] },
    )
    vi.spyOn(portfolioStore, 'loadPortfolio').mockResolvedValue({} as never)
    const wrapper = mountView()
    await flushPromises()
    const todayCalls = vi.mocked(adviceStore.loadToday).mock.calls.length
    const portfolioCalls = vi.mocked(portfolioStore.loadPortfolio).mock.calls.length

    adviceStore.error = '执行已记录，但刷新最新状态失败，请重试刷新'
    await flushPromises()
    expect(wrapper.get('[data-testid="execution-refresh-warning"]').text())
      .toContain('执行已记录，但刷新最新状态失败，请重试刷新')

    await wrapper.get('[data-testid="execution-refresh-retry"]').trigger('click')
    await flushPromises()
    expect(adviceStore.loadToday).toHaveBeenCalledTimes(todayCalls + 1)
    expect(portfolioStore.loadPortfolio).toHaveBeenCalledTimes(portfolioCalls + 1)
    expect(wrapper.find('[data-testid="execution-refresh-warning"]').exists()).toBe(false)
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
