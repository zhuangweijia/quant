import { defineStore } from "pinia";
import { ref } from "vue";
import { tradeApi } from "@/api/trade";
import type { Order, Position, OrderRequest, AccountInfo } from "@/types/trade";

export const useTradeStore = defineStore("trade", () => {
  const positions = ref<Position[]>([]);
  const orders = ref<Order[]>([]);
  const account = ref<AccountInfo | null>(null);

  async function fetchPositions() {
    const res: any = await tradeApi.getPositions();
    positions.value = res.data || [];
  }

  async function fetchOrders(params?: Record<string, any>) {
    const res: any = await tradeApi.getOrders(params);
    orders.value = res.data.items || [];
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
    account,
    fetchPositions,
    fetchOrders,
    submitOrder,
    cancelOrder,
    closePosition,
    fetchAccount,
  };
});
