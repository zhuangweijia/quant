<script setup lang="ts">
import { computed, ref } from 'vue'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import type { AdviceAction, AdviceItemResponse, AdviceItemStatus } from '@/types/advice'

const props = defineProps<{ items: AdviceItemResponse[] }>()
const emit = defineEmits<{ execute: [item: AdviceItemResponse] }>()

const actionOrder: Record<AdviceAction, number> = {
  exit: 0,
  reduce: 1,
  buy: 2,
  increase: 3,
  hold: 4,
}
const actionLabels: Record<AdviceAction, string> = {
  exit: '清仓',
  reduce: '减持',
  buy: '买入',
  increase: '加仓',
  hold: '继续持有',
}
const statusLabels: Record<AdviceItemStatus, string> = {
  pending: '待处理',
  executed: '已执行',
  partial: '部分执行',
  skipped: '未执行',
  expired: '已过期',
}

const holdsOpen = ref(false)
const sortedItems = computed(() => [...props.items].sort((left, right) => (
  actionOrder[left.action] - actionOrder[right.action] || left.symbol.localeCompare(right.symbol)
)))
const actionItems = computed(() => sortedItems.value.filter(item => item.action !== 'hold'))
const holdItems = computed(() => sortedItems.value.filter(item => item.action === 'hold'))

function percent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function signedQuantity(value: number): string {
  return value > 0 ? `+${value}` : String(value)
}
</script>

<template>
  <div class="space-y-4">
    <Card
      v-for="item in actionItems"
      :key="item.id"
      data-testid="advice-action"
      :data-action="item.action"
      data-read-only="false"
    >
      <CardHeader>
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle class="flex flex-wrap items-center gap-2 text-base">
              {{ item.name }}
              <span class="font-mono text-sm text-muted-foreground">{{ item.symbol }}</span>
              <Badge variant="outline">{{ actionLabels[item.action] }}</Badge>
              <Badge>{{ statusLabels[item.status] }}</Badge>
            </CardTitle>
            <CardDescription class="mt-2">{{ item.industry ?? '行业未知' }} · 置信度 {{ item.confidence }}<template v-if="item.rank !== null"> · 排名 {{ item.rank }}</template></CardDescription>
          </div>
          <p class="text-sm">评分 <span class="font-semibold">{{ percent(item.score) }}</span></p>
        </div>
      </CardHeader>
      <CardContent class="space-y-5">
        <dl class="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2 lg:grid-cols-5">
          <div><dt class="text-muted-foreground">当前 / 目标数量</dt><dd class="mt-1 font-medium">{{ item.current_quantity }} / {{ item.target_quantity }}（{{ signedQuantity(item.delta_quantity) }}）</dd></div>
          <div><dt class="text-muted-foreground">当前平均成本</dt><dd class="mt-1 font-mono">{{ item.current_average_cost ?? '—' }}</dd></div>
          <div><dt class="text-muted-foreground">当前 / 目标权重</dt><dd class="mt-1 font-medium">{{ percent(item.current_weight) }} / {{ percent(item.target_weight) }}</dd></div>
          <div><dt class="text-muted-foreground">参考价</dt><dd class="mt-1 font-mono">{{ item.reference_price }} CNY</dd></div>
          <div><dt class="text-muted-foreground">价格容忍范围</dt><dd class="mt-1 font-medium">±{{ percent(item.price_tolerance) }}</dd></div>
        </dl>
        <div class="grid gap-4 text-sm lg:grid-cols-2">
          <section><h3 class="font-medium">支持因素</h3><ul class="mt-2 list-disc space-y-1 pl-5 text-muted-foreground"><li v-for="factor in item.positive_factors" :key="factor">{{ factor }}</li><li v-if="!item.positive_factors.length">暂无</li></ul></section>
          <section><h3 class="font-medium">主要风险</h3><ul class="mt-2 list-disc space-y-1 pl-5 text-muted-foreground"><li v-for="risk in item.risks" :key="risk">{{ risk }}</li><li v-if="!item.risks.length">暂无</li></ul></section>
          <section><h3 class="font-medium">失效条件</h3><ul class="mt-2 list-disc space-y-1 pl-5 text-muted-foreground"><li v-for="condition in item.invalidation_conditions" :key="condition">{{ condition }}</li><li v-if="!item.invalidation_conditions.length">暂无</li></ul></section>
          <section><h3 class="font-medium">约束说明</h3><ul class="mt-2 list-disc space-y-1 pl-5 text-muted-foreground"><li v-for="note in item.constraint_notes" :key="note">{{ note }}</li><li v-if="!item.constraint_notes.length">无额外说明</li></ul></section>
        </div>
        <section v-if="item.execution" class="rounded-lg border bg-muted/30 p-3 text-sm">
          <h3 class="font-medium">已记录执行</h3>
          <p class="mt-2 text-muted-foreground">
            {{ statusLabels[item.execution.disposition] }} · 数量 {{ item.execution.quantity }} ·
            成交价 {{ item.execution.price ?? '—' }} · 手续费 {{ item.execution.fee }} ·
            时间 {{ item.execution.executed_at ?? '—' }} ·
            {{ item.execution.within_price_band ? '建议范围内' : '已确认范围外或过期执行' }}
          </p>
          <p v-if="item.execution.reason" class="mt-1 text-muted-foreground">说明：{{ item.execution.reason }}</p>
        </section>
      </CardContent>
      <CardFooter class="justify-between border-t pt-4">
        <p class="text-xs text-muted-foreground">{{ item.execution ? `当前执行修订版本 ${item.execution.revision}` : '尚未记录实际执行' }}</p>
        <Button :data-testid="`execute-${item.id}`" type="button" @click="emit('execute', item)">
          {{ item.execution ? '更正执行记录' : '记录实际执行' }}
        </Button>
      </CardFooter>
    </Card>

    <Card v-if="holdItems.length">
      <CardHeader>
        <button
          data-testid="toggle-holds"
          type="button"
          class="flex w-full items-center justify-between text-left"
          @click="holdsOpen = !holdsOpen"
        >
          <span><span class="font-semibold">继续持有 {{ holdItems.length }}</span><span class="ml-2 text-sm text-muted-foreground">默认折叠，只供查看</span></span>
          <ChevronUp v-if="holdsOpen" class="size-4" /><ChevronDown v-else class="size-4" />
        </button>
      </CardHeader>
      <CardContent v-if="holdsOpen" class="space-y-3">
        <article
          v-for="item in holdItems"
          :key="item.id"
          :data-testid="`hold-advice-${item.id}`"
          data-read-only="true"
          class="rounded-lg border p-4 text-sm"
        >
          <div class="flex flex-wrap items-center gap-2"><span class="font-medium">{{ item.name }}</span><span class="font-mono text-muted-foreground">{{ item.symbol }}</span><Badge variant="outline">只读</Badge><Badge>{{ statusLabels[item.status] }}</Badge></div>
          <dl class="mt-3 grid gap-2 text-muted-foreground sm:grid-cols-2 lg:grid-cols-4">
            <div><dt>当前 / 目标数量</dt><dd class="text-foreground">{{ item.current_quantity }} / {{ item.target_quantity }}（{{ signedQuantity(item.delta_quantity) }}）</dd></div>
            <div><dt>当前平均成本</dt><dd class="font-mono text-foreground">{{ item.current_average_cost ?? '—' }}</dd></div>
            <div><dt>当前 / 目标权重</dt><dd class="text-foreground">{{ percent(item.current_weight) }} / {{ percent(item.target_weight) }}</dd></div>
            <div><dt>参考价 / 容忍范围</dt><dd class="text-foreground">{{ item.reference_price }} / ±{{ percent(item.price_tolerance) }}</dd></div>
            <div><dt>评分 / 置信度</dt><dd class="text-foreground">{{ percent(item.score) }} / {{ item.confidence }}</dd></div>
            <div v-if="item.rank !== null"><dt>排名</dt><dd class="text-foreground">{{ item.rank }}</dd></div>
          </dl>
          <div class="mt-4 grid gap-3 lg:grid-cols-2">
            <section><h3 class="font-medium">支持因素</h3><ul class="mt-1 list-disc pl-5 text-muted-foreground"><li v-for="factor in item.positive_factors" :key="factor">{{ factor }}</li><li v-if="!item.positive_factors.length">暂无</li></ul></section>
            <section><h3 class="font-medium">主要风险</h3><ul class="mt-1 list-disc pl-5 text-muted-foreground"><li v-for="risk in item.risks" :key="risk">{{ risk }}</li><li v-if="!item.risks.length">暂无</li></ul></section>
            <section><h3 class="font-medium">失效条件</h3><ul class="mt-1 list-disc pl-5 text-muted-foreground"><li v-for="condition in item.invalidation_conditions" :key="condition">{{ condition }}</li><li v-if="!item.invalidation_conditions.length">暂无</li></ul></section>
            <section><h3 class="font-medium">约束说明</h3><ul class="mt-1 list-disc pl-5 text-muted-foreground"><li v-for="note in item.constraint_notes" :key="note">{{ note }}</li><li v-if="!item.constraint_notes.length">无额外说明</li></ul></section>
          </div>
        </article>
      </CardContent>
    </Card>
  </div>
</template>
