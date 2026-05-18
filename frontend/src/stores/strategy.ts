import { defineStore } from "pinia";
import { ref } from "vue";
import { strategyApi } from "@/api/strategy";
import type { StrategyListItem, StrategyDetail } from "@/types/strategy";

export const useStrategyStore = defineStore("strategy", () => {
  const strategies = ref<StrategyListItem[]>([]);
  const currentStrategy = ref<StrategyDetail | null>(null);
  const total = ref(0);

  async function fetchStrategies(params?: Record<string, any>) {
    const res: any = await strategyApi.list(params);
    strategies.value = res.data?.items || [];
    total.value = res.data?.total || 0;
  }

  async function fetchDetail(id: string) {
    const res: any = await strategyApi.get(id);
    currentStrategy.value = res.data;
  }

  async function startStrategy(id: string) {
    await strategyApi.start(id);
    await fetchStrategies();
  }

  async function stopStrategy(id: string) {
    await strategyApi.stop(id);
    await fetchStrategies();
  }

  async function deleteStrategy(id: string) {
    await strategyApi.remove(id);
    await fetchStrategies();
  }

  return {
    strategies,
    currentStrategy,
    total,
    fetchStrategies,
    fetchDetail,
    startStrategy,
    stopStrategy,
    deleteStrategy,
  };
});
