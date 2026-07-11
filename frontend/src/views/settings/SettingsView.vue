<script setup lang="ts">
import { ref } from 'vue'
import { toast } from 'vue-sonner'
import { settingsApi } from '@/api/settings'
import { BasicPage } from '@/components/global-layout'
import Button from '@/components/ui/button/Button.vue'
import Label from '@/components/ui/label/Label.vue'
import Input from '@/components/ui/input/Input.vue'
import {
  Card as UiCard,
  CardHeader as UiCardHeader,
  CardContent as UiCardContent,
  CardTitle as UiCardTitle,
  CardDescription as UiCardDescription,
} from '@/components/ui/card'
</script>

<template>
  <BasicPage title="系统设置" description="通知配置、系统参数、个人资料">
    <div class="space-y-6">
      <UiCard>
        <UiCardHeader>
          <UiCardTitle>系统参数</UiCardTitle>
          <UiCardDescription>分析引擎配置参数</UiCardDescription>
        </UiCardHeader>
        <UiCardContent>
          <p class="text-sm text-muted-foreground">配置面板即将更新</p>
        </UiCardContent>
      </UiCard>
    </div>
  </BasicPage>
</template>
