import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/client'
import { useAdviceStore } from '@/stores/advice'
import type { AdviceItemResponse } from '@/types/advice'
import ExecutionDialog from './ExecutionDialog.vue'
import { adviceItem, execution } from './test-fixtures'

const mounted: VueWrapper[] = []

async function mountDialog(item: AdviceItemResponse = adviceItem()): Promise<VueWrapper> {
  const wrapper = mount(ExecutionDialog, {
    attachTo: document.body,
    props: { open: true, item, existingExecution: item.execution },
  })
  mounted.push(wrapper)
  await flushPromises()
  return wrapper
}

async function setInput(selector: string, value: string) {
  const element = document.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(selector)
  if (!element) throw new Error(`Missing ${selector}`)
  element.value = value
  element.dispatchEvent(new Event('input', { bubbles: true }))
  element.dispatchEvent(new Event('change', { bubbles: true }))
  await flushPromises()
}

async function click(selector: string) {
  const element = document.querySelector<HTMLElement>(selector)
  if (!element) throw new Error(`Missing ${selector}`)
  element.click()
  await flushPromises()
}

describe('ExecutionDialog', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    for (const wrapper of mounted.splice(0)) wrapper.unmount()
    document.body.innerHTML = ''
    vi.restoreAllMocks()
  })

  it('prefills correction fields and revision but never prefills the actual price', async () => {
    await mountDialog(adviceItem({
      status: 'partial',
      execution: execution({ quantity: 60, price: '10.8888', fee: '2.5000', revision: 7 }),
    }))

    expect(document.querySelector<HTMLSelectElement>('#execution-disposition')?.value).toBe('partial')
    expect(document.querySelector<HTMLInputElement>('#execution-quantity')?.value).toBe('60')
    expect(document.querySelector<HTMLInputElement>('#execution-price')?.value).toBe('')
    expect(document.querySelector<HTMLInputElement>('#execution-fee')?.value).toBe('2.5000')
    expect(document.body.textContent).toContain('修订版本 7')
  })

  it('requires a skipped reason and hides and clears all trade fields', async () => {
    const store = useAdviceStore()
    const update = vi.spyOn(store, 'updateExecution').mockResolvedValue({} as never)
    const wrapper = await mountDialog()

    await setInput('#execution-price', '10.1000')
    await setInput('#execution-fee', '1.2000')
    await setInput('#execution-time', '2026-07-19T10:30')
    await setInput('#execution-disposition', 'skipped')

    expect(document.querySelector('#execution-quantity')).toBeNull()
    expect(document.querySelector('#execution-price')).toBeNull()
    expect(document.querySelector('#execution-fee')).toBeNull()
    expect(document.querySelector('#execution-time')).toBeNull()
    await click('[data-testid="execution-submit"]')
    expect(document.body.textContent).toContain('未执行原因必填')
    expect(update).not.toHaveBeenCalled()

    await setInput('#execution-reason', '临时资金安排')
    await click('[data-testid="execution-submit"]')
    expect(update).toHaveBeenCalledWith('item-1', {
      disposition: 'skipped',
      quantity: 0,
      price: null,
      fee: '0',
      executed_at: null,
      reason: '临时资金安排',
      expected_revision: 0,
      acknowledge_outside_advice: false,
    })
    expect(wrapper.emitted('submit')).toEqual([[{
      disposition: 'skipped',
      quantity: 0,
      price: null,
      fee: '0',
      executed_at: null,
      reason: '临时资金安排',
      expected_revision: 0,
      acknowledge_outside_advice: false,
    }]])
  })

  it('requires canonical price, positive integer quantity, aware time and caps sells', async () => {
    const store = useAdviceStore()
    const update = vi.spyOn(store, 'updateExecution').mockResolvedValue({} as never)
    await mountDialog(adviceItem({ action: 'reduce', current_quantity: 80, delta_quantity: -120 }))

    expect(document.querySelector<HTMLInputElement>('#execution-quantity')?.max).toBe('80')
    await setInput('#execution-disposition', 'partial')
    await setInput('#execution-quantity', '81')
    await setInput('#execution-price', ' 10.1000 ')
    await click('[data-testid="execution-submit"]')
    expect(document.body.textContent).toContain('成交数量不能超过 80')
    expect(document.body.textContent).toContain('请输入规范的正数成交价')
    expect(update).not.toHaveBeenCalled()

    await setInput('#execution-quantity', '79')
    await setInput('#execution-price', '10.100000')
    await setInput('#execution-fee', '0.2500')
    await setInput('#execution-time', '2026-07-19T10:30')
    await click('[data-testid="execution-submit"]')

    expect(update).toHaveBeenCalledWith('item-1', {
      disposition: 'partial',
      quantity: 79,
      price: '10.100000',
      fee: '0.2500',
      executed_at: new Date('2026-07-19T10:30').toISOString(),
      reason: '',
      expected_revision: 0,
      acknowledge_outside_advice: false,
    })
  })

  it('offers acknowledgement only for the exact outside-advice 409 and avoids double submission', async () => {
    const store = useAdviceStore()
    let reject!: (error: unknown) => void
    const update = vi.spyOn(store, 'updateExecution').mockImplementation(
      () => new Promise((_resolve, fail) => { reject = fail }),
    )
    await mountDialog()
    await setInput('#execution-price', '11.0000')
    await setInput('#execution-time', '2026-07-19T10:30')

    const pendingClick = click('[data-testid="execution-submit"]')
    await click('[data-testid="execution-submit"]')
    expect(update).toHaveBeenCalledOnce()
    reject(new ApiError('需要确认', {
      code: 'outside_advice_requires_acknowledgement',
      message: '成交价超出建议价格带，确认后可仍记录为实际成交',
    }, 409))
    await pendingClick
    await flushPromises()

    expect(document.body.textContent).toContain('成交价超出建议价格带')
    expect(document.querySelector('[data-testid="execution-acknowledge"]')).not.toBeNull()
    await setInput('#execution-price', '12.3456')
    await setInput('#execution-quantity', '150')
    update.mockResolvedValueOnce({} as never)
    await click('[data-testid="execution-acknowledge"]')
    expect(update).toHaveBeenNthCalledWith(2, 'item-1', expect.objectContaining({
      price: '11.0000',
      quantity: 200,
      acknowledge_outside_advice: true,
    }))
  })

  it.each([
    new ApiError('执行记录已更新', { code: 'stale_execution_revision' }, 409),
    new ApiError('请先核对持仓', { code: 'later_symbol_event_requires_reconcile' }, 409),
    new ApiError('普通校验错误', { code: 'outside_advice_requires_acknowledgement' }, 422),
  ])('never offers acknowledgement for stale, later-event, or non-409 errors', async (error) => {
    const store = useAdviceStore()
    vi.spyOn(store, 'updateExecution').mockRejectedValue(error)
    await mountDialog()
    await setInput('#execution-price', '10.1000')
    await setInput('#execution-time', '2026-07-19T10:30')
    await click('[data-testid="execution-submit"]')

    expect(document.querySelector('[data-testid="execution-acknowledge"]')).toBeNull()
    if (error.status === 409) {
      expect(document.body.textContent).toContain('请刷新今日建议并核对持仓')
    }
  })

  it('removes a prior acknowledgement action when the acknowledged retry returns stale', async () => {
    const store = useAdviceStore()
    vi.spyOn(store, 'updateExecution')
      .mockRejectedValueOnce(new ApiError('需要确认', {
        code: 'outside_advice_requires_acknowledgement',
        message: '建议已过期，确认后可仍记录为实际成交',
      }, 409))
      .mockRejectedValueOnce(new ApiError('执行记录已更新', {
        code: 'stale_execution_revision',
        message: '执行记录已更新，请刷新后重试',
      }, 409))
    await mountDialog()
    await setInput('#execution-price', '10.1000')
    await setInput('#execution-time', '2026-07-19T10:30')
    await click('[data-testid="execution-submit"]')
    expect(document.querySelector('[data-testid="execution-acknowledge"]')).not.toBeNull()

    await click('[data-testid="execution-acknowledge"]')
    expect(document.querySelector('[data-testid="execution-acknowledge"]')).toBeNull()
    expect(document.body.textContent).toContain('请刷新今日建议并核对持仓')
  })
})
