import client from "./client";
import type { ResponseBase } from "@/types/common";
import type { LoginRequest, RegisterRequest, TokenResponse, UserInfo } from "@/types/auth";

export const authApi = {
  login: (data: LoginRequest) =>
    client.post<ResponseBase<TokenResponse>>("/api/v1/auth/login", data),

  register: (data: RegisterRequest) =>
    client.post<ResponseBase<UserInfo>>("/api/v1/auth/register", data),

  getMe: () =>
    client.get<ResponseBase<UserInfo>>("/api/v1/auth/me"),

  refresh: (refreshToken: string) =>
    client.post<ResponseBase<TokenResponse>>("/api/v1/auth/refresh", {
      refresh_token: refreshToken,
    }),
};
