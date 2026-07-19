import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AdviceActionList from './AdviceActionList.vue'
import { adviceItem, execution } from './test-fixtures'

describe('AdviceActionList', () => {
  it('orders exit, reduce, buy and increase cards before collapsed holds', async () => {
    const items = [
      adviceItem({ id: 'h', action: 'hold', symbol: '000005' }),
      adviceItem({ id: 'i', action: 'increase', symbol: '000004' }),
      adviceItem({ id: 'b', action: 'buy', symbol: '000003' }),
      adviceItem({ id: 'r', action: 'reduce', symbol: '000002' }),
      adviceItem({ id: 'x', action: 'exit', symbol: '000001' }),
    ]
    const wrapper = mount(AdviceActionList, { props: { items } })

    expect(wrapper.findAll('[data-testid="advice-action"]').map(node => node.attributes('data-action')))
      .toEqual(['exit', 'reduce', 'buy', 'increase'])
    expect(wrapper.text()).toContain('继续持有 1')
    expect(wrapper.find('[data-testid="hold-advice-h"]').exists()).toBe(false)

    await wrapper.get('[data-testid="toggle-holds"]').trigger('click')
    expect(wrapper.find('[data-testid="hold-advice-h"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="execute-h"]').exists()).toBe(false)
    for (const text of [
      '87.65%', 'high', '±3.00%', '盈利上修', '趋势增强',
      '行业波动', '跌破风险带', '受单股权重约束',
    ]) expect(wrapper.get('[data-testid="hold-advice-h"]').text()).toContain(text)
  })

  it('renders all action evidence, status, and exact money/ratio presentation', () => {
    const item = adviceItem({
      status: 'partial',
      execution: execution(),
    })
    const wrapper = mount(AdviceActionList, { props: { items: [item] } })

    for (const text of [
      '平安银行', '000001', '银行', '部分执行',
      '100', '300', '+200', '9.9000', '10.00%', '25.00%',
      '10.1000', '±3.00%', '87.65%', 'high',
      '盈利上修', '趋势增强', '行业波动', '跌破风险带', '受单股权重约束',
      '10.2000', '1.2500', '2026-07-19T10:30:00+08:00', '部分成交',
    ]) expect(wrapper.text()).toContain(text)
    expect(wrapper.get('[data-testid="advice-action"]').attributes('data-read-only')).toBe('false')
  })

  it('emits execution only for non-hold actions, including corrections', async () => {
    const actionable = adviceItem({ status: 'executed', execution: execution({ disposition: 'executed' }) })
    const hold = adviceItem({ id: 'hold', action: 'hold', symbol: '000002' })
    const wrapper = mount(AdviceActionList, { props: { items: [actionable, hold] } })

    await wrapper.get('[data-testid="execute-item-1"]').trigger('click')
    expect(wrapper.emitted('execute')).toEqual([[actionable]])

    await wrapper.get('[data-testid="toggle-holds"]').trigger('click')
    expect(wrapper.get('[data-testid="hold-advice-hold"]').attributes('data-read-only')).toBe('true')
    expect(wrapper.find('[data-testid="execute-hold"]').exists()).toBe(false)
  })
})
