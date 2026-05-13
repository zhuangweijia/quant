<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useTradeStore } from "@/stores/trade";
import { MARKET_LABELS, SIDE_LABELS, STATUS_LABELS } from "@/utils/constants";
import { formatCurrency, formatNumber, formatPercent, toNum } from "@/utils/format";
import { ElMessage, ElMessageBox } from "element-plus";

const store = useTradeStore();
const loading = ref(false);
const submitting = ref(false);

const orderForm = reactive({
  symbol: "",
  market: "crypto",
  side: "buy",
  order_type: "market",
  qty: 1,
  price: undefined as number | undefined,
});

onMounted(async () => {
  loading.value = true;
  try {
    await Promise.all([
      store.fetchAccount(),
      store.fetchPositions(),
      store.fetchOrders({ page: 1, page_size: 50 }),
    ]);
  } finally {
    loading.value = false;
  }
});

async function handleSubmitOrder() {
  if (!orderForm.symbol) {
    ElMessage.warning("请输入标的代码");
    return;
  }
  if (orderForm.order_type === "limit" && !orderForm.price) {
    ElMessage.warning("请输入限价");
    return;
  }
  try {
    await ElMessageBox.confirm(
      `确认提交${SIDE_LABELS[orderForm.side]}订单：${orderForm.symbol} x ${orderForm.qty}`,
      "确认下单",
      { confirmButtonText: "确认", cancelButtonText: "取消", type: "warning" }
    );
  } catch {
    return;
  }
  submitting.value = true;
  try {
    await store.submitOrder({
      symbol: orderForm.symbol,
      market: orderForm.market,
      side: orderForm.side,
      order_type: orderForm.order_type,
      qty: orderForm.qty,
      price: orderForm.order_type === "limit" ? orderForm.price : undefined,
    });
    ElMessage.success("订单已提交");
    orderForm.symbol = "";
    orderForm.qty = 1;
    orderForm.price = undefined;
    await Promise.all([store.fetchPositions(), store.fetchOrders({ page: 1, page_size: 50 })]);
  } catch (e: any) {
    ElMessage.error(e.message || "下单失败");
  } finally {
    submitting.value = false;
  }
}

async function handleCancelOrder(id: string) {
  try {
    await ElMessageBox.confirm("确认撤单？", "确认", { type: "warning" });
    await store.cancelOrder(id);
    ElMessage.success("已撤单");
    await store.fetchOrders({ page: 1, page_size: 50 });
  } catch {
    // cancelled
  }
}

async function handleClosePosition(id: string) {
  try {
    await ElMessageBox.confirm("确认平仓？", "确认", { type: "warning" });
    await store.closePosition(id);
    ElMessage.success("已平仓");
    await Promise.all([store.fetchPositions(), store.fetchAccount()]);
  } catch {
    // cancelled
  }
}

const modeLabels: Record<string, string> = {
  paper: "模拟盘",
  live: "实盘",
  backtest: "回测模式",
};
</script>

<template>
  <div class="trade-view" v-loading="loading">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover" style="margin-bottom: 20px">
          <template #header>
            <div class="card-header">
              <span>账户信息</span>
              <el-tag
                :type="store.account?.mode === 'live' ? 'danger' : 'success'"
                size="small"
              >
                {{ modeLabels[store.account?.mode || "paper"] || "模拟盘" }}
              </el-tag>
            </div>
          </template>
          <div v-if="store.account" class="account-info">
            <div class="account-row">
              <span class="account-label">总权益</span>
              <span class="account-value">{{ formatCurrency(store.account.total_equity) }}</span>
            </div>
            <div class="account-row">
              <span class="account-label">可用资金</span>
              <span class="account-value">{{ formatCurrency(store.account.cash) }}</span>
            </div>
            <div class="account-row">
              <span class="account-label">持仓市值</span>
              <span class="account-value">{{ formatCurrency(store.account.position_value) }}</span>
            </div>
            <div class="account-row">
              <span class="account-label">日盈亏</span>
              <span class="account-value" :style="{ color: toNum(store.account.daily_pnl) >= 0 ? 'var(--qp-up)' : 'var(--qp-down)' }">
                {{ formatCurrency(store.account.daily_pnl) }}
              </span>
            </div>
          </div>
          <el-empty v-else description="暂无账户信息" :image-size="60" />
        </el-card>

        <el-card shadow="hover">
          <template #header><span>下单</span></template>
          <el-form :model="orderForm" label-width="70px" size="default">
            <el-form-item label="标的">
              <el-input v-model="orderForm.symbol" placeholder="如 BTC/USDT" />
            </el-form-item>
            <el-form-item label="市场">
              <el-select v-model="orderForm.market" style="width: 100%">
                <el-option
                  v-for="(label, value) in MARKET_LABELS"
                  :key="value"
                  :label="label"
                  :value="value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="订单类型">
              <el-radio-group v-model="orderForm.order_type">
                <el-radio-button value="market">市价</el-radio-button>
                <el-radio-button value="limit">限价</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="方向">
              <el-radio-group v-model="orderForm.side">
                <el-radio-button value="buy">买入</el-radio-button>
                <el-radio-button value="sell">卖出</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="数量">
              <el-input-number v-model="orderForm.qty" :min="0.001" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item v-if="orderForm.order_type === 'limit'" label="价格">
              <el-input-number v-model="orderForm.price" :min="0" :precision="2" style="width: 100%" />
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="submitting"
                @click="handleSubmitOrder"
                style="width: 100%"
              >
                {{ SIDE_LABELS[orderForm.side] }} {{ orderForm.order_type === 'limit' ? '限价单' : '市价单' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="hover" style="margin-bottom: 20px">
          <template #header><span>当前持仓</span></template>
          <el-table :data="store.positions" stripe size="small">
            <el-table-column prop="symbol" label="标的" width="120" />
            <el-table-column label="市场" width="90">
              <template #default="{ row }">{{ MARKET_LABELS[row.market] || row.market }}</template>
            </el-table-column>
            <el-table-column prop="qty" label="数量" width="100">
              <template #default="{ row }">{{ formatNumber(row.qty, 4) }}</template>
            </el-table-column>
            <el-table-column label="均价" width="110">
              <template #default="{ row }">{{ formatNumber(row.avg_price) }}</template>
            </el-table-column>
            <el-table-column label="市值" width="120">
              <template #default="{ row }">{{ formatCurrency(toNum(row.qty) * toNum(row.avg_price)) }}</template>
            </el-table-column>
            <el-table-column label="未实现盈亏" width="130">
              <template #default="{ row }">
                <span :style="{ color: toNum(row.unrealized_pnl) >= 0 ? 'var(--qp-up)' : 'var(--qp-down)' }">
                  {{ formatCurrency(row.unrealized_pnl) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="盈亏%" width="100">
              <template #default="{ row }">
                <span :style="{ color: toNum(row.unrealized_pnl_pct) >= 0 ? 'var(--qp-up)' : 'var(--qp-down)' }">
                  {{ formatPercent(row.unrealized_pnl_pct) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="danger" @click="handleClosePosition(row.id)">平仓</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!store.positions.length" description="暂无持仓" :image-size="60" />
        </el-card>

        <el-card shadow="hover">
          <template #header><span>委托记录</span></template>
          <el-table :data="store.orders" stripe size="small">
            <el-table-column prop="symbol" label="标的" width="100" />
            <el-table-column label="方向" width="60">
              <template #default="{ row }">
                <span :style="{ color: row.side === 'buy' ? 'var(--qp-up)' : 'var(--qp-down)' }">
                  {{ SIDE_LABELS[row.side] || row.side }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="60">
              <template #default="{ row }">{{ row.order_type === "market" ? "市价" : "限价" }}</template>
            </el-table-column>
            <el-table-column prop="qty" label="数量" width="80">
              <template #default="{ row }">{{ formatNumber(row.qty, 4) }}</template>
            </el-table-column>
            <el-table-column label="价格" width="100">
              <template #default="{ row }">{{ row.price ? formatNumber(row.price) : "-" }}</template>
            </el-table-column>
            <el-table-column label="成交价" width="100">
              <template #default="{ row }">{{ row.filled_price ? formatNumber(row.filled_price) : "-" }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="(STATUS_LABELS[row.status]?.type as any) || 'info'" size="small">
                  {{ STATUS_LABELS[row.status]?.label || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" min-width="140">
              <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
            </el-table-column>
            <el-table-column label="操作" width="70" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'pending' || row.status === 'submitted'"
                  size="small"
                  type="danger"
                  text
                  @click="handleCancelOrder(row.id)"
                >
                  撤单
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!store.orders.length" description="暂无委托记录" :image-size="60" />
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

.account-info {
  .account-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid var(--qp-border-color);

    &:last-child {
      border-bottom: none;
    }
  }

  .account-label {
    color: var(--qp-text-secondary);
    font-size: 14px;
  }

  .account-value {
    font-weight: 600;
    font-size: 14px;
  }
}
</style>
