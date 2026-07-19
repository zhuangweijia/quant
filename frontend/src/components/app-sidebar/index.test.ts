import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { defineComponent } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import { SidebarProvider } from '@/components/ui/sidebar'
import AppSidebar from './index.vue'

const SidebarHarness = defineComponent({
  components: { AppSidebar, SidebarProvider },
  template: '<SidebarProvider><AppSidebar /></SidebarProvider>',
})

async function mountSidebar(role: 'admin' | 'trader') {
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
    routes: [
      { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
    ],
  })
  await router.push('/today')
  await router.isReady()

  const wrapper = mount(SidebarHarness, {
    attachTo: document.body,
    global: { plugins: [pinia, router] },
  })
  await flushPromises()
  return wrapper
}

describe('AppSidebar', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('renders Quant Desk and the primary navigation for a trader', async () => {
    const wrapper = await mountSidebar('trader')

    expect(wrapper.text()).toContain('Quant Desk')
    expect(wrapper.text()).not.toContain('Stock Analysis')
    expect(wrapper.text()).not.toContain('Workspace')
    expect(wrapper.text()).toContain('今日')
    expect(wrapper.text()).toContain('持仓')
    expect(wrapper.text()).toContain('选股')
    expect(wrapper.text()).toContain('市场')

    const hrefs = wrapper.findAll('a').map(link => link.attributes('href'))
    expect(hrefs).toEqual(['/today', '/portfolio', '/selection', '/market'])
    wrapper.unmount()
  })

  it('hides the administrator group from a trader', async () => {
    const wrapper = await mountSidebar('trader')

    expect(wrapper.text()).not.toContain('分析任务')
    expect(wrapper.text()).not.toContain('模型与回测')
    wrapper.unmount()
  })

  it('renders administrator operations in a separate group', async () => {
    const wrapper = await mountSidebar('admin')

    expect(wrapper.text()).toContain('分析任务')
    expect(wrapper.text()).toContain('模型与回测')
    expect(wrapper.findAll('[data-slot="sidebar-group"]')).toHaveLength(2)
    wrapper.unmount()
  })
})
