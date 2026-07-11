import client from "./client";
import type { ResponseBase } from "@/types/common";

export interface StockDetail {
  symbol: string;
  name: string | null;
  industry: string | null;
  score: number | null;
  rank: number | null;
  label: string | null;
  confidence: string;
  explanation: {
    positive: ShapFactor[];
    negative: ShapFactor[];
  } | null;
  fundamentals: Record<string, number | null> | null;
  klines: KlinePoint[];
  northbound: { holding_pct: number } | null;
}

export interface ShapFactor {
  factor: string;
  value: number;
  shap: number;
  description: string;
  assessment: string;
}

export interface KlinePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ScoreHistoryItem {
  date: string;
  score: number;
  rank: number | null;
  label: string | null;
}

export const stockApi = {
  getDetail: (symbol: string) =>
    client.get<ResponseBase<StockDetail>>(`/api/v1/stocks/${symbol}/detail`),

  getScoreHistory: (symbol: string, days = 30) =>
    client.get<ResponseBase<{ symbol: string; history: ScoreHistoryItem[] }>>(
      `/api/v1/stocks/${symbol}/score-history`,
      { params: { days } }
    ),
};
