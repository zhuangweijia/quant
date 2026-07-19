import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AppLayout from './AppLayout.vue'

describe('AppLayout', () => {
  it('mounts the command menu exactly once in the shared shell', () => {
    const wrapper = mount(AppLayout, {
      global: {
        stubs: {
          AppSidebar: true,
          CommandMenu: { template: '<div data-testid="command-menu" />' },
          UiSidebarProvider: { template: '<div><slot /></div>' },
          UiSidebarInset: { template: '<div><slot /></div>' },
          UiSidebarTrigger: true,
          RouterView: true,
        },
      },
    })

    expect(wrapper.findAll('[data-testid="command-menu"]')).toHaveLength(1)
  })
})
