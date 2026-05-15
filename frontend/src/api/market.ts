import client from "./client";
import type { ResponseBase } from "@/types/common";
import type { SymbolInfo, KlineData, TickPrice, WatchlistItem } from "@/types/market";

export const marketApi = {
  searchSymbols: (keyword: string) =>
    client.get<ResponseBase<SymbolInfo[]>>("/api/v1/market/symbols", { params: { keyword } }),

  getKlines: (params: { symbol: string; market: string; timeframe: string; limit?: number }) =>
    client.get<ResponseBase<KlineData[]>>("/api/v1/market/klines", { params }),

  getTick: (params: { symbol: string; market: string }) =>
    client.get<ResponseBase<TickPrice>>("/api/v1/market/tick", { params }),

  getWatchlist: () =>
    client.get<ResponseBase<WatchlistItem[]>>("/api/v1/market/watchlist"),

  addWatchlist: (data: { symbol: string; market: string }) =>
    client.post<ResponseBase<WatchlistItem>>("/api/v1/market/watchlist", data),

  removeWatchlist: (id: string) =>
    client.delete<ResponseBase<null>>(`/api/v1/market/watchlist/${id}`),
};
