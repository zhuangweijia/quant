import { defineStore } from "pinia";
import { ref } from "vue";
import { marketApi } from "@/api/market";
import type { SymbolInfo, KlineData, TickPrice } from "@/types/market";

export const useMarketStore = defineStore("market", () => {
  const searchResults = ref<SymbolInfo[]>([]);
  const watchlist = ref<SymbolInfo[]>([]);
  const klines = ref<KlineData[]>([]);
  const currentSymbol = ref<SymbolInfo | null>(null);
  const tickData = ref<TickPrice | null>(null);

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

  function selectSymbol(symbol: SymbolInfo) {
    currentSymbol.value = symbol;
    if (!watchlist.value.find((s) => s.symbol === symbol.symbol && s.market === symbol.market)) {
      watchlist.value.push(symbol);
    }
  }

  function removeFromWatchlist(symbol: string, market: string) {
    watchlist.value = watchlist.value.filter((s) => !(s.symbol === symbol && s.market === market));
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
    selectSymbol,
    removeFromWatchlist,
  };
});
