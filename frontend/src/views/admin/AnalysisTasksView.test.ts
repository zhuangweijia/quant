import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { analysisApi } from '@/api/analysis'
import { setupApi } from '@/api/setup'
import AnalysisTasksView from './AnalysisTasksView.vue'

vi.mock('@/api/analysis', () => ({
  analysisApi: {
    getStatus: vi.fn(),
    trigger: vi.fn(),
  },
}))

vi.mock('@/api/setup', () => ({
  setupApi: {
    getStatus: vi.fn(),
    start: vi.fn(),
  },
}))

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({
    subscribe: vi.fn(),
    onMessage: vi.fn(() => vi.fn()),
  }),
}))

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe('AnalysisTasksView', () => {
  beforeEach(() => {
    vi.mocked(setupApi.getStatus).mockResolvedValue({
      data: {
        data: {
          readiness: 'ready',
          counts: { stocks: 300, daily_bars: 1000, models: 1, today_predictions: 10 },
          active_model: 'model-v1',
          run: null,
          can_start: false,
          can_run_analysis: true,
        },
      },
    } as never)
    vi.mocked(analysisApi.getStatus).mockResolvedValue({
      data: {
        data: {
          run_id: 'run-1',
          trigger_type: 'manual',
          status: 'running',
          stages: {
            data_sync: { status: 'done' },
            ranking: { status: 'running' },
          },
          started_at: null,
          finished_at: null,
          error: null,
        },
      },
    } as never)
  })

  it('shows setup and pipeline operations without recommendation cards', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
    })
    await router.push('/admin/tasks')
    await router.isReady()

    const wrapper = mount(AnalysisTasksView, {
      global: {
        plugins: [createPinia(), router],
        stubs: {
          SetupStatusCard: {
            template: '<section data-testid="setup-status">首次配置状态</section>',
          },
        },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('分析任务')
    expect(wrapper.find('[data-testid="setup-status"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('分析 Pipeline')
    expect(wrapper.text()).toContain('数据同步')
    expect(wrapper.text()).toContain('排名生成')
    expect(wrapper.text()).not.toContain('今日强推 Top 10')
    expect(wrapper.text()).not.toContain('强推股票')
    wrapper.unmount()
  })
})
