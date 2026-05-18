import { computed } from 'vue'
import { useThemeStore } from '@/stores/theme'

export function useTheme() {
  const store = useThemeStore()

  const isDark = computed(() => {
    if (store.colorMode === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return store.colorMode === 'dark'
  })

  function toggleTheme() {
    store.setColorMode(isDark.value ? 'light' : 'dark')
  }

  return {
    isDark,
    theme: computed(() => store.theme),
    radius: computed(() => store.radius),
    colorMode: computed(() => store.colorMode),
    setTheme: store.setTheme,
    setRadius: store.setRadius,
    setColorMode: store.setColorMode,
    toggleTheme,
  }
}
