import client from "./client";
import type { ResponseBase, PageResponse } from "@/types/common";
import type { RiskRule, RiskRuleCreateRequest, RiskRuleUpdateRequest, Alert } from "@/types/risk";

export const riskApi = {
  getRules: () =>
    client.get<ResponseBase<RiskRule[]>>("/api/v1/risk/rules"),

  createRule: (data: RiskRuleCreateRequest) =>
    client.post<ResponseBase<RiskRule>>("/api/v1/risk/rules", data),

  updateRule: (id: string, data: RiskRuleUpdateRequest) =>
    client.put<ResponseBase<RiskRule>>(`/api/v1/risk/rules/${id}`, data),

  toggleRule: (id: string) =>
    client.patch<ResponseBase<RiskRule>>(`/api/v1/risk/rules/${id}/toggle`),

  deleteRule: (id: string) =>
    client.delete<ResponseBase<null>>(`/api/v1/risk/rules/${id}`),

  getAlerts: (params?: Record<string, any>) =>
    client.get<ResponseBase<PageResponse<Alert>>>("/api/v1/risk/alerts", { params }),

  markAlertRead: (id: string) =>
    client.put<ResponseBase<null>>(`/api/v1/risk/alerts/${id}/read`),

  markAllAlertsRead: () =>
    client.post<ResponseBase<null>>("/api/v1/risk/alerts/read-all"),

  getUnreadCount: () =>
    client.get<ResponseBase<number>>("/api/v1/risk/alerts/unread-count"),
};
