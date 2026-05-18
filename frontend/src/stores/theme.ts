import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemeColor = 'zinc' | 'red' | 'rose' | 'orange' | 'green' | 'blue' | 'yellow' | 'violet'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<ThemeColor>((localStorage.getItem('qp-theme-color') as ThemeColor) || 'zinc')
  const radius = ref(Number(localStorage.getItem('qp-theme-radius') || 0.625))
  const colorMode = ref<'light' | 'dark' | 'system'>(
    (localStorage.getItem('qp-color-mode') as 'light' | 'dark' | 'system') || 'system'
  )

  function setTheme(color: ThemeColor) {
    theme.value = color
    localStorage.setItem('qp-theme-color', color)
    applyTheme()
  }

  function setRadius(r: number) {
    radius.value = r
    localStorage.setItem('qp-theme-radius', String(r))
    applyTheme()
  }

  function setColorMode(mode: 'light' | 'dark' | 'system') {
    colorMode.value = mode
    localStorage.setItem('qp-color-mode', mode)
    applyColorMode()
  }

  function applyTheme() {
    const el = document.documentElement
    el.className = el.className.replace(/theme-\w+/g, '').trim()
    if (theme.value !== 'zinc') {
      el.classList.add(`theme-${theme.value}`)
    }
    el.style.setProperty('--radius', `${radius.value}rem`)
    applyColorMode()
  }

  function applyColorMode() {
    const el = document.documentElement
    const isDark =
      colorMode.value === 'dark' ||
      (colorMode.value === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
    el.classList.toggle('dark', isDark)
  }

  function initTheme() {
    applyTheme()
    applyColorMode()
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      if (colorMode.value === 'system') applyColorMode()
    })
  }

  return { theme, radius, colorMode, setTheme, setRadius, setColorMode, initTheme }
})
