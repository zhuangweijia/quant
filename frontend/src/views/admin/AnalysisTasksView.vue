<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { Activity, AlertCircle, BrainCircuit, Loader2 } from 'lucide-vue-next'

import type { AnalysisStatus } from '@/api/analysis'
import { analysisApi } from '@/api/analysis'
import type { SetupStatus } from '@/api/setup'
import { setupApi } from '@/api/setup'
import { useWebSocket } from '@/composables/useWebSocket'
import { useAuthStore } from '@/stores/auth'
import Badge from '@/components/ui/badge/Badge.vue'
import {
  Card as UiCard,
  CardContent as UiCardContent,
  CardHeader as UiCardHeader,
  CardTitle as UiCardTitle,
} from '@/components/ui/card'
import SetupStatusCard from '@/views/dashboard/SetupStatusCard.vue'
import { useSetupPolling } from '@/views/dashboard/useSetupPolling'

const router = useRouter()
const authStore = useAuthStore()
const analysisStatus = ref<AnalysisStatus | null>(null)
const setupStatus = ref<SetupStatus | null>(null)
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
  const stageList = Object.values(analysisStatus.value.stages)
  const done = stageList.filter(stage => stage.status === 'done').length
  return { done, total: stageList.length }
})

async function fetchData() {
  const [analysisResult, setupResult] = await Promise.allSettled([
    analysisApi.getStatus(),
    setupApi.getStatus(),
  ])

  if (analysisResult.status === 'fulfilled') {
    analysisStatus.value = analysisResult.value.data.data
  } else {
    console.error('Analysis status request failed', analysisResult.reason)
  }

  if (setupResult.status === 'fulfilled' && setupResult.value.data.data) {
    setupStatus.value = setupResult.value.data.data
    setupPolling.sync(setupStatus.value)
  } else if (setupResult.status === 'rejected') {
    console.error('Setup status request failed', setupResult.reason)
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

function stageStatus(key: string): string {
  return analysisStatus.value?.stages?.[key]?.status || 'pending'
}

const { subscribe, onMessage } = useWebSocket()
const cleanups: (() => void)[] = []

onMounted(() => {
  void fetchData()
  subscribe('analysis:progress', 'analysis:ranking_ready')
  cleanups.push(onMessage('analysis:ranking_ready', () => void fetchData()))
  cleanups.push(onMessage('analysis:progress', () => {
    void analysisApi.getStatus().then((response) => {
      analysisStatus.value = response.data.data
    })
  }))
})

onUnmounted(() => {
  setupPolling.stop()
  cleanups.forEach(cleanup => cleanup())
})
</script>

<template>
  <div class="space-y-6">
    <h1 class="flex items-center gap-2 text-2xl font-bold">
      <Activity class="size-6 text-primary" />
      分析任务
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
            <div
              class="size-2 rounded-full"
              :class="{
                'bg-green-500': stageStatus(stage.key) === 'done',
                'bg-blue-500 animate-pulse': stageStatus(stage.key) === 'running',
                'bg-red-500': stageStatus(stage.key) === 'failed',
                'bg-muted': stageStatus(stage.key) === 'pending',
              }"
            />
            <span class="text-xs text-muted-foreground">{{ stage.label }}</span>
          </div>
        </div>
        <div v-if="analysisStatus.error" class="mt-2 flex items-center gap-1 text-sm text-red-500">
          <AlertCircle class="size-3" />
          {{ analysisStatus.error }}
        </div>
      </UiCardContent>
    </UiCard>
  </div>
</template>
