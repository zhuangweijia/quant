<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { SwitchButton, Setting } from "@element-plus/icons-vue";

const router = useRouter();
const authStore = useAuthStore();

function handleLogout() {
  authStore.logout();
  router.push("/login");
}

function handleCommand(command: string) {
  if (command === "logout") handleLogout();
  else if (command === "settings") router.push("/settings");
}
</script>

<template>
  <el-header class="app-header">
    <div class="header-left">
      <el-button text @click="$emit('toggle-sidebar')">
        <el-icon :size="20"><Setting /></el-icon>
      </el-button>
    </div>
    <div class="header-right">
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-dropdown">
          <el-avatar :size="32" class="user-avatar">
            {{ authStore.username?.charAt(0)?.toUpperCase() || "U" }}
          </el-avatar>
          <span class="username">{{ authStore.username }}</span>
          <el-tag size="small" type="info" class="role-tag">
            {{ authStore.role === "admin" ? "管理员" : "交易员" }}
          </el-tag>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="settings">
              <el-icon><Setting /></el-icon>系统设置
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </el-header>
</template>

<script lang="ts">
export default { name: "AppHeader" };
</script>

<style scoped lang="scss">
.app-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid var(--qp-border-color);
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.user-avatar {
  background: var(--el-color-primary);
  color: #fff;
}

.username {
  font-size: 14px;
  color: var(--qp-text-primary);
}

.role-tag {
  font-size: 12px;
}
</style>
