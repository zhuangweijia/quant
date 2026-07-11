<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { stockApi, type StockDetail, type ShapFactor } from '@/api/stock'
import VChart from 'vue-echarts'
import { registerECharts } from '@/utils/echarts'
import {
  Card as UiCard, CardContent as UiCardContent, CardHeader as UiCardHeader,
  CardTitle as UiCardTitle, CardDescription as UiCardDescription,
} from '@/components/ui/card'
import Badge from '@/components/ui/badge/Badge.vue'
import { ArrowLeft, TrendingUp, TrendingDown, Info } from 'lucide-vue-next'

registerECharts()

const route = useRoute()
const router = useRouter()
const symbol = route.params.symbol as string
const detail = ref<StockDetail | null>(null)
const loading = ref(true)
const scoreHistory = ref<{ date: string; score: number }[]>([])

onMounted(async () => {
  try {
    const [detailRes, histRes] = await Promise.all([
      stockApi.getDetail(symbol),
      stockApi.getScoreHistory(symbol, 30),
    ])
    detail.value = detailRes.data.data
    scoreHistory.value = histRes.data.data.history.map((h: any) => ({ date: h.date, score: h.score }))
  } catch (e) {
    console.error('Failed to load stock detail', e)
  } finally {
    loading.value = false
  }
})

const klineOption = computed(() => {
  const klines = detail.value?.klines || []
  if (!klines.length) return {}
  const dates = klines.map(k => k.date)
  const ohlc = klines.map(k => [k.open, k.close, k.low, k.high])
  const volumes = klines.map(k => k.volume)
  return {
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['K线', '成交量'], top: 0 },
    grid: [
      { left: 60, right: 30, top: 40, height: '55%' },
      { left: 60, right: 30, top: '72%', height: '20%' },
    ],
    xAxis: [
      { type: 'category', data: dates, scale: true, gridIndex: 0, boundaryGap: false },
      { type: 'category', data: dates, gridIndex: 1, show: false },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitArea: { show: true } },
      { gridIndex: 1, splitNumber: 2 },
    ],
    series: [
      {
        name: 'K线', type: 'candlestick', data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: {
          color: '#ef4444', color0: '#22c55e',
          borderColor: '#ef4444', borderColor0: '#22c55e',
        },
      },
      {
        name: '成交量', type: 'bar', data: volumes, xAxisIndex: 1, yAxisIndex: 1,
        itemStyle: { color: '#94a3b8' },
      },
    ],
  }
})

function scoreColor(s: number | null) {
  if (s === null) return ''
  if (s >= 0.7) return 'text-green-600 dark:text-green-400'
  if (s < 0.3) return 'text-red-600 dark:text-red-400'
  return 'text-yellow-600 dark:text-yellow-400'
}
</script>

<template>
  <div class="space-y-6">
    <Button variant="ghost" size="sm" @click="router.back()">
      <ArrowLeft class="size-4 mr-1" />返回
    </Button>

    <div v-if="loading" class="flex items-center justify-center min-h-[40vh]">
      <p class="text-muted-foreground">加载中...</p>
    </div>

    <template v-else-if="detail">
      <!-- Header -->
      <div class="flex items-start justify-between">
        <div>
          <h1 class="text-2xl font-bold">{{ detail.name || symbol }}</h1>
          <p class="text-sm text-muted-foreground font-mono">{{ symbol }} · {{ detail.industry || '未知行业' }}</p>
        </div>
        <div class="text-right">
          <div class="text-3xl font-bold" :class="scoreColor(detail.score)">
            {{ detail.score !== null ? detail.score.toFixed(3) : 'N/A' }}
          </div>
          <div class="flex items-center gap-2 justify-end mt-1">
            <Badge v-if="detail.label" :variant="detail.label === '强推' ? 'default' : detail.label === '回避' ? 'destructive' : 'outline'">
              {{ detail.label }}
            </Badge>
            <span v-if="detail.rank" class="text-sm text-muted-foreground">排名 #{{ detail.rank }}</span>
          </div>
        </div>
      </div>

      <!-- SHAP Explanation -->
      <div class="grid gap-6 lg:grid-cols-2" v-if="detail.explanation">
        <UiCard>
          <UiCardHeader>
            <UiCardTitle class="flex items-center gap-2">
              <TrendingUp class="size-4 text-green-500" />看好理由
            </UiCardTitle>
            <UiCardDescription>推动评分上升的主要因素</UiCardDescription>
          </UiCardHeader>
          <UiCardContent class="space-y-3">
            <div v-for="(f, i) in detail.explanation.positive" :key="i" class="flex items-start gap-3">
              <div class="mt-1 flex size-8 shrink-0 items-center justify-center rounded-full bg-green-100 text-green-700 dark:bg-green-950 dark:text-green-400">
                <TrendingUp class="size-4" />
              </div>
              <div class="flex-1">
                <p class="text-sm font-medium">{{ f.description }}</p>
                <p class="text-xs text-muted-foreground">{{ f.assessment }}</p>
              </div>
              <span class="text-sm font-mono text-green-600 dark:text-green-400">+{{ f.shap.toFixed(3) }}</span>
            </div>
            <div v-if="!detail.explanation.positive.length" class="text-sm text-muted-foreground py-4 text-center">暂无显著正向因素</div>
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader>
            <UiCardTitle class="flex items-center gap-2">
              <TrendingDown class="size-4 text-red-500" />风险提示
            </UiCardTitle>
            <UiCardDescription>拖累评分的主要因素</UiCardDescription>
          </UiCardHeader>
          <UiCardContent class="space-y-3">
            <div v-for="(f, i) in detail.explanation.negative" :key="i" class="flex items-start gap-3">
              <div class="mt-1 flex size-8 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-400">
                <TrendingDown class="size-4" />
              </div>
              <div class="flex-1">
                <p class="text-sm font-medium">{{ f.description }}</p>
                <p class="text-xs text-muted-foreground">{{ f.assessment }}</p>
              </div>
              <span class="text-sm font-mono text-red-600 dark:text-red-400">{{ f.shap.toFixed(3) }}</span>
            </div>
            <div v-if="!detail.explanation.negative.length" class="text-sm text-muted-foreground py-4 text-center">暂无显著风险因素</div>
          </UiCardContent>
        </UiCard>
      </div>

      <!-- K-line Chart -->
      <UiCard>
        <UiCardHeader>
          <UiCardTitle>K线图 (近60日)</UiCardTitle>
        </UiCardHeader>
        <UiCardContent>
          <v-chart v-if="detail.klines.length" :option="klineOption" style="height: 400px" autoresize />
          <p v-else class="text-sm text-muted-foreground py-8 text-center">暂无K线数据</p>
        </UiCardContent>
      </UiCard>

      <!-- Fundamentals -->
      <div class="grid gap-6 lg:grid-cols-2" v-if="detail.fundamentals || detail.northbound">
        <UiCard v-if="detail.fundamentals">
          <UiCardHeader>
            <UiCardTitle>基本面</UiCardTitle>
          </UiCardHeader>
          <UiCardContent>
            <div class="grid grid-cols-2 gap-4">
              <div v-for="(val, key) in detail.fundamentals" :key="key" class="space-y-0.5">
                <p class="text-xs text-muted-foreground">{{ key }}</p>
                <p class="text-lg font-semibold">{{ val !== null ? Number(val).toFixed(2) : 'N/A' }}</p>
              </div>
            </div>
          </UiCardContent>
        </UiCard>

        <UiCard v-if="detail.northbound">
          <UiCardHeader>
            <UiCardTitle>北向资金</UiCardTitle>
          </UiCardHeader>
          <UiCardContent>
            <div class="space-y-2">
              <div class="flex justify-between">
                <span class="text-sm text-muted-foreground">持股比例</span>
                <span class="font-semibold">{{ detail.northbound.holding_pct?.toFixed(2) }}%</span>
              </div>
            </div>
          </UiCardContent>
        </UiCard>
      </div>
    </template>

    <div v-else class="flex items-center justify-center min-h-[40vh]">
      <p class="text-muted-foreground">未找到该股票数据</p>
    </div>
  </div>
</template>
