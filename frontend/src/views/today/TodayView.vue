<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { AlertCircle, Clock3, RefreshCw, Sparkles } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

import { BasicPage } from '@/components/global-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useWebSocket } from '@/composables/useWebSocket'
import { useAdviceStore } from '@/stores/advice'
import { useAuthStore } from '@/stores/auth'
import { usePortfolioStore } from '@/stores/portfolio'
import type { AdviceItemResponse } from '@/types/advice'
import AdviceActionList from './AdviceActionList.vue'
import ExecutionDialog from './ExecutionDialog.vue'
import TodaySummaryCard from './TodaySummaryCard.vue'

const router = useRouter()
const adviceStore = useAdviceStore()
const authStore = useAuthStore()
const portfolioStore = usePortfolioStore()
const { subscribe, unsubscribe, onMessage } = useWebSocket()

const checkingSetup = ref(true)
const requestError = ref('')
const actionError = ref('')
const generating = ref(false)
const selectedItem = ref<AdviceItemResponse | null>(null)
const executionOpen = ref(false)
const setupConfirmed = ref(false)
let redirectedToSetup = false
let removeReadyHandler: (() => void) | undefined

const today = computed(() => adviceStore.today)
const advice = computed(() => today.value?.advice ?? null)
const stateError = computed(() => (
  today.value?.error_message || advice.value?.error_message || '建议生成失败，请稍后重试'
))

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'object' && error !== null && 'message' in error) return String(error.message)
  return String(error)
}

async function redirectToSetup() {
  if (redirectedToSetup) return
  redirectedToSetup = true
  await router.replace('/portfolio/setup')
}

async function initialize() {
  setupConfirmed.value = false
  checkingSetup.value = true
  requestError.value = ''
  try {
    const setupStatus = await portfolioStore.loadSetupStatus()
    if (!setupStatus.complete) {
      await redirectToSetup()
      return
    }
    setupConfirmed.value = true
    const [todayResponse] = await Promise.all([
      adviceStore.loadToday(),
      portfolioStore.loadPortfolio(),
    ])
    if (todayResponse.setup_required) await redirectToSetup()
  } catch (caught) {
    requestError.value = errorMessage(caught)
  } finally {
    checkingSetup.value = false
  }
}

async function generateAdvice(force: boolean) {
  if (generating.value) return
  generating.value = true
  actionError.value = ''
  try {
    await adviceStore.generate(force)
  } catch (caught) {
    actionError.value = errorMessage(caught)
  } finally {
    generating.value = false
  }
}

function openExecution(item: AdviceItemResponse) {
  selectedItem.value = item
  executionOpen.value = true
}

function handleReadyEvent(event: unknown) {
  if (!setupConfirmed.value) return
  if (typeof event !== 'object' || event === null || !('user_id' in event)) return
  if (typeof event.user_id !== 'string' || event.user_id !== authStore.user?.id) return
  void adviceStore.loadToday().catch(caught => { requestError.value = errorMessage(caught) })
}

onMounted(() => {
  subscribe('advice:ready')
  removeReadyHandler = onMessage('advice:ready', handleReadyEvent)
  void initialize()
})

onUnmounted(() => {
  removeReadyHandler?.()
  unsubscribe('advice:ready')
})
</script>

<template>
  <BasicPage title="今日" description="查看下一交易日组合动作，并记录真实执行结果。">
    <div
      v-if="checkingSetup"
      role="status"
      class="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground"
    >
      正在检查组合设置…
    </div>

    <div v-else-if="requestError" role="alert" class="rounded-lg border border-destructive/40 bg-destructive/5 p-6">
      <p class="flex items-center gap-2 font-medium text-destructive"><AlertCircle class="size-4" />加载今日建议失败</p>
      <p class="mt-2 text-sm text-destructive">{{ requestError }}</p>
      <Button data-testid="today-retry" class="mt-4" type="button" variant="outline" @click="initialize">
        <RefreshCw class="size-4" />重试
      </Button>
    </div>

    <template v-else-if="today">
      <div v-if="actionError" role="alert" class="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
        {{ actionError }}
      </div>

      <Card v-if="today.state === 'not_generated'">
        <CardHeader><CardTitle>尚未生成今日建议</CardTitle><CardDescription>将使用最新排名、当前持仓与生效投资画像生成首份建议。</CardDescription></CardHeader>
        <CardContent><Button data-testid="generate-advice" type="button" :loading="generating" :disabled="generating" @click="generateAdvice(false)"><Sparkles class="size-4" />生成首份建议</Button></CardContent>
      </Card>

      <Card v-else-if="today.state === 'generating'">
        <CardHeader><CardTitle class="flex items-center gap-2"><Clock3 class="size-4" />建议生成中</CardTitle><CardDescription>系统正在结合排名、组合约束和最新持仓计算动作。完成后此页会通过实时事件刷新。</CardDescription></CardHeader>
        <CardContent class="text-sm text-muted-foreground">请稍候；生成中不会显示空动作列表。</CardContent>
      </Card>

      <Card v-else-if="today.state === 'failed'">
        <CardHeader><CardTitle>建议生成失败</CardTitle><CardDescription>{{ stateError }}</CardDescription></CardHeader>
        <CardContent><Button data-testid="retry-generation" type="button" :loading="generating" :disabled="generating" @click="generateAdvice(true)"><RefreshCw class="size-4" />重试生成</Button></CardContent>
      </Card>

      <template v-else-if="advice">
        <div v-if="today.state === 'handled'" class="rounded-lg border bg-muted/30 p-4 text-sm">
          <p class="font-medium">今日建议已处理</p><p class="mt-1 text-muted-foreground">仍可查看建议，并在没有后续持仓事件时更正执行记录。</p>
        </div>
        <div v-if="today.state === 'partially_handled'" class="rounded-lg border bg-muted/30 p-4 text-sm">
          部分动作已经处理，其余动作仍待记录。
        </div>
        <div v-if="today.state === 'expired'" class="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 text-sm">
          <p class="font-medium">建议已过期</p><p class="mt-1 text-muted-foreground">建议内容仍可查看。记录实际成交时，服务端会要求单独确认过期或超价带执行。</p>
        </div>
        <TodaySummaryCard :advice="advice" />
        <AdviceActionList v-if="advice.items.length" :items="advice.items" @execute="openExecution" />
        <div v-else class="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">本次建议没有需要展示的股票动作。</div>
      </template>
    </template>

    <ExecutionDialog
      v-if="selectedItem"
      v-model:open="executionOpen"
      :item="selectedItem"
      :existing-execution="selectedItem.execution"
      @success="selectedItem = null"
    />
  </BasicPage>
</template>
