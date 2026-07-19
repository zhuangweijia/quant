import type { Router } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

export function setupRouterGuards(router: Router) {
  router.beforeEach(async (to, _from, next) => {
    const authStore = useAuthStore()

    if (to.meta.requiresAuth !== false && !authStore.isLoggedIn) {
      next({ name: 'Login', query: { redirect: to.fullPath } })
      return
    }

    if (authStore.isLoggedIn && authStore.user === null) {
      try {
        await authStore.fetchUser()
      } catch {
        authStore.logout()
        if (to.meta.requiresAuth !== false) {
          next({ name: 'Login', query: { redirect: to.fullPath } })
          return
        }
      }
    }

    if (to.meta.adminOnly && authStore.role !== 'admin') {
      next({ name: 'NotFound' })
      return
    }

    if (to.meta.permission === 'trade' && authStore.role === 'viewer') {
      next({ name: 'NotFound' })
      return
    }

    if (to.name === 'Login' && authStore.isLoggedIn) {
      next({ name: 'Today' })
      return
    }

    document.title = `${String(to.meta.title || 'Quant Desk')} - Quant Desk`
    next()
  })
}
