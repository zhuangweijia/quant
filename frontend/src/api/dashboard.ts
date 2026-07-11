import client from "./client";
import type { ResponseBase } from "@/types/common";

export const dashboardApi = {
  getOverview: () =>
    client.get<ResponseBase<any>>("/api/v1/dashboard/overview"),
};
