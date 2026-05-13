import client from "./client";
import type { ResponseBase, PageResponse } from "@/types/common";
import type { BacktestRunRequest, BacktestResultListItem, BacktestResultDetail } from "@/types/backtest";

export const backtestApi = {
  run: (data: BacktestRunRequest) =>
    client.post<ResponseBase<BacktestResultDetail>>("/api/v1/backtest/run", data),

  listResults: (params?: Record<string, any>) =>
    client.get<ResponseBase<PageResponse<BacktestResultListItem>>>("/api/v1/backtest/results", { params }),

  getResult: (id: string) =>
    client.get<ResponseBase<BacktestResultDetail>>(`/api/v1/backtest/results/${id}`),

  deleteResult: (id: string) =>
    client.delete<ResponseBase<null>>(`/api/v1/backtest/results/${id}`),
};
