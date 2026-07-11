<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  Activity,
  BrainCircuit,
  CandlestickChart,
  LogOut,
  Settings2,
  TrendingUp,
  Trophy,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navItems = [
  { title: '看板', icon: Activity, path: '/dashboard' },
  { title: '排名表', icon: Trophy, path: '/ranking' },
  { title: '行情', icon: CandlestickChart, path: '/market' },
  { title: '模型', icon: BrainCircuit, path: '/model' },
  { title: '设置', icon: Settings2, path: '/settings' },
]

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
    <UiSidebarHeader class="border-b px-4 py-3">
      <UiSidebarMenu>
        <UiSidebarMenuItem>
          <UiSidebarMenuButton size="lg" class="gap-3">
            <div class="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <TrendingUp class="size-4" />
            </div>
            <div class="grid flex-1 text-left text-sm leading-tight">
              <span class="truncate font-bold">Stock Analysis</span>
              <span class="truncate text-xs text-muted-foreground">AI 选股分析</span>
            </div>
          </UiSidebarMenuButton>
        </UiSidebarMenuItem>
      </UiSidebarMenu>
    </UiSidebarHeader>

    <UiSidebarContent>
      <UiSidebarGroup>
        <UiSidebarGroupLabel>Workspace</UiSidebarGroupLabel>
        <UiSidebarMenu>
          <UiSidebarMenuItem v-for="item in navItems" :key="item.path">
            <UiSidebarMenuButton
              as-child
              :is-active="isActive(item.path)"
              :tooltip="item.title"
            >
              <router-link :to="item.path" class="flex items-center gap-2">
                <component :is="item.icon" class="size-4" />
                <span>{{ item.title }}</span>
              </router-link>
            </UiSidebarMenuButton>
          </UiSidebarMenuItem>
        </UiSidebarMenu>
      </UiSidebarGroup>
    </UiSidebarContent>

    <UiSidebarFooter class="border-t">
      <UiSidebarMenu>
        <UiSidebarMenuItem>
          <UiDropdownMenu>
            <UiDropdownMenuTrigger as-child>
              <UiSidebarMenuButton size="lg" class="gap-3">
                <UiAvatar class="size-8 rounded-lg">
                  <UiAvatarFallback class="rounded-lg">{{ userInitial }}</UiAvatarFallback>
                </UiAvatar>
                <div class="grid flex-1 text-left text-sm leading-tight">
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
