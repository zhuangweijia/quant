import client from "./client";
import type { ResponseBase } from "@/types/common";
import type { DashboardOverview, EquityCurvePoint, StrategyRankItem } from "@/types/dashboard";

export const dashboardApi = {
  getOverview: () =>
    client.get<ResponseBase<DashboardOverview>>("/api/v1/dashboard/overview"),

  getEquityCurve: (params?: Record<string, any>) =>
    client.get<ResponseBase<EquityCurvePoint[]>>("/api/v1/dashboard/equity-curve", { params }),

  getStrategyRanking: () =>
    client.get<ResponseBase<StrategyRankItem[]>>("/api/v1/dashboard/strategy-ranking"),
};
