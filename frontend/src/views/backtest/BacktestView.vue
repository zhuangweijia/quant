<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useBacktestStore } from "@/stores/backtest";
import { strategyApi } from "@/api/strategy";
import { MARKET_LABELS, TIMEFRAME_OPTIONS } from "@/utils/constants";
import { formatPercent, formatNumber, toNum } from "@/utils/format";
import { ElMessage, ElMessageBox } from "element-plus";
import type { StrategyListItem } from "@/types/strategy";

const store = useBacktestStore();
const strategies = ref<StrategyListItem[]>([]);
const loading = ref(false);

const form = ref({
  strategy_id: "",
  symbol: "",
  market: "crypto",
  timeframe: "1d",
  start_date: "",
  end_date: "",
  initial_capital: 100000,
});

const dateRange = ref<[string, string]>(["", ""]);

onMounted(async () => {
  loading.value = true;
  try {
    const res: any = await strategyApi.list();
    strategies.value = res.data.items || [];
    await store.fetchResults();
  } catch (e: any) {
    ElMessage.error(e.message || "加载数据失败");
  } finally {
    loading.value = false;
  }
});

function onDateRangeChange(val: [string, string] | null) {
  if (val) {
    form.value.start_date = val[0];
    form.value.end_date = val[1];
  } else {
    form.value.start_date = "";
    form.value.end_date = "";
  }
}

async function handleRun() {
  if (!form.value.strategy_id) {
    ElMessage.warning("请选择策略");
    return;
  }
  if (!form.value.symbol) {
    ElMessage.warning("请输入标的代码");
    return;
  }
  if (!form.value.start_date || !form.value.end_date) {
    ElMessage.warning("请选择回测日期范围");
    return;
  }
  try {
    const result = await store.runBacktest(form.value);
    ElMessage.success("回测完成");
  } catch (e: any) {
    ElMessage.error(e.message || "回测失败");
  }
}

async function handleView(id: string) {
  try {
    await store.fetchResult(id);
    detailVisible.value = true;
  } catch (e: any) {
    ElMessage.error(e.message || "加载详情失败");
  }
}

async function handleDelete(id: string) {
  try {
    await ElMessageBox.confirm("确定删除该回测结果？", "确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
    await store.deleteResult(id);
    ElMessage.success("已删除");
  } catch {
    // cancelled
  }
}

const detailVisible = ref(false);
</script>

<template>
  <div class="backtest-view">
    <el-card shadow="hover" style="margin-bottom: 20px">
      <template #header><span>运行回测</span></template>
      <el-form :model="form" label-width="100px" style="max-width: 800px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="策略">
              <el-select v-model="form.strategy_id" placeholder="选择策略" filterable style="width: 100%">
                <el-option
                  v-for="s in strategies"
                  :key="s.id"
                  :label="s.name"
                  :value="s.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标的">
              <el-input v-model="form.symbol" placeholder="如 BTC/USDT" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="市场">
              <el-select v-model="form.market" style="width: 100%">
                <el-option
                  v-for="(label, value) in MARKET_LABELS"
                  :key="value"
                  :label="label"
                  :value="value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="时间框架">
              <el-select v-model="form.timeframe" style="width: 100%">
                <el-option
                  v-for="tf in TIMEFRAME_OPTIONS"
                  :key="tf.value"
                  :label="tf.label"
                  :value="tf.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="日期范围">
              <el-date-picker
                v-model="dateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                style="width: 100%"
                @change="onDateRangeChange"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="初始资金">
              <el-input-number v-model="form.initial_capital" :min="1000" :step="10000" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-button type="primary" @click="handleRun" :loading="store.running">
            运行回测
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover">
      <template #header><span>回测结果</span></template>
      <el-table :data="store.results" v-loading="loading" stripe>
        <el-table-column prop="strategy_id" label="策略ID" min-width="120">
          <template #default="{ row }">{{ row.strategy_id?.slice(0, 8) }}...</template>
        </el-table-column>
        <el-table-column prop="symbol" label="标的" width="110" />
        <el-table-column label="日期范围" width="200">
          <template #default="{ row }">{{ row.start_date }} ~ {{ row.end_date }}</template>
        </el-table-column>
        <el-table-column label="总收益率" width="100">
          <template #default="{ row }">
            <span :style="{ color: toNum(row.total_return) >= 0 ? 'var(--qp-up)' : 'var(--qp-down)' }">
              {{ formatPercent(row.total_return) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="最大回撤" width="100">
          <template #default="{ row }">
            <span style="color: var(--qp-down)">{{ formatPercent(row.max_drawdown) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="夏普比率" width="100">
          <template #default="{ row }">{{ formatNumber(row.sharpe_ratio) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">
              {{ row.status === 'completed' ? '完成' : row.status === 'failed' ? '失败' : '运行中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleView(row.id)">详情</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="detailVisible" title="回测详情" width="700px" destroy-on-close>
      <template v-if="store.currentResult">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="总收益率">
            <span :style="{ color: toNum(store.currentResult.total_return) >= 0 ? 'var(--qp-up)' : 'var(--qp-down)' }">
              {{ formatPercent(store.currentResult.total_return) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="年化收益">{{ formatPercent(store.currentResult.annual_return) }}</el-descriptions-item>
          <el-descriptions-item label="最大回撤">
            <span style="color: var(--qp-down)">{{ formatPercent(store.currentResult.max_drawdown) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="夏普比率">{{ formatNumber(store.currentResult.sharpe_ratio) }}</el-descriptions-item>
          <el-descriptions-item label="胜率">{{ formatPercent(store.currentResult.win_rate) }}</el-descriptions-item>
          <el-descriptions-item label="盈亏比">{{ formatNumber(store.currentResult.profit_factor) }}</el-descriptions-item>
          <el-descriptions-item label="总交易次数">{{ store.currentResult.trade_count ?? '-' }}</el-descriptions-item>
          <el-descriptions-item label="初始资金">{{ formatNumber(store.currentResult.initial_capital, 0) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="store.currentResult.status === 'completed' ? 'success' : 'warning'" size="small">
              {{ store.currentResult.status }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.backtest-view {
  .el-form-item {
    margin-bottom: 16px;
  }
}
</style>
