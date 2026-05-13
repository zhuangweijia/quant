import client from "./client";
import type { ResponseBase } from "@/types/common";
import type {
  BrokerConfig,
  NotificationConfig,
  SystemParams,
  TradingModeConfig,
  ProfileInfo,
  PasswordChangeRequest,
} from "@/types/settings";

export const settingsApi = {
  getBrokers: () =>
    client.get<ResponseBase<BrokerConfig[]>>("/api/v1/settings/brokers"),

  updateBroker: (brokerName: string, data: Record<string, any>) =>
    client.put<ResponseBase<null>>(`/api/v1/settings/brokers/${brokerName}`, data),

  testBroker: (brokerName: string) =>
    client.post<ResponseBase<null>>(`/api/v1/settings/brokers/${brokerName}/test`),

  getTradingMode: () =>
    client.get<ResponseBase<TradingModeConfig>>("/api/v1/settings/trading-mode"),

  updateTradingMode: (data: TradingModeConfig) =>
    client.put<ResponseBase<null>>("/api/v1/settings/trading-mode", data),

  getNotifications: () =>
    client.get<ResponseBase<NotificationConfig>>("/api/v1/settings/notifications"),

  updateNotifications: (data: Record<string, any>) =>
    client.put<ResponseBase<null>>("/api/v1/settings/notifications", data),

  testEmail: () =>
    client.post<ResponseBase<null>>("/api/v1/settings/notifications/test-email"),

  testWebhook: () =>
    client.post<ResponseBase<null>>("/api/v1/settings/notifications/test-webhook"),

  getParams: () =>
    client.get<ResponseBase<Record<string, string>>>("/api/v1/settings/params"),

  updateParams: (data: Record<string, any>) =>
    client.put<ResponseBase<null>>("/api/v1/settings/params", { params: data }),

  resetParams: () =>
    client.post<ResponseBase<null>>("/api/v1/settings/params/reset"),

  getProfile: () =>
    client.get<ResponseBase<ProfileInfo>>("/api/v1/settings/profile"),

  changePassword: (data: PasswordChangeRequest) =>
    client.put<ResponseBase<null>>("/api/v1/settings/password", data),
};
