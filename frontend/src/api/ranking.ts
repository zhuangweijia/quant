import client from "./client";
import type { ResponseBase } from "@/types/common";

export interface RankingItem {
  rank: number;
  symbol: string;
  name: string | null;
  score: number;
  label: string | null;
  rank_change: number | null;
  confidence: string;
}

export interface RankingResponse {
  date: string;
  total: number;
  items: RankingItem[];
}

export const rankingApi = {
  getRankings: (params?: { date?: string; label?: string; page?: number; size?: number }) =>
    client.get<ResponseBase<RankingResponse>>("/api/v1/rankings", { params }),
};
