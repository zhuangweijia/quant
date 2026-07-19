<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getAdminNav, getPrimaryNav } from '@/navigation/items'
import { useAuthStore } from '@/stores/auth'
import {
  LogOut,
  Settings2,
  TrendingUp,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const primaryNav = computed(() => getPrimaryNav(authStore.role))
const adminNav = computed(() => getAdminNav(authStore.role))

const isActive = (path: string) => route.path.startsWith(path)

const username = computed(() => authStore.username || 'User')
const userInitial = computed(() => username.value.charAt(0).toUpperCase())

function handleLogout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <UiSidebar collapsible="icon" class="border-r">
    <UiSidebarHeader class="border-b px-3 py-4 group-data-[collapsible=icon]:px-2">
      <UiSidebarMenu>
        <UiSidebarMenuItem>
          <UiSidebarMenuButton size="lg" class="gap-3 group-data-[collapsible=icon]:mx-auto group-data-[collapsible=icon]:size-10 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-0">
            <div class="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <TrendingUp class="size-4" />
            </div>
            <div class="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
              <span class="truncate font-bold">Quant Desk</span>
              <span class="truncate text-xs text-muted-foreground">每日组合决策</span>
            </div>
          </UiSidebarMenuButton>
        </UiSidebarMenuItem>
      </UiSidebarMenu>
    </UiSidebarHeader>

    <UiSidebarContent class="px-2 py-3">
      <UiSidebarGroup class="gap-2">
        <UiSidebarGroupLabel>每日决策</UiSidebarGroupLabel>
        <UiSidebarMenu>
          <UiSidebarMenuItem v-for="item in primaryNav" :key="item.path">
            <UiSidebarMenuButton
              as-child
              :is-active="isActive(item.path)"
              :tooltip="item.title"
            >
              <router-link :to="item.path" class="flex min-w-0 items-center gap-3">
                <component :is="item.icon" class="size-4" />
                <span>{{ item.title }}</span>
              </router-link>
            </UiSidebarMenuButton>
          </UiSidebarMenuItem>
        </UiSidebarMenu>
      </UiSidebarGroup>
      <UiSidebarGroup v-if="adminNav.length" class="gap-2">
        <UiSidebarGroupLabel>管理</UiSidebarGroupLabel>
        <UiSidebarMenu>
          <UiSidebarMenuItem v-for="item in adminNav" :key="item.path">
            <UiSidebarMenuButton
              as-child
              :is-active="isActive(item.path)"
              :tooltip="item.title"
            >
              <router-link :to="item.path" class="flex min-w-0 items-center gap-3">
                <component :is="item.icon" class="size-4" />
                <span>{{ item.title }}</span>
              </router-link>
            </UiSidebarMenuButton>
          </UiSidebarMenuItem>
        </UiSidebarMenu>
      </UiSidebarGroup>
    </UiSidebarContent>

    <UiSidebarFooter class="border-t px-2 py-3">
      <UiSidebarMenu>
        <UiSidebarMenuItem>
          <UiDropdownMenu>
            <UiDropdownMenuTrigger as-child>
              <UiSidebarMenuButton size="lg" class="gap-3 group-data-[collapsible=icon]:mx-auto group-data-[collapsible=icon]:size-10 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-0">
                <UiAvatar class="size-8 rounded-lg">
                  <UiAvatarFallback class="rounded-lg">{{ userInitial }}</UiAvatarFallback>
                </UiAvatar>
                <div class="grid flex-1 text-left text-sm leading-tight group-data-[collapsible=icon]:hidden">
                  <span class="truncate font-semibold">{{ username }}</span>
                  <span class="truncate text-xs text-muted-foreground">
                    {{ authStore.role === 'admin' ? '管理员' : '用户' }}
                  </span>
                </div>
              </UiSidebarMenuButton>
            </UiDropdownMenuTrigger>
            <UiDropdownMenuContent
              class="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
              side="bottom"
              align="start"
              :side-offset="4"
            >
              <UiDropdownMenuItem @click="router.push('/settings')">
                <Settings2 class="mr-2 size-4" />
                系统设置
              </UiDropdownMenuItem>
              <UiDropdownMenuSeparator />
              <UiDropdownMenuItem @click="handleLogout">
                <LogOut class="mr-2 size-4" />
                退出登录
              </UiDropdownMenuItem>
            </UiDropdownMenuContent>
          </UiDropdownMenu>
        </UiSidebarMenuItem>
      </UiSidebarMenu>
    </UiSidebarFooter>

    <UiSidebarRail />
  </UiSidebar>
</template>
