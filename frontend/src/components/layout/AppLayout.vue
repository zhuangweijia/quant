<script setup lang="ts">
import { ref, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { STATUS_LABELS, MARKET_LABELS } from "@/utils/constants";
import Sidebar from "./Sidebar.vue";
import Header from "./Header.vue";

const isCollapsed = ref(false);
</script>

<template>
  <el-container class="app-layout">
    <Sidebar :collapsed="isCollapsed" @toggle="isCollapsed = !isCollapsed" />
    <el-container>
      <Header @toggle-sidebar="isCollapsed = !isCollapsed" />
      <el-main class="app-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped lang="scss">
.app-layout {
  height: 100vh;
  overflow: hidden;
}

.app-main {
  background: var(--qp-bg-page);
  padding: 20px;
  overflow-y: auto;
}
</style>
