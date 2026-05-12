import { defineStore } from "pinia";
import { ref } from "vue";
import { tradeApi } from "@/api/trade";
import type { Order, Position, OrderRequest } from "@/types/trade";

export const useTradeStore = defineStore("trade", () => {
  const positions = ref<Position[]>([]);
  const orders = ref<Order[]>([]);

  async function fetchPositions() {
    const res: any = await tradeApi.getPositions();
    positions.value = res.data;
  }

  async function fetchOrders(params?: Record<string, any>) {
    const res: any = await tradeApi.getOrders(params);
    orders.value = res.data.items;
  }

  async function submitOrder(data: OrderRequest) {
    await tradeApi.submitOrder(data);
  }

  async function cancelOrder(orderId: string) {
    await tradeApi.cancelOrder(orderId);
  }

  return { positions, orders, fetchPositions, fetchOrders, submitOrder, cancelOrder };
});
