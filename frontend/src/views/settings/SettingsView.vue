<script setup lang="ts">
import { computed } from 'vue'

import { BasicPage } from '@/components/global-layout'
import { useAuthStore } from '@/stores/auth'
import AccountSecurityCard from './AccountSecurityCard.vue'
import AppearanceSettingsCard from './AppearanceSettingsCard.vue'
import NotificationSettingsCard from './NotificationSettingsCard.vue'
import SystemParamsCard from './SystemParamsCard.vue'

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.role === 'admin')
</script>

<template>
  <BasicPage title="系统设置" description="管理外观、通知、分析参数与账户安全。">
    <div class="grid gap-6 xl:grid-cols-2">
      <AppearanceSettingsCard />
      <NotificationSettingsCard />
      <div v-if="isAdmin" class="xl:col-span-2">
        <SystemParamsCard />
      </div>
      <div class="xl:col-span-2">
        <AccountSecurityCard />
      </div>
    </div>
  </BasicPage>
</template>
