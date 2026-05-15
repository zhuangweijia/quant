<script setup lang="ts">
import { ref, onMounted } from "vue";
import { dashboardApi } from "@/api/dashboard";
import { tradeApi } from "@/api/trade";
import { useTradeStore } from "@/stores/trade";
import { useRiskStore } from "@/stores/risk";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart, PieChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { formatCurrency, formatPercent, formatCompactNumber, formatDate } from "@/utils/format";

use([TitleComponent, TooltipComponent, LegendComponent, GridComponent, DataZoomComponent, LineChart, PieChart, CanvasRenderer]);

const tradeStore = useTradeStore();
const riskStore = useRiskStore();
const overview = ref<any>(null);
const equityRange = ref("1M");
const loading = ref(false);
const overviewError = ref("");

const equityOption = ref<any>({});
const positionOption = ref<any>({});

const recentOrders = ref<any[]>([]);
const strategyRanking = ref<any[]>([]);

async function loadData() {
  loading.value = true;
  overviewError.value = "";
  try {
    const [overviewRes, equityRes, rankRes, ordersRes] = await Promise.allSettled([
      dashboardApi.getOverview(),
      dashboardApi.getEquityCurve({ range: equityRange.value }),
      dashboardApi.getStrategyRanking(),
      tradeApi.getOrders({ page: 1, page_size: 5 }),
    ]);

    if (overviewRes.status === "fulfilled") {
      overview.value = (overviewRes.value as any).data;
    } else {
      overviewError.value = "看板数据加载失败";
    }
    if (ordersRes.status === "fulfilled") recentOrders.value = (ordersRes.value as any).data?.items || [];
    if (rankRes.status === "fulfilled") strategyRanking.value = (rankRes.value as any).data || [];

    if (equityRes.status === "fulfilled") {
      const points = (equityRes.value as any).data || [];
      equityOption.value = {
        tooltip: { trigger: "axis" },
        grid: { left: 80, right: 30, top: 30, bottom: 40 },
        xAxis: { type: "category", data: points.map((p: any) => p.date), boundaryGap: false },
        yAxis: { type: "value", scale: true, axisLabel: { formatter: (v: number) => formatCompactNumber(v) } },
        dataZoom: [{ type: "inside" }],
        series: [
          {
            name: "权益",
            type: "line",
            data: points.map((p: any) => p.equity),
            smooth: true,
            lineStyle: { width: 2, color: "#409EFF" },
            areaStyle: {
              color: {
                type: "linear", x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: "rgba(64,158,255,0.3)" },
                  { offset: 1, color: "rgba(64,158,255,0.02)" },
                ],
              },
            },
          },
          ...(points.some((p: any) => p.benchmark != null)
            ? [{
                name: "基准",
                type: "line",
                data: points.map((p: any) => p.benchmark),
                lineStyle: { width: 1, type: "dashed", color: "#909399" },
              }]
            : []),
        ],
      };
    }

    if (overview.value) {
      await tradeStore.fetchPositions();
      const positions = tradeStore.positions;
      const posData = positions.slice(0, 6).map((p: any) => ({
        name: p.symbol,
        value: parseFloat(p.qty) * parseFloat(p.avg_price || 0),
      }));
      positionOption.value = {
        tooltip: { trigger: "item", formatter: "{b}: ¥{c}" },
        series: [{
          type: "pie", radius: ["40%", "70%"],
          data: posData.length ? posData : [{ name: "暂无持仓", value: 1 }],
          emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: "rgba(0,0,0,0.5)" } },
          label: { fontSize: 12 },
        }],
      };
    }
  } finally {
    loading.value = false;
  }
}

function onRangeChange() {
  loadData();
}

function getPnlColor(val: any) {
  const n = Number(val);
  if (n > 0) return "var(--qp-up)";
  if (n < 0) return "var(--qp-down)";
  return "var(--qp-text-regular)";
}

onMounted(() => {
  loadData();
  riskStore.fetchUnreadCount();
});
</script>

<template>
  <div class="dashboard" v-loading="loading">
    <el-alert v-if="overviewError && !loading" :title="overviewError" type="error" show-icon closable @close="overviewError = ''" style="margin-bottom: 16px" />
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">总资产</div>
          <div class="stat-value">{{ formatCurrency(overview?.total_equity) }}</div>
          <div class="stat-sub">模式: {{ overview?.mode === "paper" ? "模拟盘" : "实盘" }}</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">日盈亏</div>
          <div class="stat-value" :style="{ color: getPnlColor(overview?.daily_pnl) }">
            {{ formatCurrency(overview?.daily_pnl) }}
          </div>
          <div class="stat-sub" :style="{ color: getPnlColor(overview?.daily_pnl_pct) }">
            {{ formatPercent(overview?.daily_pnl_pct) }}
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">总盈亏</div>
          <div class="stat-value" :style="{ color: getPnlColor(overview?.total_pnl) }">
            {{ formatCurrency(overview?.total_pnl) }}
          </div>
          <div class="stat-sub" :style="{ color: getPnlColor(overview?.total_pnl_pct) }">
            {{ formatPercent(overview?.total_pnl_pct) }}
          </div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">运行策略</div>
          <div class="stat-value">{{ overview?.running_strategies || 0 }} / {{ overview?.total_strategies || 0 }}</div>
          <div class="stat-sub">今日交易: {{ overview?.today_trades || 0 }} 笔</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <el-col :xs="24" :md="16">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>权益曲线</span>
              <el-radio-group v-model="equityRange" size="small" @change="onRangeChange">
                <el-radio-button value="1D">1天</el-radio-button>
                <el-radio-button value="1W">1周</el-radio-button>
                <el-radio-button value="1M">1月</el-radio-button>
                <el-radio-button value="3M">3月</el-radio-button>
                <el-radio-button value="1Y">1年</el-radio-button>
                <el-radio-button value="ALL">全部</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart :option="equityOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
      <el-col :xs="24" :md="8">
        <el-card shadow="hover">
          <template #header><span>持仓分布</span></template>
          <v-chart :option="positionOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="table-row">
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header><span>策略表现</span></template>
          <el-table :data="strategyRanking" size="small" stripe>
            <el-table-column prop="strategy_name" label="策略名称" min-width="100" />
            <el-table-column label="总收益" width="100">
              <template #default="{ row }">
                <span :style="{ color: getPnlColor(row.total_return) }">{{ formatPercent(row.total_return / 100) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="夏普比率" width="90">
              <template #default="{ row }">{{ Number(row.sharpe_ratio).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="最大回撤" width="90">
              <template #default="{ row }">
                <span style="color: var(--qp-danger)">{{ Number(row.max_drawdown).toFixed(2) }}%</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="12">
        <el-card shadow="hover">
          <template #header><span>最近订单</span></template>
          <el-table :data="recentOrders" size="small" stripe>
            <el-table-column prop="symbol" label="标的" width="90" />
            <el-table-column label="方向" width="60">
              <template #default="{ row }">
                <span :style="{ color: row.side === 'buy' ? 'var(--qp-up)' : 'var(--qp-down)' }">
                  {{ row.side === "buy" ? "买入" : "卖出" }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="数量" width="80">
              <template #default="{ row }">{{ Number(row.filled_qty || row.qty).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'filled' ? 'success' : row.status === 'cancelled' ? 'danger' : 'info'">
                  {{ ({ filled: "已成交", pending: "待成交", submitted: "已提交", cancelled: "已撤单", rejected: "已拒绝" } as Record<string, string>)[row.status] || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" min-width="140">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.dashboard {
  max-width: 1400px;
}

.stat-row {
  margin-bottom: 16px;
}

.stat-card {
  text-align: center;

  .stat-label {
    font-size: 13px;
    color: var(--qp-text-secondary);
    margin-bottom: 8px;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 600;
    color: var(--qp-text-primary);
    margin-bottom: 4px;
  }

  .stat-sub {
    font-size: 12px;
    color: var(--qp-text-secondary);
  }
}

.chart-row {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.table-row {
  margin-bottom: 16px;
}
</style>
