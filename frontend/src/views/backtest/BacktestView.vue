<script setup lang="ts">
import { ref, onMounted } from "vue";
import { strategyApi } from "@/api/strategy";
import { useBacktestStore } from "@/stores/backtest";
import { useStrategyStore } from "@/stores/strategy";
import { ElMessage, ElMessageBox } from "element-plus";
import VChart from "vue-echarts";
import { use } from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import { TitleComponent, TooltipComponent, GridComponent, DataZoomComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { formatPercent, formatDate } from "@/utils/format";

use([TitleComponent, TooltipComponent, GridComponent, DataZoomComponent, LineChart, BarChart, CanvasRenderer]);

const backtestStore = useBacktestStore();
const strategyStore = useStrategyStore();

const strategies = ref<any[]>([]);
const runForm = ref({
  strategy_id: "",
  symbol: "BTCUSDT",
  market: "crypto",
  timeframe: "1d",
  start_date: "",
  end_date: "",
  initial_capital: 100000,
});
const detailDialog = ref(false);
const detailData = ref<any>(null);
const equityChartOption = ref<any>({});
const drawdownChartOption = ref<any>({});

const currentPage = ref(1);
const pageSize = ref(20);

async function loadStrategies() {
  const res: any = await strategyApi.list();
  strategies.value = res.data?.items || [];
}

async function handleRun() {
  if (!runForm.value.strategy_id) {
    ElMessage.warning("请选择策略");
    return;
  }
  if (!runForm.value.start_date || !runForm.value.end_date) {
    ElMessage.warning("请选择日期范围");
    return;
  }
  if (runForm.value.start_date >= runForm.value.end_date) {
    ElMessage.warning("开始日期必须早于结束日期");
    return;
  }
  try {
    const result = await backtestStore.runBacktest(runForm.value as any);
    ElMessage.success("回测已提交");
    if (result) showDetail(result);
  } catch (e: any) {
    ElMessage.error(e.message || "回测失败");
  }
}

function showDetail(row: any) {
  detailData.value = row;
  if (row.equity_curve?.data) {
    const points = row.equity_curve.data;
    equityChartOption.value = {
      tooltip: { trigger: "axis" },
      grid: { left: 70, right: 20, top: 20, bottom: 30 },
      xAxis: { type: "category", data: points.map((p: any) => p.timestamp?.substring(0, 10)), boundaryGap: false },
      yAxis: { type: "value", scale: true },
      dataZoom: [{ type: "inside" }],
      series: [{
        type: "line", data: points.map((p: any) => p.equity), smooth: true,
        lineStyle: { width: 2, color: "#409EFF" },
        areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(64,158,255,0.25)" }, { offset: 1, color: "rgba(64,158,255,0.02)" }] } },
      }],
    };
  }
  if (row.drawdown_curve?.data) {
    const points = row.drawdown_curve.data;
    drawdownChartOption.value = {
      tooltip: { trigger: "axis" },
      grid: { left: 70, right: 20, top: 20, bottom: 30 },
      xAxis: { type: "category", data: points.map((p: any) => p.timestamp?.substring(0, 10)) },
      yAxis: { type: "value" },
      series: [{ type: "bar", data: points.map((p: any) => p.drawdown), itemStyle: { color: "#F56C6C" } }],
    };
  }
  detailDialog.value = true;
}

async function handleViewResult(row: any) {
  try {
    await backtestStore.fetchResult(row.id);
    showDetail(backtestStore.currentResult);
  } catch (e: any) {
    ElMessage.error(e.message);
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm("确认删除该回测结果?", "提示", { type: "warning" });
  await backtestStore.deleteResult(row.id);
  ElMessage.success("已删除");
}

async function handlePageChange(page: number) {
  currentPage.value = page;
  await backtestStore.fetchResults({ page: currentPage.value, size: pageSize.value });
}

function formatMetric(val: any) {
  if (val === null || val === undefined) return "-";
  return Number(val).toFixed(2);
}

onMounted(() => {
  loadStrategies();
  backtestStore.fetchResults({ page: currentPage.value, size: pageSize.value });
});
</script>

<template>
  <div class="backtest-page">
    <el-card shadow="hover" class="run-card">
      <template #header><span>运行回测</span></template>
      <el-form :model="runForm" label-width="80px" inline>
        <el-form-item label="策略">
          <el-select v-model="runForm.strategy_id" placeholder="选择策略" style="width: 200px">
            <el-option v-for="s in strategies" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="标的">
          <el-input v-model="runForm.symbol" style="width: 140px" />
        </el-form-item>
        <el-form-item label="市场">
          <el-select v-model="runForm.market" style="width: 120px">
            <el-option label="A股" value="a_stock" />
            <el-option label="美股" value="us_stock" />
            <el-option label="加密货币" value="crypto" />
          </el-select>
        </el-form-item>
        <el-form-item label="周期">
          <el-select v-model="runForm.timeframe" style="width: 100px">
            <el-option label="日线" value="1d" />
            <el-option label="1小时" value="1h" />
            <el-option label="4小时" value="4h" />
            <el-option label="周线" value="1w" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="runForm.start_date"
            type="date"
            placeholder="开始日期"
            value-format="YYYY-MM-DD"
            style="width: 150px"
          />
          <span style="margin: 0 8px">-</span>
          <el-date-picker
            v-model="runForm.end_date"
            type="date"
            placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 150px"
          />
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="runForm.initial_capital" :min="10000" :step="10000" style="width: 160px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="backtestStore.running" @click="handleRun">运行回测</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover" style="margin-top: 16px">
      <template #header><span>回测结果</span></template>
      <el-table :data="backtestStore.results" stripe>
        <el-table-column prop="strategy_id" label="策略ID" width="110">
          <template #default="{ row }">{{ row.strategy_id?.substring(0, 8) }}...</template>
        </el-table-column>
        <el-table-column prop="symbol" label="标的" width="90" />
        <el-table-column label="日期范围" width="180">
          <template #default="{ row }">{{ row.start_date }} ~ {{ row.end_date }}</template>
        </el-table-column>
        <el-table-column label="总收益" width="100">
          <template #default="{ row }">
            <span :style="{ color: Number(row.total_return) >= 0 ? 'var(--qp-up)' : 'var(--qp-down)' }">
              {{ formatMetric(row.total_return) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="最大回撤" width="100">
          <template #default="{ row }">
            <span style="color: var(--qp-danger)">{{ formatMetric(row.max_drawdown) }}%</span>
          </template>
        </el-table-column>
        <el-table-column label="夏普比率" width="90">
          <template #default="{ row }">{{ formatMetric(row.sharpe_ratio) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="({ completed: 'success', running: 'warning', failed: 'danger' }[row.status as string] ?? 'info') as any">
              {{ ({ completed: "完成", running: "运行中", failed: "失败" } as Record<string, string>)[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleViewResult(row)">详情</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="backtestStore.total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="detailDialog" title="回测详情" width="900px" destroy-on-close>
      <template v-if="detailData">
        <el-descriptions :column="3" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="总收益">{{ formatMetric(detailData.total_return) }}%</el-descriptions-item>
          <el-descriptions-item label="年化收益">{{ formatMetric(detailData.annual_return) }}%</el-descriptions-item>
          <el-descriptions-item label="最大回撤">{{ formatMetric(detailData.max_drawdown) }}%</el-descriptions-item>
          <el-descriptions-item label="夏普比率">{{ formatMetric(detailData.sharpe_ratio) }}</el-descriptions-item>
          <el-descriptions-item label="索提诺比率">{{ formatMetric(detailData.sortino_ratio) }}</el-descriptions-item>
          <el-descriptions-item label="卡尔玛比率">{{ formatMetric(detailData.calmar_ratio) }}</el-descriptions-item>
          <el-descriptions-item label="胜率">{{ formatMetric(detailData.win_rate) }}%</el-descriptions-item>
          <el-descriptions-item label="盈亏比">{{ formatMetric(detailData.profit_factor) }}</el-descriptions-item>
          <el-descriptions-item label="交易次数">{{ detailData.trade_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="初始资金">{{ formatMetric(detailData.initial_capital) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="detailData.status === 'completed' ? 'success' : 'danger'">
              {{ detailData.status }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="detailData.equity_curve?.data">
          <h4 style="margin: 12px 0 8px">权益曲线</h4>
          <v-chart :option="equityChartOption" style="height: 250px" autoresize />
        </div>

        <div v-if="detailData.drawdown_curve?.data">
          <h4 style="margin: 12px 0 8px">回撤曲线</h4>
          <v-chart :option="drawdownChartOption" style="height: 200px" autoresize />
        </div>

        <div v-if="detailData.trades?.data?.length">
          <h4 style="margin: 12px 0 8px">交易明细 ({{ detailData.trades.data.length }} 笔)</h4>
          <el-table :data="detailData.trades.data.slice(0, 20)" size="small" stripe max-height="300">
            <el-table-column prop="symbol" label="标的" width="90" />
            <el-table-column prop="side" label="方向" width="60">
              <template #default="{ row }">
                <span :style="{ color: row.side === 'buy' ? 'var(--qp-up)' : 'var(--qp-down)' }">
                  {{ row.side === "buy" ? "买" : "卖" }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="入场价" width="90">
              <template #default="{ row }">{{ Number(row.entry_price).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="出场价" width="90">
              <template #default="{ row }">{{ row.exit_price ? Number(row.exit_price).toFixed(2) : "-" }}</template>
            </el-table-column>
            <el-table-column label="数量" width="80">
              <template #default="{ row }">{{ Number(row.qty).toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="盈亏" width="100">
              <template #default="{ row }">
                <span :style="{ color: (row.pnl || 0) >= 0 ? 'var(--qp-up)' : 'var(--qp-down)' }">
                  {{ row.pnl ? Number(row.pnl).toFixed(2) : "-" }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.backtest-page {
  max-width: 1400px;
}

.run-card {
  :deep(.el-form-item) {
    margin-bottom: 12px;
  }
}
</style>
