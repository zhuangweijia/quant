<script setup lang="ts">
import { useTheme } from '@/composables/useTheme'
import AppSidebar from '@/components/app-sidebar/index.vue'
import CommandMenu from '@/components/command-menu/index.vue'
import {
  MoonStar,
  Search,
  SunMedium,
} from 'lucide-vue-next'

const { isDark, toggleTheme } = useTheme()
const commandMenuRef = ref<InstanceType<typeof CommandMenu> | null>(null)

function openCommandMenu() {
  commandMenuRef.value?.setOpen(true)
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
