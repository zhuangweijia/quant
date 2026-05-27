import { defineStore } from "pinia";
import { ref } from "vue";
import { tradeApi } from "@/api/trade";
import { wsClient } from "@/utils/websocket";
import type { Order, Position, OrderRequest, AccountInfo } from "@/types/trade";

export const useTradeStore = defineStore("trade", () => {
  const positions = ref<Position[]>([]);
  const orders = ref<Order[]>([]);
  const ordersTotal = ref(0);
  const account = ref<AccountInfo | null>(null);

  const onTradeOrder = () => {
    fetchOrders();
    fetchPositions();
    fetchAccount();
  };

  const onTradePosition = () => {
    fetchPositions();
    fetchAccount();
  };

  wsClient.on("trade:order", onTradeOrder);
  wsClient.on("trade:position", onTradePosition);

  async function fetchPositions() {
    const res: any = await tradeApi.getPositions();
    positions.value = res.data || [];
  }

  async function fetchOrders(params?: Record<string, any>) {
    const res: any = await tradeApi.getOrders(params);
    orders.value = res.data.items || [];
    ordersTotal.value = res.data.total || 0;
  }

  async function submitOrder(data: OrderRequest) {
    await tradeApi.submitOrder(data);
  }

  async function cancelOrder(orderId: string) {
    await tradeApi.cancelOrder(orderId);
  }

  async function closePosition(positionId: string) {
    await tradeApi.closePosition(positionId);
    await fetchPositions();
  }

  async function fetchAccount() {
    const res: any = await tradeApi.getAccount();
    account.value = res.data;
  }

  return {
    positions,
    orders,
    ordersTotal,
    account,
    fetchPositions,
    fetchOrders,
    submitOrder,
    cancelOrder,
    closePosition,
    fetchAccount,
    $dispose() {
      wsClient.off("trade:order", onTradeOrder);
      wsClient.off("trade:position", onTradePosition);
    },
  };
});
