<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useTradeStore } from "@/stores/trade";
import { ElMessage, ElMessageBox } from "element-plus";
import { formatCurrency, formatDate } from "@/utils/format";

const tradeStore = useTradeStore();

const orderForm = ref({
  symbol: "BTCUSDT",
  market: "crypto",
  side: "buy",
  order_type: "market",
  qty: 1,
  price: undefined as number | undefined,
});

const orderPage = ref(1);
const orderPageSize = ref(10);

async function loadData() {
  await Promise.allSettled([
    tradeStore.fetchAccount(),
    tradeStore.fetchPositions(),
    tradeStore.fetchOrders({ page: orderPage.value, page_size: orderPageSize.value }),
  ]);
}

async function handleSubmitOrder() {
  if (!orderForm.value.symbol?.trim()) {
    ElMessage.warning("请输入标的代码");
    return;
  }
  if (!orderForm.value.qty || orderForm.value.qty <= 0) {
    ElMessage.warning("数量必须大于0");
    return;
  }
  if (orderForm.value.order_type === "limit" && !orderForm.value.price) {
    ElMessage.warning("限价单必须填写价格");
    return;
  }
  const actionText = orderForm.value.side === "buy" ? "买入" : "卖出";
  await ElMessageBox.confirm(
    `确认${actionText} ${orderForm.value.qty} ${orderForm.value.symbol}?`,
    "下单确认",
    { type: "warning" }
  );
  try {
    await tradeStore.submitOrder(orderForm.value as any);
    ElMessage.success("下单成功");
    await loadData();
  } catch (e: any) {
    ElMessage.error(e.message || "下单失败");
  }
}

async function handleCancelOrder(orderId: string) {
  await ElMessageBox.confirm("确认撤单?", "提示", { type: "warning" });
  try {
    await tradeStore.cancelOrder(orderId);
    ElMessage.success("已撤单");
    await loadData();
  } catch (e: any) {
    ElMessage.error(e.message);
  }
}

async function handleClosePosition(positionId: string) {
  await ElMessageBox.confirm("确认平仓?", "提示", { type: "warning" });
  try {
    await tradeStore.closePosition(positionId);
    ElMessage.success("平仓成功");
    await loadData();
  } catch (e: any) {
    ElMessage.error(e.message);
  }
}

function handleOrderPageChange(page: number) {
  orderPage.value = page;
  tradeStore.fetchOrders({ page, page_size: orderPageSize.value });
}

const accountInfo = computed(() => tradeStore.account);

onMounted(() => {
  loadData();
});
</script>

<template>
  <div class="trade-page">
    <el-row :gutter="16">
      <el-col :xs="24" :md="8">
        <el-card shadow="hover" class="account-card">
          <template #header><span>账户信息</span></template>
          <template v-if="accountInfo">
            <div class="info-row">
              <span class="label">总资产</span>
              <span class="value">{{ formatCurrency(accountInfo.total_equity) }}</span>
            </div>
            <div class="info-row">
              <span class="label">可用资金</span>
              <span class="value">{{ formatCurrency(accountInfo.cash) }}</span>
            </div>
            <div class="info-row">
              <span class="label">持仓市值</span>
              <span class="value">{{ formatCurrency(accountInfo.position_value) }}</span>
            </div>
            <div class="info-row">
              <span class="label">日盈亏</span>
              <span class="value" :style="{ color: Number(accountInfo.daily_pnl) >= 0 ? 'var(--qp-up)' : 'var(--qp-down)' }">
                {{ formatCurrency(accountInfo.daily_pnl) }}
              </span>
            </div>
            <el-tag size="small" type="warning" style="margin-top: 8px">
              {{ accountInfo.mode === "paper" ? "模拟盘" : "实盘" }}
            </el-tag>
          </template>
        </el-card>

        <el-card shadow="hover" style="margin-top: 16px">
          <template #header><span>下单</span></template>
          <el-form :model="orderForm" label-width="60px" size="default">
            <el-form-item label="标的">
              <el-input v-model="orderForm.symbol" />
            </el-form-item>
            <el-form-item label="市场">
              <el-select v-model="orderForm.market" style="width: 100%">
                <el-option label="A股" value="a_stock" />
                <el-option label="美股" value="us_stock" />
                <el-option label="加密货币" value="crypto" />
              </el-select>
            </el-form-item>
            <el-form-item label="类型">
              <el-radio-group v-model="orderForm.order_type">
                <el-radio value="market">市价</el-radio>
                <el-radio value="limit">限价</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="方向">
              <el-radio-group v-model="orderForm.side">
                <el-radio value="buy">
                  <span style="color: var(--qp-up)">买入</span>
                </el-radio>
                <el-radio value="sell">
                  <span style="color: var(--qp-down)">卖出</span>
                </el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="数量">
              <el-input-number v-model="orderForm.qty" :min="0.01" :step="1" style="width: 100%" />
            </el-form-item>
            <el-form-item v-if="orderForm.order_type === 'limit'" label="价格">
              <el-input-number v-model="orderForm.price" :min="0.01" :precision="2" style="width: 100%" />
            </el-form-item>
            <el-button
              type="primary"
              style="width: 100%"
              @click="handleSubmitOrder"
            >
              {{ orderForm.side === "buy" ? "买入" : "卖出" }}
            </el-button>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="16">
        <el-card shadow="hover">
          <template #header><span>当前持仓</span></template>
          <el-table :data="tradeStore.positions" size="small" stripe>
            <el-table-column prop="symbol" label="标的" width="100" />
            <el-table-column prop="market" label="市场" width="80">
              <template #default="{ row }">
                {{ ({ a_stock: "A股", us_stock: "美股", crypto: "加密" } as Record<string, string>)[row.market] || row.market }}
              </template>
            </el-table-column>
            <el-table-column label="数量" width="100">
              <template #default="{ row }">{{ Number(row.qty).toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="均价" width="110">
              <template #default="{ row }">{{ Number(row.avg_price).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="市值" width="120">
              <template #default="{ row }">{{ formatCurrency(Number(row.qty) * Number(row.avg_price)) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button link type="danger" size="small" @click="handleClosePosition(row.id)">平仓</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!tradeStore.positions.length" description="暂无持仓" :image-size="60" />
        </el-card>

        <el-card shadow="hover" style="margin-top: 16px">
          <template #header><span>订单记录</span></template>
          <el-table :data="tradeStore.orders" size="small" stripe>
            <el-table-column prop="symbol" label="标的" width="90" />
            <el-table-column label="方向" width="60">
              <template #default="{ row }">
                <span :style="{ color: row.side === 'buy' ? 'var(--qp-up)' : 'var(--qp-down)' }">
                  {{ row.side === "buy" ? "买入" : "卖出" }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="类型" width="60">
              <template #default="{ row }">{{ ({ market: "市价", limit: "限价", stop: "止损" } as Record<string, string>)[row.order_type] || row.order_type }}</template>
            </el-table-column>
            <el-table-column label="数量" width="80">
              <template #default="{ row }">{{ Number(row.qty).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="成交价" width="90">
              <template #default="{ row }">{{ row.filled_price ? Number(row.filled_price).toFixed(2) : "-" }}</template>
            </el-table-column>
            <el-table-column label="手续费" width="80">
              <template #default="{ row }">{{ Number(row.commission).toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'filled' ? 'success' : row.status === 'cancelled' ? 'danger' : 'info'">
                  {{ ({ filled: "已成交", pending: "待成交", submitted: "已提交", partial_filled: "部分成交", cancelled: "已撤单", rejected: "已拒绝" } as Record<string, string>)[row.status] || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" min-width="140">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="60" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'pending' || row.status === 'submitted'"
                  link type="danger" size="small"
                  @click="handleCancelOrder(row.id)"
                >撤单</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div style="margin-top: 12px; text-align: center" v-if="tradeStore.orders.length">
            <el-pagination
              small
              layout="prev, pager, next"
              :current-page="orderPage"
              :page-size="orderPageSize"
              :total="tradeStore.ordersTotal"
              @current-change="handleOrderPageChange"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.trade-page {
  max-width: 1400px;
}

.account-card {
  .info-row {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px solid #f5f5f5;

    .label {
      color: var(--qp-text-secondary);
      font-size: 13px;
    }

    .value {
      font-weight: 500;
      font-size: 14px;
    }
  }
}
</style>
