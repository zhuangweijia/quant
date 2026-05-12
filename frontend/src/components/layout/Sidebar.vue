<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import {
  Odometer,
  TrendCharts,
  Setting,
  DataAnalysis,
  Money,
  Lock,
  Tools,
} from "@element-plus/icons-vue";

defineProps<{ collapsed: boolean }>();
defineEmits<{ (e: "toggle"): void }>();

const route = useRoute();

const menuItems = [
  { title: "看板", icon: Odometer, path: "/dashboard" },
  { title: "行情", icon: TrendCharts, path: "/market" },
  { title: "策略", icon: Setting, path: "/strategy" },
  { title: "回测", icon: DataAnalysis, path: "/backtest" },
  { title: "交易", icon: Money, path: "/trade" },
  { title: "风控", icon: Lock, path: "/risk" },
  { title: "设置", icon: Tools, path: "/settings" },
];

const activeMenu = computed(() => {
  const path = route.path;
  const match = menuItems.find((item) => path.startsWith(item.path));
  return match ? match.path : "/dashboard";
});
</script>

<template>
  <el-aside :width="collapsed ? '64px' : '220px'" class="sidebar">
    <div class="sidebar-logo">
      <h1 v-if="!collapsed">QuantPlatform</h1>
      <h1 v-else>Q</h1>
    </div>
    <el-menu
      :default-active="activeMenu"
      :collapse="collapsed"
      router
      class="sidebar-menu"
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409EFF"
    >
      <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <template #title>{{ item.title }}</template>
      </el-menu-item>
    </el-menu>
  </el-aside>
</template>

<style scoped lang="scss">
.sidebar {
  background: #304156;
  transition: width 0.3s;
  overflow: hidden;
}

.sidebar-logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);

  h1 {
    margin: 0;
    font-size: 20px;
    font-weight: 600;
    white-space: nowrap;
  }
}

.sidebar-menu {
  border-right: none;
}
</style>
