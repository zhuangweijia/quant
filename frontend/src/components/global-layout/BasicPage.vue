<script setup lang="ts">
import { cn } from '@/lib/utils'

const props = withDefaults(defineProps<{
  title?: string
  description?: string
  sticky?: boolean
  class?: string
}>(), {
  title: '',
  description: '',
  sticky: false,
  class: '',
})
</script>

<template>
  <div :class="cn('space-y-6', props.class)">
    <div
      :class="cn(
        'flex items-center justify-between gap-4',
        sticky && 'sticky top-0 z-10 bg-background/80 backdrop-blur-sm py-4 -mt-6 px-1',
      )"
    >
      <div v-if="title" class="space-y-1">
        <h1 class="text-2xl font-bold tracking-tight">{{ title }}</h1>
        <p v-if="description" class="text-muted-foreground">{{ description }}</p>
      </div>
      <div class="flex items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
    <slot />
  </div>
</template>
