import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SetupStatusCard from './SetupStatusCard.vue'

const emptyStatus = {
  readiness: 'uninitialized' as const,
  counts: { stocks: 0, daily_bars: 0, models: 0, today_predictions: 0 },
  active_model: null,
  run: null,
  can_start: true,
  can_run_analysis: false,
}

describe('SetupStatusCard', () => {
  it('does not show setup controls to ordinary users', () => {
    const wrapper = mount(SetupStatusCard, {
      props: {
        status: emptyStatus,
        isAdmin: false,
        starting: false,
        analysisRunning: false,
      },
    })

    expect(wrapper.find('[data-testid="setup-primary-action"]').exists()).toBe(false)
  })

  it('emits start when an administrator starts first-time setup', async () => {
    const wrapper = mount(SetupStatusCard, {
      props: {
        status: emptyStatus,
        isAdmin: true,
        starting: false,
        analysisRunning: false,
      },
    })

    await wrapper.get('[data-testid="setup-primary-action"]').trigger('click')

    expect(wrapper.emitted('start')).toHaveLength(1)
  })
})
