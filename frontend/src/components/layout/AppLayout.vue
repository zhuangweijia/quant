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
      <header class="flex h-16 shrink-0 items-center gap-4 border-b bg-background/95 px-5 backdrop-blur supports-[backdrop-filter]:bg-background/80 lg:px-6">
        <UiSidebarTrigger class="size-9" />
        <UiSeparator orientation="vertical" class="h-7" />
        <Button
          variant="outline"
          size="sm"
          class="h-9 w-11 justify-start rounded-full px-3 text-muted-foreground shadow-none md:w-64 md:px-4"
          @click="openCommandMenu"
        >
          <Search class="size-4" />
          <span class="hidden flex-1 text-left md:inline">搜索...</span>
          <kbd class="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground md:inline-flex">
            ⌘K
          </kbd>
        </Button>
        <div class="flex-1" />
        <div class="flex items-center gap-2">
          <UiButton variant="ghost" size="icon" class="size-9 rounded-full" @click="toggleTheme">
            <SunMedium v-if="!isDark" class="size-4" />
            <MoonStar v-else class="size-4" />
          </UiButton>
        </div>
      </header>

      <main class="flex-1 overflow-auto">
        <div class="mx-auto w-full max-w-7xl px-5 py-7 sm:px-6 lg:px-8 lg:py-8">
          <router-view v-slot="{ Component, route }">
            <transition name="page" mode="out-in">
              <component :is="Component" :key="route.path" />
            </transition>
          </router-view>
        </div>
      </main>
    </UiSidebarInset>
    <CommandMenu ref="commandMenuRef" />
  </UiSidebarProvider>
</template>
