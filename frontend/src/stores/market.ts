import { defineStore } from "pinia";
import { ref } from "vue";
import { marketApi } from "@/api/market";
import type { SymbolInfo, KlineData, TickPrice, WatchlistItem } from "@/types/market";

export const useMarketStore = defineStore("market", () => {
  const searchResults = ref<SymbolInfo[]>([]);
  const watchlist = ref<SymbolInfo[]>([]);
  const klines = ref<KlineData[]>([]);
  const currentSymbol = ref<SymbolInfo | null>(null);
  const tickData = ref<TickPrice | null>(null);
  const watchlistIdMap = ref<Map<string, string>>(new Map());

  async function searchSymbols(keyword: string) {
    const res: any = await marketApi.searchSymbols(keyword);
    searchResults.value = res.data || [];
  }

  async function fetchKlines(params: { symbol: string; market: string; timeframe: string; limit?: number }) {
    const res: any = await marketApi.getKlines(params);
    klines.value = res.data || [];
  }

  async function fetchTick(params: { symbol: string; market: string }) {
    const res: any = await marketApi.getTick(params);
    tickData.value = res.data;
  }

  async function initWatchlist() {
    try {
      const res: any = await marketApi.getWatchlist();
      const items: WatchlistItem[] = res.data || [];
      watchlist.value = items.map((item) => ({ symbol: item.symbol, name: item.symbol, market: item.market }));
      watchlistIdMap.value.clear();
      items.forEach((item) => watchlistIdMap.value.set(`${item.symbol}:${item.market}`, item.id));
    } catch {
      // ignore
    }
  }

  async function selectSymbol(symbol: SymbolInfo) {
    currentSymbol.value = symbol;
    const key = `${symbol.symbol}:${symbol.market}`;
    if (!watchlist.value.find((s) => s.symbol === symbol.symbol && s.market === symbol.market)) {
      watchlist.value.push(symbol);
      try {
        const res: any = await marketApi.addWatchlist({ symbol: symbol.symbol, market: symbol.market });
        if (res.data?.id) watchlistIdMap.value.set(key, res.data.id);
      } catch {
        // ignore duplicate
      }
    }
  }

  async function removeFromWatchlist(symbol: string, market: string) {
    const key = `${symbol}:${market}`;
    const id = watchlistIdMap.value.get(key);
    watchlist.value = watchlist.value.filter((s) => !(s.symbol === symbol && s.market === market));
    watchlistIdMap.value.delete(key);
    if (id) {
      try {
        await marketApi.removeWatchlist(id);
      } catch {
        // ignore
      }
    }
  }

  return {
    searchResults,
    watchlist,
    klines,
    currentSymbol,
    tickData,
    searchSymbols,
    fetchKlines,
    fetchTick,
    initWatchlist,
    selectSymbol,
    removeFromWatchlist,
  };
});
