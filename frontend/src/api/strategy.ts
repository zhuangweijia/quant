import client from "./client";
import type { ResponseBase, PageResponse } from "@/types/common";
import type {
  StrategyListItem,
  StrategyDetail,
  StrategyCreateRequest,
  StrategyUpdateRequest,
} from "@/types/strategy";

export const strategyApi = {
  list: (params?: Record<string, any>) =>
    client.get<ResponseBase<PageResponse<StrategyListItem>>>("/api/v1/strategies", { params }),

  get: (id: string) =>
    client.get<ResponseBase<StrategyDetail>>(`/api/v1/strategies/${id}`),

  create: (data: StrategyCreateRequest) =>
    client.post<ResponseBase<StrategyDetail>>("/api/v1/strategies", data),

  update: (id: string, data: StrategyUpdateRequest) =>
    client.put<ResponseBase<StrategyDetail>>(`/api/v1/strategies/${id}`, data),

  remove: (id: string) =>
    client.delete<ResponseBase<null>>(`/api/v1/strategies/${id}`),

  start: (id: string) =>
    client.post<ResponseBase<null>>(`/api/v1/strategies/${id}/start`),

  stop: (id: string) =>
    client.post<ResponseBase<null>>(`/api/v1/strategies/${id}/stop`),
};

export const strategyLogApi = {
  list: (strategyId: string, params?: Record<string, any>) =>
    client.get<ResponseBase<PageResponse<any>>>(`/api/v1/strategies/${strategyId}/logs`, { params }),
};

export const strategyVersionApi = {
  list: (strategyId: string) =>
    client.get<ResponseBase<any[]>>(`/api/v1/strategies/${strategyId}/versions`),

  get: (strategyId: string, version: number) =>
    client.get<ResponseBase<any>>(`/api/v1/strategies/${strategyId}/versions/${version}`),

  rollback: (strategyId: string, targetVersion: number) =>
    client.post<ResponseBase<any>>(`/api/v1/strategies/${strategyId}/rollback`, { target_version: targetVersion }),
};
