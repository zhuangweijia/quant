import client from "./client";
import type { ResponseBase } from "@/types/common";

export const settingsApi = {
  getParams: () =>
    client.get<ResponseBase<Record<string, string>>>("/api/v1/settings/params"),

  updateParams: (data: Record<string, any>) =>
    client.put<ResponseBase<null>>("/api/v1/settings/params", { params: data }),

  resetParams: () =>
    client.post<ResponseBase<null>>("/api/v1/settings/params/reset"),

  getProfile: () =>
    client.get<ResponseBase<any>>("/api/v1/settings/profile"),

  changePassword: (data: { current_password: string; new_password: string }) =>
    client.put<ResponseBase<null>>("/api/v1/settings/password", data),
};
