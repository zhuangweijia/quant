import { defineStore } from "pinia";
import { ref } from "vue";
import { riskApi } from "@/api/risk";
import { wsClient } from "@/utils/websocket";
import type { RiskRule, RiskRuleCreateRequest, RiskRuleUpdateRequest, Alert } from "@/types/risk";

export const useRiskStore = defineStore("risk", () => {
  const rules = ref<RiskRule[]>([]);
  const alerts = ref<Alert[]>([]);
  const alertTotal = ref(0);
  const unreadCount = ref(0);

  const onRiskAlert = () => {
    fetchUnreadCount();
  };

  wsClient.on("risk:alert", onRiskAlert);

  async function fetchRules() {
    const res: any = await riskApi.getRules();
    rules.value = res.data || [];
  }

  async function createRule(data: RiskRuleCreateRequest) {
    await riskApi.createRule(data);
    await fetchRules();
  }

  async function updateRule(id: string, data: RiskRuleUpdateRequest) {
    await riskApi.updateRule(id, data);
    await fetchRules();
  }

  async function toggleRule(id: string) {
    await riskApi.toggleRule(id);
    await fetchRules();
  }

  async function deleteRule(id: string) {
    await riskApi.deleteRule(id);
    await fetchRules();
  }

  async function fetchAlerts(params?: Record<string, any>) {
    const res: any = await riskApi.getAlerts(params);
    alerts.value = res.data.items || [];
    alertTotal.value = res.data.total || 0;
  }

  async function markAlertRead(id: string) {
    await riskApi.markAlertRead(id);
    await fetchAlerts();
    await fetchUnreadCount();
  }

  async function markAllAlertsRead() {
    await riskApi.markAllAlertsRead();
    await fetchAlerts();
    await fetchUnreadCount();
  }

  async function fetchUnreadCount() {
    try {
      const res: any = await riskApi.getUnreadCount();
      unreadCount.value = res.data || 0;
    } catch {
      unreadCount.value = 0;
    }
  }

  return {
    rules,
    alerts,
    alertTotal,
    unreadCount,
    fetchRules,
    createRule,
    updateRule,
    toggleRule,
    deleteRule,
    fetchAlerts,
    markAlertRead,
    markAllAlertsRead,
    fetchUnreadCount,
    $dispose() {
      wsClient.off("risk:alert", onRiskAlert);
    },
  };
});
