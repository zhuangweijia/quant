import client from "./client";
import type { ResponseBase } from "@/types/common";

export interface AnalysisStatus {
  run_id: string | null;
  trigger_type: string | null;
  status: string;
  stages: Record<string, { status: string; started_at?: string; finished_at?: string; error?: string }> | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export const analysisApi = {
  trigger: () =>
    client.post<ResponseBase<{ run_id: string; status: string }>>("/api/v1/analysis/trigger"),

  getStatus: () =>
    client.get<ResponseBase<AnalysisStatus>>("/api/v1/analysis/status"),
};
