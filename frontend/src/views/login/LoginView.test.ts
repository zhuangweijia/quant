import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LoginView from './LoginView.vue'

const push = vi.fn()

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ query: {} }),
}))

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

function button(wrapper: ReturnType<typeof mount>, label: string) {
  const match = wrapper.findAll('button').find((candidate) => candidate.text().includes(label))
  if (!match) throw new Error(`Button not found: ${label}`)
  return match
}

function mountView() {
  return mount(LoginView, { attachTo: document.body })
}

describe('LoginView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    push.mockReset()
  })

  it('does not show validation errors merely by switching to registration', async () => {
    const wrapper = mountView()

    await button(wrapper, '立即注册').trigger('click')
    await flushPromises()
    await new Promise((resolve) => setTimeout(resolve, 25))

    expect(wrapper.text()).toContain('创建 Quant Desk 账户')
    expect(wrapper.text()).not.toContain('用户名至少 3 个字符')
    expect(wrapper.text()).not.toContain('密码至少 8 个字符')
    wrapper.unmount()
  })

})
