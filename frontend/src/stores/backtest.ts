import { defineStore } from "pinia";
import { ref } from "vue";
import { backtestApi } from "@/api/backtest";
import type { BacktestResultListItem, BacktestResultDetail, BacktestRunRequest } from "@/types/backtest";

export const useBacktestStore = defineStore("backtest", () => {
  const results = ref<BacktestResultListItem[]>([]);
  const currentResult = ref<BacktestResultDetail | null>(null);
  const total = ref(0);
  const running = ref(false);

  async function fetchResults(params?: Record<string, any>) {
    const res: any = await backtestApi.listResults(params);
    results.value = res.data.items || [];
    total.value = res.data.total || 0;
  }

  async function runBacktest(data: BacktestRunRequest) {
    running.value = true;
    try {
      const res: any = await backtestApi.run(data);
      currentResult.value = res.data;
      await fetchResults();
      return res.data;
    } finally {
      running.value = false;
    }
  }

  async function fetchResult(id: string) {
    const res: any = await backtestApi.getResult(id);
    currentResult.value = res.data;
  }

  async function deleteResult(id: string) {
    await backtestApi.deleteResult(id);
    await fetchResults();
  }

  return { results, currentResult, total, running, fetchResults, runBacktest, fetchResult, deleteResult };
});
