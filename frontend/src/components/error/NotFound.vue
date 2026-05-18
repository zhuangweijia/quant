<script setup lang="ts">
import { useRouter } from 'vue-router'
import Button from '@/components/ui/button/Button.vue'
import { FileQuestion } from 'lucide-vue-next'

const router = useRouter()
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-6 bg-background">
    <div class="text-center space-y-6 max-w-md">
      <div class="flex justify-center">
        <div class="rounded-full bg-muted p-6">
          <FileQuestion class="size-12 text-muted-foreground" />
        </div>
      </div>
      <div class="space-y-2">
        <h1 class="text-4xl font-bold tracking-tight">404</h1>
        <p class="text-muted-foreground">页面不存在或已被移除。</p>
      </div>
      <div class="flex gap-3 justify-center">
        <Button @click="router.push('/dashboard')">返回首页</Button>
        <Button variant="outline" @click="router.back()">返回上页</Button>
      </div>
    </div>
  </div>
</template>
