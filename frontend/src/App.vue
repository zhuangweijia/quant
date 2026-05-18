<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { Toaster } from '@/components/ui/sonner'
import { useThemeStore } from '@/stores/theme'
import { useAuthStore } from '@/stores/auth'
import { wsClient } from '@/utils/websocket'

const themeStore = useThemeStore()
const authStore = useAuthStore()

onMounted(async () => {
  themeStore.initTheme()
  if (authStore.isLoggedIn && !authStore.user) {
    try {
      await authStore.fetchUser()
      wsClient.connect()
    } catch {
      authStore.logout()
    }
  } else if (authStore.isLoggedIn) {
    wsClient.connect()
  }
})

onUnmounted(() => {
  wsClient.disconnect()
})
</script>

<template>
  <Toaster />
  <router-view v-slot="{ Component, route }">
    <component :is="Component" :key="route.path" />
  </router-view>
</template>
