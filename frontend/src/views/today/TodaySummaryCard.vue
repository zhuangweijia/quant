<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { DailyAdviceResponse } from '@/types/advice'

defineProps<{ advice: DailyAdviceResponse }>()

function percent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}
</script>

<template>
  <div class="space-y-4">
    <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card>
        <CardHeader class="pb-2"><CardDescription>总资产</CardDescription></CardHeader>
        <CardContent class="font-mono text-lg font-semibold">{{ advice.total_asset }} CNY</CardContent>
      </Card>
      <Card>
        <CardHeader class="pb-2"><CardDescription>当前 / 目标仓位</CardDescription></CardHeader>
        <CardContent class="text-lg font-semibold">{{ percent(advice.current_exposure) }} / {{ percent(advice.target_exposure) }}</CardContent>
      </Card>
      <Card>
        <CardHeader class="pb-2"><CardDescription>当前 / 预计现金</CardDescription></CardHeader>
        <CardContent class="font-mono text-sm font-semibold">{{ advice.current_cash }} / {{ advice.estimated_cash }}</CardContent>
      </Card>
      <Card>
        <CardHeader class="pb-2"><CardDescription>信号日期</CardDescription></CardHeader>
        <CardContent><p class="font-semibold">{{ advice.signal_date }}</p><p class="text-xs text-muted-foreground">适用于下一交易日</p></CardContent>
      </Card>
    </section>

    <Card>
      <CardHeader>
        <CardTitle class="text-base">建议口径</CardTitle>
        <CardDescription>建议版本 {{ advice.version }}；金额按服务端精确十进制值展示。</CardDescription>
      </CardHeader>
      <CardContent>
        <dl class="grid gap-x-8 gap-y-3 text-sm md:grid-cols-3">
          <div><dt class="text-muted-foreground">生成时间</dt><dd class="mt-1">{{ advice.generated_at }}</dd></div>
          <div><dt class="text-muted-foreground">数据日期</dt><dd class="mt-1">{{ advice.data_date }}</dd></div>
          <div><dt class="text-muted-foreground">模型版本</dt><dd class="mt-1">{{ advice.model_version }}</dd></div>
        </dl>
      </CardContent>
    </Card>

    <div
      v-if="advice.stale_warnings.length || advice.constraint_violations.length"
      class="space-y-3 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 text-sm"
    >
      <p class="flex items-center gap-2 font-medium text-amber-700 dark:text-amber-300">
        <AlertTriangle class="size-4" />数据与约束提醒
      </p>
      <p v-for="warning in advice.stale_warnings" :key="warning">{{ warning }}</p>
      <p v-for="violation in advice.constraint_violations" :key="violation">{{ violation }}</p>
    </div>
  </div>
</template>
