<script setup lang="ts">
import AppSidebar from '@/components/app-sidebar/index.vue'
import CommandMenu from '@/components/command-menu/index.vue'
</script>

<template>
  <UiSidebarProvider>
    <AppSidebar />
    <CommandMenu />
    <UiSidebarInset>
      <header class="flex h-16 shrink-0 items-center gap-4 border-b bg-background/95 px-5 backdrop-blur supports-[backdrop-filter]:bg-background/80 lg:px-6">
        <UiSidebarTrigger class="size-9" />
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
  </UiSidebarProvider>
</template>
