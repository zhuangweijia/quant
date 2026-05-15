import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { storage } from "@/utils/storage";

const client: AxiosInstance = axios.create({
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = storage.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      isRedirecting = false;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

let isRedirecting = false;

client.interceptors.response.use(
  (response) => {
    const { code, message, data } = response.data;
    if (code !== undefined && code !== 0) {
      return Promise.reject(new Error(message || "请求失败"));
    }
    return response.data;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as any;

    if (error.response?.status === 401) {
      const url = originalRequest?.url || "";
      if (url.includes("/auth/login") || url.includes("/auth/refresh")) {
        const msg = (error.response?.data as any)?.message || "用户名或密码错误";
        return Promise.reject(new Error(msg));
      }

      const refreshToken = storage.getRefreshToken();
      if (refreshToken && !originalRequest._retry) {
        originalRequest._retry = true;

        if (!isRefreshing) {
          isRefreshing = true;
          try {
            const res = await axios.post("/api/v1/auth/refresh", {
              refresh_token: refreshToken,
            });
            const newToken = res.data?.data?.access_token;
            const newRefresh = res.data?.data?.refresh_token;
            if (newToken) {
              storage.setToken(newToken);
              if (newRefresh) storage.setRefreshToken(newRefresh);
              onRefreshed(newToken);
              isRefreshing = false;
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              return client(originalRequest);
            }
          } catch {
            isRefreshing = false;
            refreshSubscribers.forEach((cb) => cb(""));
            refreshSubscribers = [];
            storage.clearAuth();
            window.location.href = "/login";
            return Promise.reject(error);
          }
        }

        return new Promise((resolve) => {
          refreshSubscribers.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            resolve(client(originalRequest));
          });
        });
      }

      if (!isRedirecting) {
        isRedirecting = true;
        storage.clearAuth();
        window.location.href = "/login";
      }
    }
    const msg =
      (error.response?.data as any)?.message || error.message || "网络错误";
    return Promise.reject(new Error(msg));
  }
);

export default client;
