<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { dashboardApi } from "@/api/dashboard";
import { tradeApi } from "@/api/trade";
import { strategyApi } from "@/api/strategy";
import { formatCurrency, formatPercent, formatCompactNumber, formatNumber, toNum } from "@/utils/format";
import { MARKET_LABELS, SIDE_LABELS, STATUS_LABELS } from "@/utils/constants";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, PieChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from "echarts/components";

use([CanvasRenderer, LineChart, PieChart, TitleComponent, TooltipComponent, LegendComponent, GridComponent]);

import type { DashboardOverview, EquityCurvePoint, StrategyRankItem } from "@/types/dashboard";
import type { Order, Position } from "@/types/trade";

const loading = ref(false);
const overview = ref<DashboardOverview | null>(null);
const equityCurve = ref<EquityCurvePoint[]>([]);
const strategyRanking = ref<StrategyRankItem[]>([]);
const recentOrders = ref<Order[]>([]);
const positions = ref<Position[]>([]);

const stats = computed(() => {
  if (!overview.value) {
    return [
      { label: "总资产", value: "-", sub: "", color: "" },
      { label: "日盈亏", value: "-", sub: "", color: "" },
      { label: "总盈亏", value: "-", sub: "", color: "" },
      { label: "运行策略", value: "0", sub: "/ 0", color: "" },
    ];
  }
  const o = overview.value;
  const equity = Number(o.total_equity) || 0;
  const dailyPnl = Number(o.daily_pnl) || 0;
  const totalPnl = Number(o.total_pnl) || 0;
  return [
    {
      label: "总资产",
      value: formatCurrency(equity),
      sub: "",
      color: "",
    },
    {
      label: "日盈亏",
      value: formatCurrency(dailyPnl),
      sub: formatPercent(o.daily_pnl_pct ? Number(o.daily_pnl_pct) : 0),
      color: dailyPnl >= 0 ? "var(--qp-up)" : "var(--qp-down)",
    },
    {
      label: "总盈亏",
      value: formatCurrency(totalPnl),
      sub: formatPercent(o.total_pnl_pct ? Number(o.total_pnl_pct) : 0),
      color: totalPnl >= 0 ? "var(--qp-up)" : "var(--qp-down)",
    },
    {
      label: "运行策略",
      value: String(o.running_strategies),
      sub: `/ ${o.total_strategies}`,
      color: "",
    },
  ];
});

const equityOption = computed(() => {
  if (!equityCurve.value.length) return null;
  return {
    tooltip: { trigger: "axis" as const },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: "category" as const,
      data: equityCurve.value.map((p) => p.date),
      axisLabel: { fontSize: 11 },
    },
    yAxis: {
      type: "value" as const,
      axisLabel: { fontSize: 11, formatter: (v: number) => formatCompactNumber(v) },
    },
    series: [
      {
        type: "line" as const,
        data: equityCurve.value.map((p) => p.equity),
        smooth: true,
        lineStyle: { width: 2, color: "#409EFF" },
        areaStyle: {
          color: {
            type: "linear" as const,
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(64,158,255,0.3)" },
              { offset: 1, color: "rgba(64,158,255,0.05)" },
            ],
          },
        },
      },
    ],
  };
});

const pieOption = computed(() => {
  if (!positions.value.length) return null;
  const data = positions.value.map((p) => ({
    name: `${p.symbol} (${MARKET_LABELS[p.market] || p.market})`,
    value: toNum(p.qty) * toNum(p.avg_price),
  }));
  return {
    tooltip: { trigger: "item" as const },
    legend: { bottom: 0, type: "scroll" as const },
    series: [
      {
        type: "pie" as const,
        radius: ["40%", "70%"],
        data,
        label: { show: false },
      },
    ],
  };
});

onMounted(async () => {
  loading.value = true;
  try {
    const [overviewRes, equityRes, rankRes] = await Promise.allSettled([
      dashboardApi.getOverview(),
      dashboardApi.getEquityCurve(),
      dashboardApi.getStrategyRanking(),
    ]);
    if (overviewRes.status === "fulfilled") overview.value = (overviewRes.value as any).data;
    if (equityRes.status === "fulfilled") equityCurve.value = (equityRes.value as any).data || [];
    if (rankRes.status === "fulfilled") strategyRanking.value = (rankRes.value as any).data || [];

    const [ordersRes, positionsRes] = await Promise.allSettled([
      tradeApi.getOrders({ page: 1, page_size: 10 }),
      tradeApi.getPositions(),
    ]);
    if (ordersRes.status === "fulfilled") recentOrders.value = ((ordersRes.value as any).data?.items) || [];
    if (positionsRes.status === "fulfilled") positions.value = ((positionsRes.value as any).data) || [];
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="dashboard-view" v-loading="loading">
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="stat in stats" :key="stat.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-value" :style="{ color: stat.color || 'var(--qp-text-primary)' }">
            {{ stat.value }}
            <small>{{ stat.sub }}</small>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><span>权益曲线</span></template>
          <div class="chart-area">
            <VChart v-if="equityOption" :option="equityOption" autoresize style="height: 300px; width: 100%" />
            <el-empty v-else description="暂无数据" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>持仓分布</span></template>
          <div class="chart-area">
            <VChart v-if="pieOption" :option="pieOption" autoresize style="height: 300px; width: 100%" />
            <el-empty v-else description="暂无持仓" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>策略表现</span></template>
          <el-table v-if="strategyRanking.length" :data="strategyRanking" stripe size="small">
            <el-table-column prop="strategy_name" label="策略" min-width="120" />
            <el-table-column label="收益率" width="100">
              <template #default="{ row }">
                <span :style="{ color: row.total_return >= 0 ? 'var(--qp-up)' : 'var(--qp-down)' }">
                  {{ formatPercent(row.total_return) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="夏普比率" width="100">
              <template #default="{ row }">{{ formatNumber(row.sharpe_ratio) }}</template>
            </el-table-column>
            <el-table-column label="最大回撤" width="100">
              <template #default="{ row }">
                <span style="color: var(--qp-down)">{{ formatPercent(row.max_drawdown) }}</span>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无策略数据" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>最近交易</span></template>
          <el-table v-if="recentOrders.length" :data="recentOrders" stripe size="small">
            <el-table-column prop="symbol" label="标的" width="90" />
            <el-table-column label="方向" width="60">
              <template #default="{ row }">
                <span :style="{ color: row.side === 'buy' ? 'var(--qp-up)' : 'var(--qp-down)' }">
                  {{ SIDE_LABELS[row.side] || row.side }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="qty" label="数量" width="70" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="(STATUS_LABELS[row.status]?.type as any) || 'info'" size="small">
                  {{ STATUS_LABELS[row.status]?.label || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" min-width="140">
              <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无交易记录" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.dashboard-view {
  .stat-row {
    margin-bottom: 20px;
  }

  .stat-card {
    text-align: center;
  }

  .stat-label {
    font-size: 14px;
    color: var(--qp-text-secondary);
    margin-bottom: 8px;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 600;
    color: var(--qp-text-primary);

    small {
      font-size: 14px;
      font-weight: 400;
      color: var(--qp-text-secondary);
      margin-left: 4px;
    }
  }

  .chart-area {
    height: 320px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style>
