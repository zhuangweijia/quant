import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import type { UserInfo } from '@/types/auth'
import { setupRouterGuards } from './guards'

const Page = { template: '<div />' }
const admin: UserInfo = {
  id: 'admin-1', username: 'admin', role: 'admin', is_active: true,
  created_at: '2026-07-01T00:00:00+08:00',
}
const trader: UserInfo = { ...admin, id: 'trader-1', username: 'trader', role: 'trader' }

function router() {
  const instance = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', name: 'Login', component: Page, meta: { requiresAuth: false, title: '登录' } },
      { path: '/today', name: 'Today', component: Page, meta: { title: '今日' } },
      { path: '/model', name: 'Model', component: Page, meta: { title: '模型', adminOnly: true } },
      { path: '/404', name: 'NotFound', component: Page, meta: { requiresAuth: false } },
    ],
  })
  setupRouterGuards(instance)
  return instance
}

describe('router guards', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('awaits the cold-start user fetch before allowing an admin direct visit', async () => {
    const auth = useAuthStore()
    auth.accessToken = 'persisted-token'
    const fetchUser = vi.spyOn(auth, 'fetchUser').mockImplementation(async () => {
      await Promise.resolve()
      auth.user = admin
    })
    const instance = router()

    await instance.push('/model')
    await instance.isReady()

    expect(fetchUser).toHaveBeenCalledOnce()
    expect(instance.currentRoute.value.name).toBe('Model')
  })

  it('renders NotFound for an ordinary user on admin-only routes', async () => {
    const auth = useAuthStore()
    auth.accessToken = 'token'
    auth.user = trader
    const instance = router()
    await instance.push('/model')
    await instance.isReady()
    expect(instance.currentRoute.value.name).toBe('NotFound')
  })

  it('logs out and safely redirects when cold-start user loading fails', async () => {
    const auth = useAuthStore()
    auth.accessToken = 'expired-token'
    const logout = vi.spyOn(auth, 'logout')
    vi.spyOn(auth, 'fetchUser').mockRejectedValue(new Error('unauthorized'))
    const instance = router()
    await instance.push('/model')
    await instance.isReady()
    expect(logout).toHaveBeenCalledOnce()
    expect(instance.currentRoute.value.name).toBe('Login')
    expect(instance.currentRoute.value.query.redirect).toBe('/model')
  })

  it('redirects logged-in login visits to Today and sets the exact title', async () => {
    const auth = useAuthStore()
    auth.accessToken = 'token'
    auth.user = trader
    const instance = router()
    await instance.push('/login')
    await instance.isReady()
    expect(instance.currentRoute.value.name).toBe('Today')
    expect(document.title).toBe('今日 - Quant Desk')
  })

  it('uses the exact fallback title', async () => {
    const instance = router()
    await instance.push('/404')
    await instance.isReady()
    expect(document.title).toBe('Quant Desk - Quant Desk')
  })
})
