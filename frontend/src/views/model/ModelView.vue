<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { modelApi, type ModelVersion, type BacktestResult } from '@/api/model'
import {
  Card as UiCard, CardContent as UiCardContent, CardHeader as UiCardHeader,
  CardTitle as UiCardTitle, CardDescription as UiCardDescription,
} from '@/components/ui/card'
import {
  Table as UiTable, TableHeader as UiTableHeader, TableBody as UiTableBody,
  TableRow as UiTableRow, TableHead as UiTableHead, TableCell as UiTableCell,
} from '@/components/ui/table'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import VChart from 'vue-echarts'
import { registerECharts } from '@/utils/echarts'
import { BrainCircuit, Play, CheckCircle2, FlaskConical, Loader2 } from 'lucide-vue-next'
import { toast } from 'vue-sonner'

registerECharts()

const versions = ref<ModelVersion[]>([])
const loading = ref(true)
const training = ref(false)
const backtesting = ref(false)
const backtestResult = ref<BacktestResult | null>(null)

async function fetchVersions() {
  loading.value = true
  try {
    const { data } = await modelApi.getVersions()
    versions.value = data.data.versions
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleTrain() {
  training.value = true
  try {
    const { data } = await modelApi.train()
    toast.success(`训练完成: ${data.data.version}, IC=${data.data.ic?.toFixed(4) || 'N/A'}`)
    await fetchVersions()
  } catch (e: any) {
    toast.error('训练失败: ' + (e?.response?.data?.detail || e.message))
  } finally {
    training.value = false
  }
}

async function handleActivate(version: string) {
  try {
    await modelApi.activate(version)
    toast.success(`已激活 ${version}`)
    await fetchVersions()
  } catch (e: any) {
    toast.error('激活失败: ' + (e?.response?.data?.detail || e.message))
  }
}

async function handleBacktest(version?: string) {
  backtesting.value = true
  try {
    const { data } = await modelApi.backtest({ model_version: version })
    backtestResult.value = data.data
    toast.success('回测完成')
  } catch (e: any) {
    toast.error('回测失败: ' + (e?.response?.data?.detail || e.message))
  } finally {
    backtesting.value = false
  }
}

const groupChartOption = computed(() => {
  if (!backtestResult.value) return {}
  const groups = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']
  const series = groups.map(q => {
    const data = backtestResult.value!.group_returns[q] || []
    let cum = 1
    return {
      name: q,
      type: 'line',
      data: data.map(d => { if (d.return !== null) cum *= (1 + d.return); return cum - 1 }),
      smooth: true,
    }
  })
  const dates = (backtestResult.value.group_returns['Q1'] || []).map(d => d.date)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: groups, top: 0 },
    grid: { left: 60, right: 30, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => (v * 100).toFixed(0) + '%' } },
    series,
  }
})

import { computed } from 'vue'
onMounted(() => fetchVersions())
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex min-w-0 items-center gap-3">
        <div class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <BrainCircuit class="size-5" />
        </div>
        <div class="min-w-0">
          <h1 class="text-2xl font-semibold tracking-normal">模型管理</h1>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <Button class="min-w-24" variant="outline" size="sm" :disabled="backtesting" @click="handleBacktest()">
          <FlaskConical class="size-4" :class="{ 'animate-spin': backtesting }" />
          <span>回测</span>
        </Button>
        <Button class="min-w-32" size="sm" :disabled="training" @click="handleTrain">
          <Loader2 v-if="training" class="size-4 animate-spin" />
          <Play v-else class="size-4" />
          <span>训练新模型</span>
        </Button>
      </div>
    </div>

    <!-- Version List -->
    <UiCard>
      <UiCardHeader>
        <UiCardTitle>模型版本</UiCardTitle>
        <UiCardDescription>管理训练好的 LightGBM 模型</UiCardDescription>
      </UiCardHeader>
      <UiCardContent>
        <UiTable>
          <UiTableHeader>
            <UiTableRow>
              <UiTableHead>版本</UiTableHead>
              <UiTableHead>训练时间</UiTableHead>
              <UiTableHead>IC</UiTableHead>
              <UiTableHead>准确率</UiTableHead>
              <UiTableHead>状态</UiTableHead>
              <UiTableHead class="w-32">操作</UiTableHead>
            </UiTableRow>
          </UiTableHeader>
          <UiTableBody>
            <UiTableRow v-for="v in versions" :key="v.version">
              <UiTableCell class="font-mono text-xs">{{ v.version }}</UiTableCell>
              <UiTableCell class="text-xs text-muted-foreground">{{ v.trained_at.slice(0, 16) }}</UiTableCell>
              <UiTableCell :class="v.ic !== null && Number(v.ic) > 0.03 ? 'text-green-600' : ''">
                {{ v.ic !== null ? Number(v.ic).toFixed(4) : 'N/A' }}
              </UiTableCell>
              <UiTableCell>{{ v.val_accuracy !== null ? (Number(v.val_accuracy) * 100).toFixed(1) + '%' : 'N/A' }}</UiTableCell>
              <UiTableCell>
                <Badge v-if="v.is_active" variant="default"><CheckCircle2 class="size-3 mr-1" />激活</Badge>
                <Badge v-else variant="outline">未激活</Badge>
              </UiTableCell>
              <UiTableCell>
                <Button v-if="!v.is_active" variant="ghost" size="sm" @click="handleActivate(v.version)">激活</Button>
                <Button variant="ghost" size="sm" @click="handleBacktest(v.version)">回测</Button>
              </UiTableCell>
            </UiTableRow>
            <UiTableRow v-if="!versions.length && !loading">
              <UiTableCell :colspan="6" class="h-24 text-center text-muted-foreground">暂无模型，请先训练</UiTableCell>
            </UiTableRow>
          </UiTableBody>
        </UiTable>
      </UiCardContent>
    </UiCard>

    <!-- Backtest Results -->
    <template v-if="backtestResult">
      <UiCard>
        <UiCardHeader>
          <UiCardTitle>回测结果 — {{ backtestResult.model_version }}</UiCardTitle>
          <UiCardDescription>{{ backtestResult.start_date }} ~ {{ backtestResult.end_date }}</UiCardDescription>
        </UiCardHeader>
        <UiCardContent>
          <!-- Metrics Table -->
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-5 mb-6">
            <div v-for="(metrics, group) in backtestResult.metrics" :key="group"
              class="rounded-lg border p-3" :class="{ 'border-green-500/50 bg-green-50/30': group === 'Q1', 'border-red-500/50 bg-red-50/30': group === 'Q5' }">
              <p class="text-xs text-muted-foreground mb-1">{{ group }}</p>
              <p class="text-lg font-bold">{{ group === 'ic' ? metrics.mean?.toFixed(4) : ((metrics.annual_return || 0) * 100).toFixed(1) + '%' }}</p>
              <p class="text-[10px] text-muted-foreground">{{ group === 'ic' ? 'IC均值' : '年化收益' }}</p>
            </div>
          </div>

          <!-- Group Returns Chart -->
          <v-chart :option="groupChartOption" style="height: 350px" autoresize />
        </UiCardContent>
      </UiCard>
    </template>

    <div v-if="!versions.length && !loading" class="space-y-4">
      <UiCard>
        <UiCardContent class="pt-6">
          <div class="flex items-start gap-3">
            <BrainCircuit class="size-5 text-muted-foreground mt-0.5" />
            <div class="space-y-1">
              <p class="text-sm font-medium">还没有训练模型</p>
              <p class="text-xs text-muted-foreground">确保已完成数据同步，然后点击「训练新模型」</p>
            </div>
          </div>
        </UiCardContent>
      </UiCard>
    </div>
  </div>
</template>
