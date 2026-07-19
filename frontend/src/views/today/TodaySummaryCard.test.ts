import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import TodaySummaryCard from './TodaySummaryCard.vue'
import { dailyAdvice } from './test-fixtures'

describe('TodaySummaryCard', () => {
  it('renders every advice summary field without changing exact money strings', () => {
    const wrapper = mount(TodaySummaryCard, { props: { advice: dailyAdvice() } })

    for (const text of [
      '100000.0100',
      '42.00%',
      '58.00%',
      '58000.0001',
      '42000.0099',
      '2026-07-18',
      '下一交易日',
      '2026-07-18T18:30:00+08:00',
      'model-v3',
      '部分行情使用上一交易日数据',
      'turnover_relaxed',
    ]) expect(wrapper.text()).toContain(text)
  })
})
