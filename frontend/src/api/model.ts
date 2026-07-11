import client from "./client";
import type { ResponseBase } from "@/types/common";

export interface ModelVersion {
  version: string;
  trained_at: string;
  data_start: string;
  data_end: string;
  ic: number | null;
  val_accuracy: number | null;
  top_features: Record<string, number> | null;
  is_active: boolean;
  n_estimators: number;
}

export interface TrainResult {
  version: string;
  ic: number | null;
  val_accuracy: number | null;
}

export interface BacktestResult {
  model_version: string;
  start_date: string;
  end_date: string;
  group_returns: Record<string, { date: string; return: number | null }[]>;
  ic_series: { date: string; ic: number | null }[];
  metrics: Record<string, Record<string, number>>;
}

export const modelApi = {
  getVersions: () =>
    client.get<ResponseBase<{ versions: ModelVersion[] }>>("/api/v1/model/versions"),

  train: () =>
    client.post<ResponseBase<TrainResult>>("/api/v1/model/train"),

  activate: (version: string) =>
    client.post<ResponseBase<{ version: string; activated: boolean }>>(
      `/api/v1/model/${version}/activate`
    ),

  backtest: (params: { model_version?: string; start_date?: string; end_date?: string }) =>
    client.post<ResponseBase<BacktestResult>>("/api/v1/model/backtest", params),
};
