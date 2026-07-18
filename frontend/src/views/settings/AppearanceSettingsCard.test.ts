import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useThemeStore } from '@/stores/theme'
import AppearanceSettingsCard from './AppearanceSettingsCard.vue'

describe('AppearanceSettingsCard', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('applies color mode immediately', async () => {
    const wrapper = mount(AppearanceSettingsCard)
    await wrapper.get('[data-testid="appearance-mode-dark"]').trigger('click')
    expect(useThemeStore().colorMode).toBe('dark')
    expect(localStorage.getItem('qp-color-mode')).toBe('dark')
  })

  it('applies theme color and radius immediately', async () => {
    const wrapper = mount(AppearanceSettingsCard)
    await wrapper.get('[data-testid="appearance-color-blue"]').trigger('click')
    await wrapper.get('[data-testid="appearance-radius-comfortable"]').trigger('click')
    const store = useThemeStore()
    expect(store.theme).toBe('blue')
    expect(store.radius).toBe(0.75)
    expect(localStorage.getItem('qp-theme-color')).toBe('blue')
    expect(localStorage.getItem('qp-theme-radius')).toBe('0.75')
  })
})
