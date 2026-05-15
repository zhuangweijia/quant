<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useMarketStore } from "@/stores/market";
import { MARKET_LABELS, TIMEFRAME_OPTIONS } from "@/utils/constants";
import { formatNumber, formatPercent, formatDate, toNum } from "@/utils/format";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { CandlestickChart, BarChart, LineChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
} from "echarts/components";

use([CanvasRenderer, CandlestickChart, BarChart, LineChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent, DataZoomComponent]);

const store = useMarketStore();
const keyword = ref("");
const selectedTimeframe = ref("1d");
const loading = ref(false);
const chartLoading = ref(false);

let searchTimer: ReturnType<typeof setTimeout> | null = null;

onMounted(() => {
  store.initWatchlist();
});

function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer);
  if (!keyword.value.trim()) {
    store.searchResults = [];
    return;
  }
  searchTimer = setTimeout(async () => {
    loading.value = true;
    try {
      await store.searchSymbols(keyword.value.trim());
    } finally {
      loading.value = false;
    }
  }, 300);
}

async function selectSymbol(sym: any) {
  store.selectSymbol(sym);
  await loadChart();
}

async function loadChart() {
  if (!store.currentSymbol) return;
  chartLoading.value = true;
  try {
    await store.fetchKlines({
      symbol: store.currentSymbol.symbol,
      market: store.currentSymbol.market,
      timeframe: selectedTimeframe.value,
      limit: 200,
    });
    await store.fetchTick({
      symbol: store.currentSymbol.symbol,
      market: store.currentSymbol.market,
    });
  } finally {
    chartLoading.value = false;
  }
}

watch(selectedTimeframe, () => {
  if (store.currentSymbol) loadChart();
});

const klineOption = computed(() => {
  if (!store.klines.length) return null;
  const dates = store.klines.map((k) => k.timestamp);
  const ohlc = store.klines.map((k) => [Number(k.open), Number(k.close), Number(k.low), Number(k.high)]);
  const volumes = store.klines.map((k) => Number(k.volume));

  return {
    tooltip: { trigger: "axis" as const, axisPointer: { type: "cross" as const } },
    legend: { data: ["K线", "成交量"], top: 0 },
    grid: [
      { left: 60, right: 20, top: 30, height: "55%" },
      { left: 60, right: 20, top: "72%", height: "20%" },
    ],
    xAxis: [
      { type: "category" as const, data: dates, gridIndex: 0, axisLabel: { show: false } },
      { type: "category" as const, data: dates, gridIndex: 1 },
    ],
    yAxis: [
      { scale: true, gridIndex: 0, splitLine: { lineStyle: { type: "dashed" as const } } },
      { scale: true, gridIndex: 1, splitNumber: 2 },
    ],
    dataZoom: [
      { type: "inside" as const, xAxisIndex: [0, 1], start: 60, end: 100 },
    ],
    series: [
      {
        name: "K线",
        type: "candlestick" as const,
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: "var(--qp-up)",
          color0: "var(--qp-down)",
          borderColor: "var(--qp-up)",
          borderColor0: "var(--qp-down)",
        },
      },
      {
        name: "成交量",
        type: "bar" as const,
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: { color: "#409EFF", opacity: 0.6 },
      },
    ],
  };
});
</script>

<template>
  <div class="market-view">
    <el-card shadow="hover" style="margin-bottom: 20px">
      <template #header>
        <div class="card-header">
          <span>行情监控</span>
          <el-select v-model="selectedTimeframe" size="small" style="width: 120px">
            <el-option
              v-for="tf in TIMEFRAME_OPTIONS"
              :key="tf.value"
              :label="tf.label"
              :value="tf.value"
            />
          </el-select>
        </div>
      </template>

      <el-input
        v-model="keyword"
        placeholder="搜索标的代码或名称..."
        size="large"
        clearable
        prefix-icon="Search"
        @input="onSearchInput"
        style="margin-bottom: 16px"
      />

      <div v-if="loading" style="text-align: center; padding: 20px">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      </div>
      <div v-else-if="store.searchResults.length" class="search-results">
        <el-card
          v-for="sym in store.searchResults"
          :key="sym.symbol + sym.market"
          shadow="hover"
          class="symbol-card"
          :class="{ active: store.currentSymbol?.symbol === sym.symbol && store.currentSymbol?.market === sym.market }"
          @click="selectSymbol(sym)"
        >
          <div class="symbol-name">{{ sym.symbol }}</div>
          <div class="symbol-info">{{ sym.name }}</div>
          <el-tag size="small" type="info">{{ MARKET_LABELS[sym.market] || sym.market }}</el-tag>
        </el-card>
      </div>
    </el-card>

    <el-row :gutter="20">
      <el-col :xs="24" :md="18">
        <el-card shadow="hover" v-loading="chartLoading">
          <template #header>
            <span>{{ store.currentSymbol ? `${store.currentSymbol.symbol} - K线图` : 'K线图' }}</span>
          </template>
          <div class="chart-area">
            <VChart v-if="klineOption" :option="klineOption" autoresize style="height: 400px; width: 100%" />
            <el-empty v-else description="选择标的查看K线" />
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="6">
        <el-card shadow="hover">
          <template #header><span>自选列表</span></template>
          <div v-if="store.watchlist.length">
            <div
              v-for="sym in store.watchlist"
              :key="sym.symbol + sym.market"
              class="watchlist-item"
              :class="{ active: store.currentSymbol?.symbol === sym.symbol }"
              @click="selectSymbol(sym)"
            >
              <div>
                <div class="watchlist-symbol">{{ sym.symbol }}</div>
                <div class="watchlist-info">{{ sym.name }}</div>
              </div>
              <el-button size="small" text type="danger" @click.stop="store.removeFromWatchlist(sym.symbol, sym.market)">
                <el-icon><Close /></el-icon>
              </el-button>
            </div>
          </div>
          <el-empty v-else description="搜索并添加自选" :image-size="60" />
        </el-card>

        <el-card shadow="hover" style="margin-top: 16px" v-if="store.tickData">
          <template #header><span>实时行情</span></template>
          <div class="tick-info">
            <div class="tick-price">
              {{ formatNumber(store.tickData.price, toNum(store.tickData.price) < 1 ? 6 : 2) }}
            </div>
            <div class="tick-time" style="font-size: 12px; color: var(--qp-text-secondary)">
              {{ store.tickData.timestamp ? formatDate(store.tickData.timestamp) : "" }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-results {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.symbol-card {
  width: 180px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--qp-primary);
  }

  &.active {
    border-color: var(--qp-primary);
    box-shadow: 0 0 0 1px var(--qp-primary);
  }

  :deep(.el-card__body) {
    padding: 12px;
  }

  .symbol-name {
    font-weight: 600;
    font-size: 16px;
    margin-bottom: 4px;
  }

  .symbol-info {
    font-size: 12px;
    color: var(--qp-text-secondary);
    margin-bottom: 6px;
  }
}

.chart-area {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.watchlist-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  cursor: pointer;
  border-bottom: 1px solid var(--qp-border-color);

  &:last-child {
    border-bottom: none;
  }

  &:hover,
  &.active {
    background: var(--qp-bg-page);
  }

  .watchlist-symbol {
    font-weight: 500;
  }

  .watchlist-info {
    font-size: 12px;
    color: var(--qp-text-secondary);
  }
}

.tick-info {
  text-align: center;

  .tick-price {
    font-size: 28px;
    font-weight: 600;
    margin-bottom: 4px;
  }
}
</style>
