<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { useAuthStore } from "@/stores/auth";
import { wsClient } from "@/utils/websocket";

const authStore = useAuthStore();

onMounted(async () => {
  if (authStore.isLoggedIn && !authStore.user) {
    try {
      await authStore.fetchUser();
      wsClient.connect();
    } catch {
      authStore.logout();
    }
  } else if (authStore.isLoggedIn) {
    wsClient.connect();
  }
});

onUnmounted(() => {
  wsClient.disconnect();
});
</script>

<template>
  <router-view />
</template>
