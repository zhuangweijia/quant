<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useRiskStore } from '@/stores/risk'
import {
  Activity,
  CandlestickChart,
  FlaskConical,
  LogOut,
  Settings2,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  WalletCards,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const riskStore = useRiskStore()

const navItems = [
  { title: '看板', icon: Activity, path: '/dashboard' },
  { title: '行情', icon: CandlestickChart, path: '/market' },
  { title: '策略', icon: Sparkles, path: '/strategy', requireRole: 'trader' },
  { title: '回测', icon: FlaskConical, path: '/backtest', requireRole: 'trader' },
  { title: '交易', icon: WalletCards, path: '/trade', requireRole: 'trader' },
  { title: '风控', icon: ShieldAlert, path: '/risk', requireRole: 'trader' },
  { title: '设置', icon: Settings2, path: '/settings' },
]

const visibleNavItems = computed(() =>
  navItems.filter(item => !item.requireRole || authStore.role !== 'viewer')
)

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
              <span class="truncate font-bold">Quant Desk</span>
              <span class="truncate text-xs text-muted-foreground">Systematic trading</span>
            </div>
          </UiSidebarMenuButton>
        </UiSidebarMenuItem>
      </UiSidebarMenu>
    </UiSidebarHeader>

    <UiSidebarContent>
      <UiSidebarGroup>
        <UiSidebarGroupLabel>Workspace</UiSidebarGroupLabel>
        <UiSidebarMenu>
          <UiSidebarMenuItem v-for="item in visibleNavItems" :key="item.path">
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
            <UiSidebarMenuBadge
              v-if="item.path === '/risk' && riskStore.unreadCount > 0"
            >
              {{ riskStore.unreadCount > 99 ? '99+' : riskStore.unreadCount }}
            </UiSidebarMenuBadge>
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
                    {{ authStore.role === 'admin' ? '管理员' : '交易员' }}
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
