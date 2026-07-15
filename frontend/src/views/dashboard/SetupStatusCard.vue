<script setup lang="ts">
import { computed } from 'vue'
import {
  AlertCircle,
  CheckCircle2,
  Circle,
  Loader2,
  RefreshCw,
  Rocket,
} from 'lucide-vue-next'

import type { SetupStatus } from '@/api/setup'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { getSetupPresentation } from './setup-state'

const props = defineProps<{
  status: SetupStatus
  isAdmin: boolean
  starting: boolean
  analysisRunning: boolean
}>()

const emit = defineEmits<{
  start: []
  'run-analysis': []
  'open-model': []
}>()

const setupStages = [
  { key: 'constituents', label: '同步成分股' },
  { key: 'daily_bars', label: '同步历史行情' },
  { key: 'fundamentals', label: '同步基本面' },
  { key: 'validation', label: '校验数据' },
  { key: 'training', label: '训练模型' },
  { key: 'activation', label: '激活模型' },
  { key: 'analysis', label: '生成推荐' },
]

const presentation = computed(() => getSetupPresentation(
  props.status,
  { status: props.analysisRunning ? 'running' : 'idle' },
))

const progress = computed(() => {
  const stages = props.status.run?.stages ?? {}
  let units = setupStages.filter(stage => stages[stage.key]?.status === 'done').length
  const dailyBars = stages.daily_bars
  if (dailyBars?.status === 'running' && dailyBars.total) {
    units += Math.min((dailyBars.current ?? 0) / dailyBars.total, 1)
  }
  return Math.round(units / setupStages.length * 100)
})

const currentStage = computed(() => {
  const key = props.status.run?.current_stage
  return setupStages.find(stage => stage.key === key)
})

const dailyBarProgress = computed(() => props.status.run?.stages.daily_bars)
const showOpenModel = computed(() => {
  const stage = props.status.run?.current_stage
  return props.status.readiness === 'failed' && ['training', 'activation'].includes(stage ?? '')
})
</script>

<template>
  <Card :class="status.readiness === 'failed' ? 'border-destructive/40' : ''">
    <CardHeader class="gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div class="space-y-1.5">
        <CardTitle class="flex items-center gap-2 text-base">
          <Loader2 v-if="status.readiness === 'initializing'" class="size-4 animate-spin text-primary" />
          <AlertCircle v-else-if="status.readiness === 'failed'" class="size-4 text-destructive" />
          <CheckCircle2 v-else-if="status.readiness === 'ready'" class="size-4 text-green-600" />
          <Rocket v-else class="size-4 text-primary" />
          {{ presentation.title }}
          <Badge v-if="status.readiness === 'ready'" variant="secondary">已就绪</Badge>
        </CardTitle>
        <p class="text-sm text-muted-foreground">{{ presentation.description }}</p>
      </div>

      <div v-if="isAdmin" class="flex shrink-0 flex-wrap gap-2">
        <Button
          v-if="presentation.action === 'start_setup' && status.can_start"
          data-testid="setup-primary-action"
          :loading="starting"
          @click="emit('start')"
        >
          <RefreshCw v-if="status.readiness === 'failed'" />
          <Rocket v-else />
          {{ presentation.actionLabel }}
        </Button>
        <Button
          v-else-if="presentation.action === 'run_analysis' && status.can_run_analysis"
          data-testid="setup-primary-action"
          :loading="analysisRunning"
          @click="emit('run-analysis')"
        >
          <Rocket />
          {{ presentation.actionLabel }}
        </Button>
        <Button v-if="showOpenModel" variant="outline" @click="emit('open-model')">
          查看模型
        </Button>
      </div>
    </CardHeader>

    <CardContent v-if="status.readiness === 'initializing' || status.readiness === 'failed'" class="space-y-4">
      <div class="space-y-2">
        <div class="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {{ currentStage ? currentStage.label : (status.readiness === 'failed' ? '初始化中断' : '准备开始') }}
            <template v-if="dailyBarProgress?.status === 'running' && dailyBarProgress.total">
              · {{ dailyBarProgress.current ?? 0 }}/{{ dailyBarProgress.total }}
            </template>
          </span>
          <span>{{ progress }}%</span>
        </div>
        <Progress :model-value="progress" />
      </div>

      <div class="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="stage in setupStages" :key="stage.key" class="flex items-center gap-2 text-xs">
          <CheckCircle2 v-if="status.run?.stages[stage.key]?.status === 'done'" class="size-3.5 text-green-600" />
          <Loader2 v-else-if="status.run?.stages[stage.key]?.status === 'running'" class="size-3.5 animate-spin text-primary" />
          <AlertCircle v-else-if="status.run?.stages[stage.key]?.status === 'failed'" class="size-3.5 text-destructive" />
          <Circle v-else class="size-3.5 text-muted-foreground/50" />
          <span>{{ stage.label }}</span>
        </div>
      </div>

      <p v-if="status.run?.error" class="flex items-start gap-2 text-sm text-destructive">
        <AlertCircle class="mt-0.5 size-4 shrink-0" />
        {{ status.run.error }}
      </p>
    </CardContent>
  </Card>
</template>
