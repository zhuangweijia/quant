<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { useRiskStore } from "@/stores/risk";
import { SwitchButton, Setting, Bell, Fold, Expand } from "@element-plus/icons-vue";

defineEmits<{ (e: "toggle-sidebar"): void }>();

const router = useRouter();
const authStore = useAuthStore();
const riskStore = useRiskStore();
const showNotifications = ref(false);

  const username = computed(() => {
    const u = authStore.username;
    return typeof u === 'string' ? u : '';
  });
  const role = computed(() => {
    const r = authStore.role;
    return typeof r === 'string' ? r : '';
  });

function handleLogout() {
  authStore.logout();
  router.push("/login");
}

function handleCommand(command: string) {
  if (command === "logout") handleLogout();
  else if (command === "settings") router.push("/settings");
}

async function handleNotificationClick() {
  showNotifications.value = !showNotifications.value;
  if (showNotifications.value) {
    await riskStore.fetchAlerts({ page: 1, page_size: 10 });
  }
}

async function markAllRead() {
  await riskStore.markAllAlertsRead();
}

onMounted(() => {
  riskStore.fetchUnreadCount();
});
</script>

<template>
  <el-header class="app-header">
    <div class="header-left">
      <el-button text class="collapse-btn" @click="$emit('toggle-sidebar')">
        <el-icon :size="18"><Fold /></el-icon>
      </el-button>
    </div>
    <div class="header-right">
      <el-popover
        :visible="showNotifications"
        placement="bottom-end"
        :width="360"
        trigger="click"
        @update:visible="showNotifications = $event"
      >
        <template #reference>
          <el-badge :value="riskStore.unreadCount" :hidden="riskStore.unreadCount === 0" :max="99">
            <el-button text class="icon-btn" @click="handleNotificationClick">
              <el-icon :size="18"><Bell /></el-icon>
            </el-button>
          </el-badge>
        </template>
        <div class="notification-panel">
          <div class="notification-header">
            <span>通知</span>
            <el-button v-if="riskStore.unreadCount > 0" link type="primary" size="small" @click="markAllRead">
              全部已读
            </el-button>
          </div>
          <div class="notification-list">
            <div v-for="alert in riskStore.alerts.slice(0, 10)" :key="alert.id" class="notification-item">
              <div class="notification-title">
                <el-tag size="small" :type="({ low: 'info', medium: 'warning', high: 'danger' }[alert.level as string] ?? 'info') as any">
                  {{ alert.level }}
                </el-tag>
                <span>{{ alert.rule_name || '告警' }}</span>
              </div>
              <div class="notification-msg">{{ alert.message }}</div>
            </div>
            <el-empty v-if="!riskStore.alerts.length" description="暂无通知" :image-size="60" />
          </div>
          <div class="notification-footer">
            <el-button link type="primary" @click="router.push('/risk'); showNotifications = false">查看全部</el-button>
          </div>
        </div>
      </el-popover>

      <el-divider direction="vertical" />

      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-dropdown">
          <el-avatar :size="30" class="user-avatar">
            {{ username?.charAt(0)?.toUpperCase() || "U" }}
          </el-avatar>
          <span class="username">{{ username || "用户" }}</span>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              <el-tag size="small" type="info">{{ role === "admin" ? "管理员" : "交易员" }}</el-tag>
            </el-dropdown-item>
            <el-dropdown-item command="settings" divided>
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

<style scoped lang="scss">
.app-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid var(--qp-border-color);
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
}

.collapse-btn {
  color: var(--qp-text-regular);
  &:hover {
    color: var(--qp-primary);
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.icon-btn {
  color: var(--qp-text-regular);
  &:hover {
    color: var(--qp-primary);
  }
}

.el-divider--vertical {
  height: 20px;
  border-color: var(--qp-border-color);
}

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;

  &:hover {
    background: #f5f7fa;
  }
}

.user-avatar {
  background: var(--el-color-primary);
  color: #fff;
  font-size: 13px;
  flex-shrink: 0;
}

.username {
  font-size: 14px;
  color: var(--qp-text-primary);
  white-space: nowrap;
}

.notification-panel {
  .notification-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--qp-border-color);
    margin-bottom: 8px;
    font-weight: 600;
  }

  .notification-list {
    max-height: 320px;
    overflow-y: auto;
  }

  .notification-item {
    padding: 10px 0;
    border-bottom: 1px solid #f0f0f0;

    &:last-child {
      border-bottom: none;
    }
  }

  .notification-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
    font-size: 13px;
  }

  .notification-msg {
    font-size: 12px;
    color: var(--qp-text-secondary);
    padding-left: 52px;
  }

  .notification-footer {
    text-align: center;
    padding-top: 8px;
    border-top: 1px solid var(--qp-border-color);
    margin-top: 8px;
  }
}
</style>
