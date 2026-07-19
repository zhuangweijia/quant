<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useTheme } from '@/composables/useTheme'
import { getAdminNav, getPrimaryNav } from '@/navigation/items'
import { useAuthStore } from '@/stores/auth'
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
  MoonStar,
  SunMedium,
} from 'lucide-vue-next'

const router = useRouter()
const authStore = useAuthStore()
const { isDark, toggleTheme } = useTheme()
const open = ref(false)

const primaryNav = computed(() => getPrimaryNav(authStore.role))
const adminNav = computed(() => getAdminNav(authStore.role))

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
          v-for="item in primaryNav"
          :key="item.path"
          :value="item.title"
          @select="handleSelect(item.path)"
        >
          <component :is="item.icon" class="mr-2 size-4" />
          <span>{{ item.title }}</span>
        </UiCommandItem>
      </UiCommandGroup>
      <template v-if="adminNav.length">
        <UiCommandSeparator />
        <UiCommandGroup heading="管理">
          <UiCommandItem
            v-for="item in adminNav"
            :key="item.path"
            :value="item.title"
            @select="handleSelect(item.path)"
          >
            <component :is="item.icon" class="mr-2 size-4" />
            <span>{{ item.title }}</span>
          </UiCommandItem>
        </UiCommandGroup>
      </template>
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
