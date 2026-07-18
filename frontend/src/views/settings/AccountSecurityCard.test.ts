import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { settingsApi } from '@/api/settings'
import { useAuthStore } from '@/stores/auth'
import AccountSecurityCard from './AccountSecurityCard.vue'

const { push } = vi.hoisted(() => ({ push: vi.fn() }))

vi.mock('vue-router', () => ({ useRouter: () => ({ push }) }))
vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

describe('AccountSecurityCard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    push.mockReset()
    setActivePinia(createPinia())
    vi.spyOn(settingsApi, 'getProfile').mockResolvedValue({
      data: {
        username: 'alice',
        role: 'admin',
        is_active: true,
        created_at: '2026-07-18T00:00:00Z',
      },
    } as never)
  })

  it('renders profile data', async () => {
    const wrapper = mount(AccountSecurityCard)
    await flushPromises()
    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('管理员')
    expect(wrapper.text()).toContain('正常')
  })

  it('rejects mismatched new passwords before calling the API', async () => {
    const change = vi.spyOn(settingsApi, 'changePassword')
    const wrapper = mount(AccountSecurityCard)
    await flushPromises()
    await wrapper.get('#old-password').setValue('oldpass1')
    await wrapper.get('#new-password').setValue('newpass2')
    await wrapper.get('#confirm-password').setValue('different3')
    await wrapper.get('form').trigger('submit')
    expect(change).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('两次密码不一致')
  })

  it('logs out and redirects after a successful password change', async () => {
    vi.spyOn(settingsApi, 'changePassword').mockResolvedValue({ data: null } as never)
    const auth = useAuthStore()
    auth.accessToken = 'access-token'
    auth.refreshToken = 'refresh-token'
    const logout = vi.spyOn(auth, 'logout')
    const wrapper = mount(AccountSecurityCard)
    await flushPromises()
    await wrapper.get('#old-password').setValue('oldpass1')
    await wrapper.get('#new-password').setValue('newpass2')
    await wrapper.get('#confirm-password').setValue('newpass2')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(logout).toHaveBeenCalledOnce()
    expect(auth.accessToken).toBe('')
    expect(auth.refreshToken).toBe('')
    expect(push).toHaveBeenCalledWith('/login')
  })
})
