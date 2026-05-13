import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { storage } from "@/utils/storage";

const client: AxiosInstance = axios.create({
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = storage.getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
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
    if (error.response?.status === 401) {
      const url = error.config?.url || "";
      if (url.includes("/auth/login") || url.includes("/auth/refresh")) {
        const msg = (error.response?.data as any)?.message || "用户名或密码错误";
        return Promise.reject(new Error(msg));
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
