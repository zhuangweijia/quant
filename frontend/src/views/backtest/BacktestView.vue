<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { toast } from 'vue-sonner'
import { strategyApi } from '@/api/strategy'
import { useBacktestStore } from '@/stores/backtest'
import { formatPercent, formatDate } from '@/utils/format'
import { BasicPage } from '@/components/global-layout'
import { DataTable } from '@/components/data-table'
import type { ColumnDef } from '@tanstack/vue-table'
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
import {
  Select as UiSelect,
  SelectContent as UiSelectContent,
  SelectItem as UiSelectItem,
  SelectTrigger as UiSelectTrigger,
  SelectValue as UiSelectValue,
} from '@/components/ui/select'
import {
  Dialog as UiDialog,
  DialogContent as UiDialogContent,
  DialogHeader as UiDialogHeader,
  DialogTitle as UiDialogTitle,
  DialogDescription as UiDialogDescription,
} from '@/components/ui/dialog'
import {
  AlertDialog as UiAlertDialog,
  AlertDialogAction as UiAlertDialogAction,
  AlertDialogCancel as UiAlertDialogCancel,
  AlertDialogContent as UiAlertDialogContent,
  AlertDialogDescription as UiAlertDialogDescription,
  AlertDialogFooter as UiAlertDialogFooter,
  AlertDialogHeader as UiAlertDialogHeader,
  AlertDialogTitle as UiAlertDialogTitle,
} from '@/components/ui/alert-dialog'
import UiProgress from '@/components/ui/progress/Progress.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { Play } from 'lucide-vue-next'

use([TitleComponent, TooltipComponent, GridComponent, DataZoomComponent, LineChart, BarChart, CanvasRenderer])

const backtestStore = useBacktestStore()
const strategies = ref<any[]>([])
const runForm = ref({
  strategy_id: '',
  symbol: 'BTCUSDT',
  market: 'crypto',
  timeframe: '1d',
  start_date: '',
  end_date: '',
  initial_capital: 100000,
})

const detailDialog = ref(false)
const detailData = ref<any>(null)
const equityChartOption = ref<any>({})
const drawdownChartOption = ref<any>({})
const deleteTarget = ref<string | null>(null)

const currentPage = ref(1)
const pageSize = 20
const loading = ref(false)

const resultColumns: ColumnDef<any>[] = [
  {
    accessorKey: 'strategy_name',
    header: '策略',
    cell: ({ row }) => h('span', { class: 'font-medium' }, row.original.strategy_name || '—'),
  },
  { accessorKey: 'symbol', header: '标的' },
  { accessorKey: 'timeframe', header: '周期' },
  {
    accessorKey: 'total_return',
    header: '总收益',
    cell: ({ row }) => {
      const v = Number(row.getValue('total_return'))
      return h('span', { class: v > 0 ? 'text-green-600 dark:text-green-400' : v < 0 ? 'text-red-600 dark:text-red-400' : '' }, formatPercent(v / 100))
    },
  },
  {
    accessorKey: 'sharpe_ratio',
    header: '夏普',
    cell: ({ row }) => Number(row.getValue('sharpe_ratio')).toFixed(2),
  },
  {
    accessorKey: 'max_drawdown',
    header: '最大回撤',
    cell: ({ row }) => h('span', { class: 'text-red-600 dark:text-red-400' }, Number(row.getValue('max_drawdown')).toFixed(2) + '%'),
  },
  { accessorKey: 'created_at', header: '时间', cell: ({ row }) => formatDate(row.getValue('created_at')) },
  {
    id: 'actions',
    header: '操作',
    cell: ({ row }) => h('div', { class: 'flex gap-1' }, [
      h(Button, { size: 'sm', variant: 'ghost', onClick: () => handleViewResult(row.original) }, () => '详情'),
      h(Button, { size: 'sm', variant: 'ghost', class: 'text-destructive', onClick: () => { deleteTarget.value = row.original.id } }, () => '删除'),
    ]),
  },
]

async function loadStrategies() {
  const res: any = await strategyApi.list()
  strategies.value = res.data?.items || []
}

async function handleRun() {
  if (!runForm.value.strategy_id) { toast.error('请选择策略'); return }
  if (!runForm.value.start_date || !runForm.value.end_date) { toast.error('请选择日期范围'); return }
  try {
    const result = await backtestStore.runBacktest(runForm.value as any)
    toast.success('回测完成')
    if (result) showDetail(result)
  } catch (e: any) { toast.error(e.message || '回测失败') }
}

function showDetail(row: any) {
  detailData.value = row
  if (row.equity_curve?.data) {
    const points = row.equity_curve.data
    equityChartOption.value = {
      tooltip: { trigger: 'axis' },
      grid: { left: 70, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: points.map((p: any) => p.timestamp?.substring(0, 10)), boundaryGap: false },
      yAxis: { type: 'value', scale: true },
      dataZoom: [{ type: 'inside' }],
      series: [{
        type: 'line', data: points.map((p: any) => p.equity), smooth: true,
        lineStyle: { width: 2 },
        areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(59,130,246,0.25)' }, { offset: 1, color: 'rgba(59,130,246,0.02)' }] } },
      }],
    }
  }
  if (row.drawdown_curve?.data) {
    const points = row.drawdown_curve.data
    drawdownChartOption.value = {
      tooltip: { trigger: 'axis' },
      grid: { left: 70, right: 20, top: 20, bottom: 30 },
      xAxis: { type: 'category', data: points.map((p: any) => p.timestamp?.substring(0, 10)) },
      yAxis: { type: 'value' },
      series: [{ type: 'bar', data: points.map((p: any) => p.drawdown), itemStyle: { color: '#ef4444' } }],
    }
  }
  detailDialog.value = true
}

async function handleViewResult(row: any) {
  try {
    await backtestStore.fetchResult(row.id)
    showDetail(backtestStore.currentResult)
  } catch (e: any) { toast.error(e.message) }
}

async function handleDelete() {
  if (!deleteTarget.value) return
  await backtestStore.deleteResult(deleteTarget.value)
  toast.success('已删除')
  deleteTarget.value = null
}

async function handlePageChange(page: number) {
  currentPage.value = page
  loading.value = true
  try { await backtestStore.fetchResults({ page: currentPage.value, size: pageSize }) }
  finally { loading.value = false }
}

function formatMetric(val: any) {
  if (val === null || val === undefined) return '-'
  return Number(val).toFixed(2)
}

onMounted(() => {
  loadStrategies()
  loading.value = true
  backtestStore.fetchResults({ page: 1, size: pageSize }).finally(() => { loading.value = false })
})
</script>

<template>
  <BasicPage title="回测" description="运行策略回测并分析结果">
    <div class="space-y-6">
      <UiCard>
        <UiCardHeader>
          <UiCardTitle>运行回测</UiCardTitle>
          <UiCardDescription>选择策略和参数进行历史数据模拟</UiCardDescription>
        </UiCardHeader>
        <UiCardContent>
          <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div class="space-y-2">
              <Label>策略</Label>
              <UiSelect v-model="runForm.strategy_id">
                <UiSelectTrigger><UiSelectValue placeholder="选择策略" /></UiSelectTrigger>
                <UiSelectContent>
                  <UiSelectItem v-for="s in strategies" :key="s.id" :value="s.id">{{ s.name }}</UiSelectItem>
                </UiSelectContent>
              </UiSelect>
            </div>
            <div class="space-y-2">
              <Label>标的</Label>
              <Input v-model="runForm.symbol" placeholder="如 BTCUSDT" />
            </div>
            <div class="space-y-2">
              <Label>开始日期</Label>
              <Input v-model="runForm.start_date" type="date" />
            </div>
            <div class="space-y-2">
              <Label>结束日期</Label>
              <Input v-model="runForm.end_date" type="date" />
            </div>
          </div>
          <div v-if="backtestStore.running" class="mt-4">
            <UiProgress :model-value="100" class="animate-pulse" />
            <p class="text-sm text-muted-foreground mt-2">回测运行中...</p>
          </div>
          <Button v-else class="mt-4" @click="handleRun">
            <Play class="mr-2 size-4" />
            运行回测
          </Button>
        </UiCardContent>
      </UiCard>

      <DataTable
        :columns="resultColumns"
        :data="backtestStore.results"
        :total="backtestStore.total"
        :page-size="pageSize"
        :loading="loading"
        @page-change="handlePageChange"
      />

      <UiDialog v-model:open="detailDialog">
        <UiDialogContent class="max-w-3xl max-h-[85vh] overflow-y-auto">
          <UiDialogHeader>
            <UiDialogTitle>回测结果详情</UiDialogTitle>
            <UiDialogDescription v-if="detailData">{{ detailData.strategy_name }} - {{ detailData.symbol }}</UiDialogDescription>
          </UiDialogHeader>
          <div v-if="detailData" class="space-y-6">
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div class="space-y-1">
                <p class="text-xs text-muted-foreground">总收益</p>
                <p class="text-lg font-bold" :class="Number(detailData.total_return) > 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'">
                  {{ formatPercent(detailData.total_return / 100) }}
                </p>
              </div>
              <div class="space-y-1">
                <p class="text-xs text-muted-foreground">夏普比率</p>
                <p class="text-lg font-bold">{{ formatMetric(detailData.sharpe_ratio) }}</p>
              </div>
              <div class="space-y-1">
                <p class="text-xs text-muted-foreground">最大回撤</p>
                <p class="text-lg font-bold text-red-600 dark:text-red-400">{{ formatMetric(detailData.max_drawdown) }}%</p>
              </div>
              <div class="space-y-1">
                <p class="text-xs text-muted-foreground">胜率</p>
                <p class="text-lg font-bold">{{ formatMetric(detailData.win_rate) }}%</p>
              </div>
            </div>

            <div v-if="equityChartOption.series?.length">
              <h4 class="text-sm font-medium mb-3">权益曲线</h4>
              <VChart :option="equityChartOption" style="height: 280px" autoresize />
            </div>
            <div v-if="drawdownChartOption.series?.length">
              <h4 class="text-sm font-medium mb-3">回撤曲线</h4>
              <VChart :option="drawdownChartOption" style="height: 200px" autoresize />
            </div>
          </div>
        </UiDialogContent>
      </UiDialog>

      <UiAlertDialog :open="!!deleteTarget" @update:open="!$event && (deleteTarget = null)">
        <UiAlertDialogContent>
          <UiAlertDialogHeader>
            <UiAlertDialogTitle>确认删除</UiAlertDialogTitle>
            <UiAlertDialogDescription>确定删除该回测结果？此操作不可撤销。</UiAlertDialogDescription>
          </UiAlertDialogHeader>
          <UiAlertDialogFooter>
            <UiAlertDialogCancel>取消</UiAlertDialogCancel>
            <UiAlertDialogAction @click="handleDelete">删除</UiAlertDialogAction>
          </UiAlertDialogFooter>
        </UiAlertDialogContent>
      </UiAlertDialog>
    </div>
  </BasicPage>
</template>
