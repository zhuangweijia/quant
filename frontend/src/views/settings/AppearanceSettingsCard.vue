<script setup lang="ts">
import { Monitor, Moon, Palette, Sun } from 'lucide-vue-next'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { useThemeStore, type ThemeColor } from '@/stores/theme'

const themeStore = useThemeStore()

const modes = [
  { value: 'light' as const, label: '亮色', icon: Sun },
  { value: 'dark' as const, label: '暗色', icon: Moon },
  { value: 'system' as const, label: '跟随系统', icon: Monitor },
]

const colors: Array<{ value: ThemeColor; label: string; swatch: string }> = [
  { value: 'zinc', label: '中性', swatch: 'bg-zinc-500' },
  { value: 'red', label: '红色', swatch: 'bg-red-500' },
  { value: 'rose', label: '玫红', swatch: 'bg-rose-500' },
  { value: 'orange', label: '橙色', swatch: 'bg-orange-500' },
  { value: 'green', label: '绿色', swatch: 'bg-green-500' },
  { value: 'blue', label: '蓝色', swatch: 'bg-blue-500' },
  { value: 'yellow', label: '黄色', swatch: 'bg-yellow-500' },
  { value: 'violet', label: '紫色', swatch: 'bg-violet-500' },
]

const radii = [
  { value: 0.375, key: 'compact', label: '紧凑' },
  { value: 0.625, key: 'default', label: '默认' },
  { value: 0.75, key: 'comfortable', label: '柔和' },
]
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle class="flex items-center gap-2">
        <Palette class="size-4" />
        外观偏好
      </CardTitle>
      <CardDescription>仅保存在当前浏览器，修改后立即生效。</CardDescription>
    </CardHeader>
    <CardContent class="space-y-6">
      <section class="space-y-3">
        <p class="text-sm font-medium">显示模式</p>
        <div class="grid gap-2 sm:grid-cols-3">
          <Button
            v-for="mode in modes"
            :key="mode.value"
            type="button"
            :data-testid="`appearance-mode-${mode.value}`"
            :variant="themeStore.colorMode === mode.value ? 'default' : 'outline'"
            :aria-pressed="themeStore.colorMode === mode.value"
            @click="themeStore.setColorMode(mode.value)"
          >
            <component :is="mode.icon" class="size-4" />
            {{ mode.label }}
          </Button>
        </div>
      </section>

      <section class="space-y-3">
        <p class="text-sm font-medium">主题色</p>
        <div class="flex flex-wrap gap-2">
          <Button
            v-for="color in colors"
            :key="color.value"
            type="button"
            :data-testid="`appearance-color-${color.value}`"
            :variant="themeStore.theme === color.value ? 'secondary' : 'ghost'"
            :aria-pressed="themeStore.theme === color.value"
            @click="themeStore.setTheme(color.value)"
          >
            <span :class="['size-3 rounded-full', color.swatch]" />
            {{ color.label }}
          </Button>
        </div>
      </section>

      <section class="space-y-3">
        <p class="text-sm font-medium">圆角密度</p>
        <div class="flex flex-wrap gap-2">
          <Button
            v-for="item in radii"
            :key="item.key"
            type="button"
            :data-testid="`appearance-radius-${item.key}`"
            :variant="themeStore.radius === item.value ? 'default' : 'outline'"
            :aria-pressed="themeStore.radius === item.value"
            @click="themeStore.setRadius(item.value)"
          >
            {{ item.label }}
          </Button>
        </div>
      </section>
    </CardContent>
  </Card>
</template>
