import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import CommandMenu from './index.vue'

async function openCommandMenu(role: 'admin' | 'trader') {
  const pinia = createPinia()
  setActivePinia(pinia)

  const auth = useAuthStore()
  auth.user = {
    id: 'u1',
    username: 'alice',
    role,
    is_active: true,
    created_at: '',
  }

  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
  })
  await router.push('/today')
  await router.isReady()

  const wrapper = mount(CommandMenu, {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  })
  wrapper.vm.setOpen(true)
  await nextTick()
  await flushPromises()
  const text = document.body.textContent ?? ''
  wrapper.unmount()
  return text
}

describe('CommandMenu', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('shows the shared primary navigation and no settings to a trader', async () => {
    const text = await openCommandMenu('trader')

    for (const title of ['今日', '持仓', '选股', '市场']) expect(text).toContain(title)
    expect(text).not.toContain('分析任务')
    expect(text).not.toContain('模型与回测')
    expect(text).not.toContain('设置')
  })

  it('adds the administrator navigation for an admin', async () => {
    const text = await openCommandMenu('admin')

    expect(text).toContain('分析任务')
    expect(text).toContain('模型与回测')
  })
})
