import client from "./client";
import type { ResponseBase, PageResponse } from "@/types/common";
import type { Order, Position, OrderRequest } from "@/types/trade";

export const tradeApi = {
  submitOrder: (data: OrderRequest) =>
    client.post<ResponseBase<Order>>("/api/v1/trade/order", data),

  cancelOrder: (orderId: string) =>
    client.delete<ResponseBase<null>>(`/api/v1/trade/order/${orderId}`),

  getOrders: (params?: Record<string, any>) =>
    client.get<ResponseBase<PageResponse<Order>>>("/api/v1/trade/orders", { params }),

  getPositions: () =>
    client.get<ResponseBase<Position[]>>("/api/v1/trade/positions"),
};
