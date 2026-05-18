<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { toast } from 'vue-sonner'
import { useMarketStore } from '@/stores/market'
import { MARKET_LABELS, TIMEFRAME_OPTIONS } from '@/utils/constants'
import { formatNumber, formatDate, toNum } from '@/utils/format'
import { BasicPage } from '@/components/global-layout'
import Button from '@/components/ui/button/Button.vue'
import Badge from '@/components/ui/badge/Badge.vue'
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
  ScrollArea as UiScrollArea,
} from '@/components/ui/scroll-area'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart, BarChart } from 'echarts/charts'
import {
  TitleComponent, TooltipComponent, LegendComponent, GridComponent, DataZoomComponent,
} from 'echarts/components'
import { X, Search } from 'lucide-vue-next'

use([CanvasRenderer, CandlestickChart, BarChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, DataZoomComponent])

const store = useMarketStore()
const keyword = ref('')
const selectedTimeframe = ref('1d')
const loading = ref(false)
const chartLoading = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | null = null

onMounted(() => { store.initWatchlist() })

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  if (!keyword.value.trim()) {
    store.searchResults = []
    return
  }
  searchTimer = setTimeout(async () => {
    loading.value = true
    try { await store.searchSymbols(keyword.value.trim()) }
    finally { loading.value = false }
  }, 300)
}

async function selectSymbol(sym: any) {
  store.selectSymbol(sym)
  await loadChart()
}

async function loadChart() {
  if (!store.currentSymbol) return
  chartLoading.value = true
  try {
    await store.fetchKlines({
      symbol: store.currentSymbol.symbol,
      market: store.currentSymbol.market,
      timeframe: selectedTimeframe.value,
      limit: 200,
    })
    await store.fetchTick({ symbol: store.currentSymbol.symbol, market: store.currentSymbol.market })
  } finally { chartLoading.value = false }
}

watch(selectedTimeframe, () => { if (store.currentSymbol) loadChart() })

const klineOption = computed(() => {
  if (!store.klines.length) return null
  const dates = store.klines.map((k) => k.timestamp)
  const ohlc = store.klines.map((k) => [Number(k.open), Number(k.close), Number(k.low), Number(k.high)])
  const volumes = store.klines.map((k) => Number(k.volume))
  return {
    tooltip: { trigger: 'axis' as const, axisPointer: { type: 'cross' as const } },
    legend: { data: ['K线', '成交量'], top: 0 },
    grid: [
      { left: 60, right: 20, top: 30, height: '55%' },
      { left: 60, right: 20, top: '72%', height: '20%' },
    ],
    xAxis: [
      { type: 'category' as const, data: dates, gridIndex: 0, axisLabel: { show: false } },
      { type: 'category' as const, data: dates, gridIndex: 1 },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitLine: { lineStyle: { type: 'dashed' as const } } },
      { scale: true, gridIndex: 1, splitNumber: 2 },
    ],
    dataZoom: [{ type: 'inside' as const, xAxisIndex: [0, 1], start: 60, end: 100 }],
    series: [
      {
        name: 'K线', type: 'candlestick' as const, data: ohlc, xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: { color: '#ef4444', color0: '#22c55e', borderColor: '#ef4444', borderColor0: '#22c55e' },
      },
      {
        name: '成交量', type: 'bar' as const, data: volumes, xAxisIndex: 1, yAxisIndex: 1,
        itemStyle: { color: '#3b82f6', opacity: 0.6 },
      },
    ],
  }
})
</script>

<template>
  <BasicPage title="行情" description="实时行情监控与K线分析">
    <template #actions>
      <UiSelect v-model="selectedTimeframe">
        <UiSelectTrigger class="w-32">
          <UiSelectValue placeholder="时间周期" />
        </UiSelectTrigger>
        <UiSelectContent>
          <UiSelectItem v-for="tf in TIMEFRAME_OPTIONS" :key="tf.value" :value="tf.value">
            {{ tf.label }}
          </UiSelectItem>
        </UiSelectContent>
      </UiSelect>
    </template>

    <div class="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div class="space-y-6">
        <UiCard>
          <UiCardHeader class="pb-3">
            <UiCardTitle class="text-base">搜索标的</UiCardTitle>
          </UiCardHeader>
          <UiCardContent>
            <div class="relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                v-model="keyword"
                placeholder="输入标的代码或名称..."
                class="pl-9"
                @input="onSearchInput"
              />
            </div>
            <div v-if="store.searchResults.length" class="flex flex-wrap gap-2 mt-4">
              <button
                v-for="sym in store.searchResults"
                :key="sym.symbol + sym.market"
                class="flex items-center gap-2 rounded-md border px-3 py-2 text-sm hover:bg-accent transition-colors"
                :class="store.currentSymbol?.symbol === sym.symbol && store.currentSymbol?.market === sym.market ? 'border-primary bg-accent' : ''"
                @click="selectSymbol(sym)"
              >
                <span class="font-medium">{{ sym.symbol }}</span>
                <span class="text-muted-foreground text-xs">{{ sym.name }}</span>
                <Badge variant="secondary" class="text-[10px] px-1.5">{{ MARKET_LABELS[sym.market] || sym.market }}</Badge>
              </button>
            </div>
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader>
            <UiCardTitle>{{ store.currentSymbol ? `${store.currentSymbol.symbol} - K线图` : 'K线图' }}</UiCardTitle>
          </UiCardHeader>
          <UiCardContent>
            <div v-if="chartLoading" class="flex items-center justify-center h-[420px]">
              <div class="size-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
            <VChart v-else-if="klineOption" :option="klineOption" autoresize style="height: 420px; width: 100%" />
            <div v-else class="flex items-center justify-center h-[420px] text-muted-foreground">
              选择标的查看K线
            </div>
          </UiCardContent>
        </UiCard>
      </div>

      <div class="space-y-6">
        <UiCard>
          <UiCardHeader>
            <UiCardTitle class="text-base">自选列表</UiCardTitle>
          </UiCardHeader>
          <UiCardContent class="p-0">
            <UiScrollArea class="h-[300px]">
              <div v-if="store.watchlist.length" class="divide-y">
                <button
                  v-for="sym in store.watchlist"
                  :key="sym.symbol + sym.market"
                  class="flex items-center justify-between w-full px-4 py-3 text-left hover:bg-accent/50 transition-colors"
                  :class="store.currentSymbol?.symbol === sym.symbol ? 'bg-accent' : ''"
                  @click="selectSymbol(sym)"
                >
                  <div>
                    <div class="text-sm font-medium">{{ sym.symbol }}</div>
                    <div class="text-xs text-muted-foreground">{{ sym.name }}</div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    class="size-7 shrink-0"
                    @click.stop="store.removeFromWatchlist(sym.symbol, sym.market)"
                  >
                    <X class="size-3" />
                  </Button>
                </button>
              </div>
              <div v-else class="py-8 text-center text-sm text-muted-foreground">
                搜索并添加自选
              </div>
            </UiScrollArea>
          </UiCardContent>
        </UiCard>

        <UiCard v-if="store.tickData">
          <UiCardHeader>
            <UiCardTitle class="text-base">实时行情</UiCardTitle>
          </UiCardHeader>
          <UiCardContent>
            <div class="text-center">
              <div class="text-3xl font-bold">
                {{ formatNumber(store.tickData.price, toNum(store.tickData.price) < 1 ? 6 : 2) }}
              </div>
              <div class="text-xs text-muted-foreground mt-2">
                {{ store.tickData.timestamp ? formatDate(store.tickData.timestamp) : '' }}
              </div>
            </div>
          </UiCardContent>
        </UiCard>
      </div>
    </div>
  </BasicPage>
</template>
