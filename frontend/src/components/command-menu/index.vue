<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from '@/composables/useTheme'
import {
  CommandDialog as UiCommandDialog,
  CommandEmpty as UiCommandEmpty,
  CommandGroup as UiCommandGroup,
  CommandInput as UiCommandInput,
  CommandItem as UiCommandItem,
  CommandList as UiCommandList,
  CommandSeparator as UiCommandSeparator,
} from '@/components/ui/command'
import {
  Activity,
  CandlestickChart,
  FlaskConical,
  MoonStar,
  Settings2,
  ShieldAlert,
  Sparkles,
  SunMedium,
  WalletCards,
} from 'lucide-vue-next'

const router = useRouter()
const { isDark, toggleTheme } = useTheme()
const open = ref(false)

const navItems = [
  { title: '看板', icon: Activity, path: '/dashboard' },
  { title: '行情', icon: CandlestickChart, path: '/market' },
  { title: '策略', icon: Sparkles, path: '/strategy' },
  { title: '回测', icon: FlaskConical, path: '/backtest' },
  { title: '交易', icon: WalletCards, path: '/trade' },
  { title: '风控', icon: ShieldAlert, path: '/risk' },
  { title: '设置', icon: Settings2, path: '/settings' },
]

function handleSelect(path: string) {
  open.value = false
  router.push(path)
}

function handleTheme() {
  open.value = false
  toggleTheme()
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
    e.preventDefault()
    open.value = !open.value
  }
}

function setOpen(value: boolean) {
  open.value = value
}

onMounted(() => document.addEventListener('keydown', handleKeyDown))
onUnmounted(() => document.removeEventListener('keydown', handleKeyDown))

defineExpose({ setOpen })
</script>

<template>
  <UiCommandDialog v-model:open="open">
    <UiCommandInput placeholder="搜索页面或执行命令..." />
    <UiCommandList>
      <UiCommandEmpty>没有找到匹配的结果</UiCommandEmpty>
      <UiCommandGroup heading="导航">
        <UiCommandItem
          v-for="item in navItems"
          :key="item.path"
          :value="item.title"
          @select="handleSelect(item.path)"
        >
          <component :is="item.icon" class="mr-2 size-4" />
          <span>{{ item.title }}</span>
        </UiCommandItem>
      </UiCommandGroup>
      <UiCommandSeparator />
      <UiCommandGroup heading="操作">
        <UiCommandItem value="切换主题" @select="handleTheme">
          <SunMedium v-if="isDark" class="mr-2 size-4" />
          <MoonStar v-else class="mr-2 size-4" />
          <span>切换主题</span>
        </UiCommandItem>
      </UiCommandGroup>
    </UiCommandList>
  </UiCommandDialog>
</template>
