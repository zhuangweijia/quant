<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import type { SetupStatus } from '@/api/setup'
import { setupApi } from '@/api/setup'
import { rankingApi } from '@/api/ranking'
import { analysisApi } from '@/api/analysis'
import { useWebSocket } from '@/composables/useWebSocket'
import { useAuthStore } from '@/stores/auth'
import {
  Card as UiCard, CardContent as UiCardContent, CardHeader as UiCardHeader,
  CardTitle as UiCardTitle,
} from '@/components/ui/card'
import Badge from '@/components/ui/badge/Badge.vue'
import { Activity, Trophy, BrainCircuit, AlertCircle, Loader2 } from 'lucide-vue-next'
import SetupStatusCard from './SetupStatusCard.vue'
import { getSetupPresentation } from './setup-state'
import { useSetupPolling } from './useSetupPolling'

const router = useRouter()
const authStore = useAuthStore()
const topStocks = ref<any[]>([])
const analysisStatus = ref<any>(null)
const setupStatus = ref<SetupStatus | null>(null)
const loading = ref(true)
const startingSetup = ref(false)
const triggeringAnalysis = ref(false)

const isAdmin = computed(() => authStore.role === 'admin')
const analysisRunning = computed(() => (
  triggeringAnalysis.value || analysisStatus.value?.status === 'running'
))

const stages = [
  { key: 'data_sync', label: '数据同步' },
  { key: 'northbound_sync', label: '北向资金' },
  { key: 'feature_engineering', label: '特征计算' },
  { key: 'model_prediction', label: '模型预测' },
  { key: 'shap_explanation', label: 'SHAP解释' },
  { key: 'ranking', label: '排名生成' },
]

const pipelineProgress = computed(() => {
  if (!analysisStatus.value?.stages) return null
  const stageList = Object.entries(analysisStatus.value.stages)
  const done = stageList.filter(([, v]: any) => v.status === 'done').length
  return { done, total: stageList.length }
})

async function fetchData() {
  loading.value = true
  try {
    const [rankingResult, analysisResult, setupResult] = await Promise.allSettled([
      rankingApi.getRankings({ date: 'today', label: '强推', page: 1, size: 10 }),
      analysisApi.getStatus(),
      setupApi.getStatus(),
    ])

    if (rankingResult.status === 'fulfilled') {
      topStocks.value = rankingResult.value.data.data?.items ?? []
    }
    if (analysisResult.status === 'fulfilled') {
      analysisStatus.value = analysisResult.value.data.data
    }
    if (setupResult.status === 'fulfilled' && setupResult.value.data.data) {
      setupStatus.value = setupResult.value.data.data
      setupPolling.sync(setupStatus.value)
    }

    for (const result of [rankingResult, analysisResult, setupResult]) {
      if (result.status === 'rejected') console.error('Dashboard request failed', result.reason)
    }
  } catch (e) {
    console.error('Dashboard fetch failed', e)
  } finally {
    loading.value = false
  }
}

async function fetchSetupStatus(): Promise<SetupStatus> {
  const response = await setupApi.getStatus()
  if (!response.data.data) throw new Error('首次配置状态响应为空')
  return response.data.data
}

function handlePolledSetupStatus(status: SetupStatus) {
  const wasInitializing = setupStatus.value?.readiness === 'initializing'
  setupStatus.value = status
  if (wasInitializing && status.readiness !== 'initializing') void fetchData()
}

const setupPolling = useSetupPolling(fetchSetupStatus, handlePolledSetupStatus)

async function handleStartSetup() {
  if (startingSetup.value) return
  startingSetup.value = true
  try {
    await setupApi.start()
    toast.success(setupStatus.value?.readiness === 'failed' ? '已继续初始化' : '首次配置已启动')
    setupStatus.value = await fetchSetupStatus()
    setupPolling.sync(setupStatus.value)
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '启动首次配置失败')
  } finally {
    startingSetup.value = false
  }
}

async function handleRunAnalysis() {
  if (triggeringAnalysis.value) return
  triggeringAnalysis.value = true
  try {
    await analysisApi.trigger()
    toast.success('今日分析已启动')
    const response = await analysisApi.getStatus()
    analysisStatus.value = response.data.data
  } catch (error: any) {
    toast.error(error?.response?.data?.detail || '启动今日分析失败')
  } finally {
    triggeringAnalysis.value = false
  }
}

const emptyMessage = computed(() => {
  if (!setupStatus.value) return '正在读取推荐系统状态...'
  return getSetupPresentation(setupStatus.value, analysisStatus.value).emptyMessage
})

const { subscribe, onMessage } = useWebSocket()
const cleanups: (() => void)[] = []
onMounted(() => {
  fetchData()
  subscribe('analysis:progress', 'analysis:ranking_ready')
  cleanups.push(onMessage('analysis:ranking_ready', () => fetchData()))
  cleanups.push(onMessage('analysis:progress', () => analysisApi.getStatus().then((response) => {
    analysisStatus.value = response.data.data
  })))
})

onUnmounted(() => {
  setupPolling.stop()
  cleanups.forEach(cleanup => cleanup())
})

function stageStatus(key: string): string {
  return analysisStatus.value?.stages?.[key]?.status || 'pending'
}
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold flex items-center gap-2">
      <Activity class="size-6 text-primary" />市场概览
    </h1>

    <SetupStatusCard
      v-if="setupStatus"
      :status="setupStatus"
      :is-admin="isAdmin"
      :starting="startingSetup"
      :analysis-running="analysisRunning"
      @start="handleStartSetup"
      @run-analysis="handleRunAnalysis"
      @open-model="router.push('/model')"
    />

    <!-- Pipeline Status -->
    <UiCard v-if="analysisStatus && analysisStatus.status !== 'idle'">
      <UiCardHeader>
        <UiCardTitle class="flex items-center gap-2 text-base">
          <Loader2 v-if="analysisStatus.status === 'running'" class="size-4 animate-spin text-blue-500" />
          <BrainCircuit v-else class="size-4 text-muted-foreground" />
          分析 Pipeline
          <Badge v-if="pipelineProgress" variant="secondary" class="text-xs">
            {{ pipelineProgress.done }}/{{ pipelineProgress.total }}
          </Badge>
        </UiCardTitle>
      </UiCardHeader>
      <UiCardContent>
        <div class="flex flex-wrap gap-2">
          <div v-for="stage in stages" :key="stage.key" class="flex items-center gap-1.5">
            <div class="size-2 rounded-full"
              :class="{
                'bg-green-500': stageStatus(stage.key) === 'done',
                'bg-blue-500 animate-pulse': stageStatus(stage.key) === 'running',
                'bg-red-500': stageStatus(stage.key) === 'failed',
                'bg-muted': stageStatus(stage.key) === 'pending',
              }" />
            <span class="text-xs text-muted-foreground">{{ stage.label }}</span>
          </div>
        </div>
        <div v-if="analysisStatus.error" class="mt-2 flex items-center gap-1 text-sm text-red-500">
          <AlertCircle class="size-3" />{{ analysisStatus.error }}
        </div>
      </UiCardContent>
    </UiCard>

    <!-- Top 10 Strong Buy -->
    <UiCard>
      <UiCardHeader>
        <UiCardTitle class="flex items-center gap-2">
          <Trophy class="size-5 text-yellow-500" />今日强推 Top 10
        </UiCardTitle>
      </UiCardHeader>
      <UiCardContent>
        <div v-if="loading" class="py-8 text-center text-muted-foreground">加载中...</div>
        <div v-else-if="!topStocks.length" class="py-8 text-center text-muted-foreground">
          {{ emptyMessage }}
        </div>
        <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div
            v-for="stock in topStocks" :key="stock.symbol"
            class="cursor-pointer rounded-lg border p-3 hover:bg-muted/50 transition-colors"
            @click="router.push(`/stock/${stock.symbol}`)"
          >
            <div class="flex items-center justify-between mb-1">
              <span class="text-xs font-mono text-muted-foreground">#{{ stock.rank }}</span>
              <Badge variant="default" class="text-[10px] px-1.5 py-0">{{ stock.label }}</Badge>
            </div>
            <p class="font-medium text-sm truncate">{{ stock.name || stock.symbol }}</p>
            <p class="text-xs font-mono text-muted-foreground">{{ stock.symbol }}</p>
            <p class="text-lg font-bold text-green-600 dark:text-green-400 mt-1">{{ stock.score.toFixed(3) }}</p>
          </div>
        </div>
      </UiCardContent>
    </UiCard>

    <!-- Quick Stats -->
    <div class="grid gap-4 sm:grid-cols-3" v-if="!loading && topStocks.length">
      <UiCard>
        <UiCardContent class="pt-6">
          <div class="text-2xl font-bold text-green-600 dark:text-green-400">
            {{ topStocks.length }}+
          </div>
          <p class="text-xs text-muted-foreground mt-1">强推股票</p>
        </UiCardContent>
      </UiCard>
      <UiCard>
        <UiCardContent class="pt-6">
          <div class="text-2xl font-bold">{{ analysisStatus?.status === 'running' ? '运行中' : '已完成' }}</div>
          <p class="text-xs text-muted-foreground mt-1">Pipeline 状态</p>
        </UiCardContent>
      </UiCard>
      <UiCard>
        <UiCardContent class="pt-6">
          <div class="text-2xl font-bold">{{ analysisStatus?.trigger_type === 'scheduled' ? '自动' : '手动' }}</div>
          <p class="text-xs text-muted-foreground mt-1">触发方式</p>
        </UiCardContent>
      </UiCard>
    </div>
  </div>
</template>
