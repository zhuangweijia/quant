<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute } from "vue-router";
import Sidebar from "./Sidebar.vue";
import Header from "./Header.vue";

const isCollapsed = ref(false);
const route = useRoute();
const mainRef = ref<any>(null);

watch(() => route.path, () => {
  const el = mainRef.value?.$el as HTMLElement | undefined;
  el?.scrollTo({ top: 0 });
});
</script>

<template>
  <el-container class="app-layout">
    <Sidebar :collapsed="isCollapsed" @toggle="isCollapsed = !isCollapsed" />
    <el-container class="right-container">
      <Header @toggle-sidebar="isCollapsed = !isCollapsed" />
      <el-main ref="mainRef" class="app-main">
        <router-view v-slot="{ Component, route }">
          <component :is="Component" :key="route.path" />
        </router-view>
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

.right-container {
  flex-direction: column;
}
</style>
