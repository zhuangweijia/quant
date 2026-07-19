import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import type { PositionInput } from '@/types/portfolio'
import HoldingsEditor from './HoldingsEditor.vue'

function mountEditor(
  positions: PositionInput[] = [],
  cash = '100000.0001',
  totalCapital = '100000.0001',
) {
  return mount(HoldingsEditor, {
    props: { cash, positions, totalCapital },
  })
}

describe('HoldingsEditor', () => {
  it('emits exact money strings and immutable position arrays', async () => {
    const original: PositionInput[] = [
      { symbol: '000001', quantity: 100, average_cost: '10.0001' },
    ]
    const wrapper = mountEditor(original)

    await wrapper.get('#portfolio-cash').setValue('99999.9999')
    await wrapper.get('#holding-cost-0').setValue('10.0002')

    expect(wrapper.emitted('update:cash')?.at(-1)).toEqual(['99999.9999'])
    const emitted = wrapper.emitted('update:positions')?.at(-1)?.[0] as PositionInput[]
    expect(emitted).not.toBe(original)
    expect(emitted[0]).not.toBe(original[0])
    expect(emitted[0].average_cost).toBe('10.0002')
    expect(original[0].average_cost).toBe('10.0001')
  })

  it('renders stable row fields and a decimal-safe calculated cost', () => {
    const wrapper = mountEditor([
      { symbol: '000001', quantity: 3, average_cost: '0.1000000000000001' },
    ])

    expect(wrapper.find('#holding-symbol-0').exists()).toBe(true)
    expect(wrapper.find('#holding-quantity-0').exists()).toBe(true)
    expect(wrapper.find('#holding-cost-0').exists()).toBe(true)
    expect(wrapper.get('[data-testid="holding-value-0"]').text()).toContain(
      '0.3000000000000003',
    )
  })

  it('requires exactly six ASCII digits without silently rewriting invalid symbols', async () => {
    const wrapper = mountEditor([
      { symbol: 'abc000001', quantity: 100, average_cost: '10' },
    ])

    expect((wrapper.get('#holding-symbol-0').element as HTMLInputElement).value).toBe(
      'abc000001',
    )
    expect(wrapper.text()).toContain('股票代码必须是六位数字')

    await wrapper.get('#holding-symbol-0').setValue('１２３４５６')
    expect((wrapper.get('#holding-symbol-0').element as HTMLInputElement).value).toBe(
      '１２３４５６',
    )
    expect(wrapper.text()).toContain('股票代码必须是六位数字')
  })

  it('shows duplicate-symbol errors inline', () => {
    const wrapper = mountEditor([
      { symbol: '000001', quantity: 100, average_cost: '10' },
      { symbol: '000001', quantity: 200, average_cost: '11' },
    ])

    expect(wrapper.findAll('[data-testid="holding-symbol-error"]')).toHaveLength(2)
    expect(wrapper.text()).toContain('持仓股票代码不能重复')
  })

  it('adds and removes rows without mutating the provided array', async () => {
    const original: PositionInput[] = [
      { symbol: '000001', quantity: 100, average_cost: '10' },
    ]
    const wrapper = mountEditor(original)

    await wrapper.get('[data-testid="holding-add"]').trigger('click')
    const added = wrapper.emitted('update:positions')?.at(-1)?.[0] as PositionInput[]
    expect(added).toEqual([
      original[0],
      { symbol: '', quantity: 0, average_cost: '' },
    ])
    expect(original).toHaveLength(1)

    await wrapper.get('[data-testid="holding-remove-0"]').trigger('click')
    const removed = wrapper.emitted('update:positions')?.at(-1)?.[0] as PositionInput[]
    expect(removed).toEqual([])
    expect(original).toHaveLength(1)
  })
})
