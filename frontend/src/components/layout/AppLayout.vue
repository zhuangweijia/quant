<script setup lang="ts">
import { useTheme } from '@/composables/useTheme'
import { useRiskStore } from '@/stores/risk'
import AppSidebar from '@/components/app-sidebar/index.vue'
import CommandMenu from '@/components/command-menu/index.vue'
import {
  Bell,
  MoonStar,
  Search,
  SunMedium,
} from 'lucide-vue-next'

const { isDark, toggleTheme } = useTheme()
const riskStore = useRiskStore()
const showNotifications = ref(false)
const commandMenuRef = ref<InstanceType<typeof CommandMenu> | null>(null)

function openCommandMenu() {
  commandMenuRef.value?.setOpen(true)
}

async function toggleNotifications() {
  showNotifications.value = !showNotifications.value
  if (showNotifications.value) {
    await riskStore.fetchAlerts({ page: 1, page_size: 10 })
  }
}
</script>

<template>
  <UiSidebarProvider>
    <AppSidebar />
    <UiSidebarInset>
      <header class="flex h-14 items-center gap-3 border-b px-4 shrink-0">
        <UiSidebarTrigger class="-ml-1" />
        <UiSeparator orientation="vertical" class="h-6" />
        <Button variant="outline" size="sm" class="ml-2 gap-2 text-muted-foreground" @click="openCommandMenu">
          <Search class="size-4" />
          <span class="hidden sm:inline">搜索...</span>
          <kbd class="pointer-events-none hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
            ⌘K
          </kbd>
        </Button>
        <div class="flex-1" />
        <div class="flex items-center gap-2">
          <UiButton variant="ghost" size="icon" @click="toggleTheme">
            <SunMedium v-if="!isDark" class="size-4" />
            <MoonStar v-else class="size-4" />
          </UiButton>

          <UiPopover :open="showNotifications" @update:open="showNotifications = $event">
            <UiPopoverTrigger as-child>
              <UiButton variant="ghost" size="icon" class="relative">
                <Bell class="size-4" />
                <span
                  v-if="riskStore.unreadCount > 0"
                  class="absolute -top-1 -right-1 flex size-4 items-center justify-center rounded-full bg-destructive text-destructive-foreground text-[10px] font-bold"
                >
                  {{ riskStore.unreadCount > 9 ? '9+' : riskStore.unreadCount }}
                </span>
              </UiButton>
            </UiPopoverTrigger>
            <UiPopoverContent class="w-80 p-0" align="end">
              <div class="flex items-center justify-between border-b px-4 py-3">
                <span class="font-semibold text-sm">通知</span>
                <button
                  v-if="riskStore.unreadCount > 0"
                  class="text-xs text-primary font-medium hover:underline"
                  @click="riskStore.markAllAlertsRead()"
                >
                  全部已读
                </button>
              </div>
              <div class="max-h-80 overflow-y-auto">
                <div
                  v-for="alert in riskStore.alerts.slice(0, 10)"
                  :key="alert.id"
                  class="border-b px-4 py-3 last:border-0"
                >
                  <div class="flex items-center gap-2 mb-1">
                    <UiBadge
                      :variant="alert.level === 'high' ? 'destructive' : alert.level === 'medium' ? 'outline' : 'secondary'"
                      class="text-[10px] px-1.5 py-0"
                    >
                      {{ alert.level }}
                    </UiBadge>
                    <span class="text-sm font-medium">{{ alert.rule_name || '告警' }}</span>
                  </div>
                  <p class="text-xs text-muted-foreground line-clamp-2">{{ alert.message }}</p>
                </div>
                <div v-if="!riskStore.alerts.length" class="py-8 text-center text-sm text-muted-foreground">
                  暂无通知
                </div>
              </div>
              <div class="border-t px-4 py-2 text-center">
                <router-link
                  to="/risk"
                  class="text-xs text-primary font-medium hover:underline"
                  @click="showNotifications = false"
                >
                  查看全部
                </router-link>
              </div>
            </UiPopoverContent>
          </UiPopover>
        </div>
      </header>

      <main class="flex-1 p-6 overflow-auto">
        <router-view v-slot="{ Component, route }">
          <transition name="page" mode="out-in">
            <component :is="Component" :key="route.path" />
          </transition>
        </router-view>
      </main>
    </UiSidebarInset>
    <CommandMenu ref="commandMenuRef" />
  </UiSidebarProvider>
</template>
