import { computed } from 'vue'
import { useThemeStore } from '@/stores/theme'

export function useTheme() {
  const store = useThemeStore()

  return {
    isDark: computed(() => store.isDark),
    theme: computed(() => store.theme),
    radius: computed(() => store.radius),
    colorMode: computed(() => store.colorMode),
    setTheme: store.setTheme,
    setRadius: store.setRadius,
    setColorMode: store.setColorMode,
    toggleTheme: () => store.setColorMode(store.isDark ? 'light' : 'dark'),
  }
}
