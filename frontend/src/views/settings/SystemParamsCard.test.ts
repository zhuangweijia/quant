import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { settingsApi, type SystemParams } from '@/api/settings'
import SystemParamsCard from './SystemParamsCard.vue'

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const defaults: SystemParams = {
  data_retention_days: 90,
  alert_retention_days: 90,
  model_train_window_days: 756,
  model_val_window_days: 126,
  forward_return_days: 5,
  forward_return_threshold: 0.02,
  model_ic_threshold: 0.02,
  stock_universe: 'csi300',
  analysis_time: '17:00',
}

function mountCard() {
  return mount(SystemParamsCard, { attachTo: document.body })
}

describe('SystemParamsCard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(settingsApi, 'getParams').mockResolvedValue({ data: defaults } as never)
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('saves a validated complete parameter object', async () => {
    const update = vi
      .spyOn(settingsApi, 'updateParams')
      .mockResolvedValue({ data: { ...defaults, analysis_time: '18:15' } } as never)
    const wrapper = mountCard()
    await flushPromises()
    await wrapper.get('#analysis-time').setValue('18:15')
    await wrapper.get('[data-testid="system-params-save"]').trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith(
      expect.objectContaining({ analysis_time: '18:15', stock_universe: 'csi300' }),
    )
  })

  it('prevents validation windows from matching the training window', async () => {
    const wrapper = mountCard()
    await flushPromises()
    await wrapper.get('#model-val-window').setValue('756')
    expect(wrapper.text()).toContain('验证窗口必须短于训练窗口')
    expect(
      wrapper.get('[data-testid="system-params-save"]').attributes('disabled'),
    ).toBeDefined()
  })

  it('maps backend validation detail to the matching field', async () => {
    vi.spyOn(settingsApi, 'updateParams').mockRejectedValue(
      new ApiError('参数校验失败', [
        {
          loc: ['body', 'params', 'analysis_time'],
          msg: '分析时间不可用',
          type: 'value_error',
        },
      ]),
    )
    const wrapper = mountCard()
    await flushPromises()
    await wrapper.get('#analysis-time').setValue('18:15')
    await wrapper.get('[data-testid="system-params-save"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('分析时间不可用')
  })

  it('replaces the form with the server reset response', async () => {
    vi.spyOn(settingsApi, 'resetParams').mockResolvedValue({ data: defaults } as never)
    const wrapper = mountCard()
    await flushPromises()
    await wrapper.get('#analysis-time').setValue('18:15')
    await wrapper.get('[data-testid="system-params-reset"]').trigger('click')
    await flushPromises()
    document.querySelector<HTMLButtonElement>('[data-testid="system-params-reset-confirm"]')?.click()
    await flushPromises()
    expect((wrapper.get('#analysis-time').element as HTMLInputElement).value).toBe('17:00')
  })
})
