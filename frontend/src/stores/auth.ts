import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { authApi } from "@/api/auth";
import { storage } from "@/utils/storage";
import type { UserInfo, LoginRequest } from "@/types/auth";

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref<string>(storage.getToken());
  const refreshToken = ref<string>(storage.getRefreshToken());
  const user = ref<UserInfo | null>(null);

  const isLoggedIn = computed(() => !!accessToken.value);
  const role = computed(() => user.value?.role || "");
  const username = computed(() => user.value?.username || "");

  async function login(credentials: LoginRequest) {
    const res: any = await authApi.login(credentials);
    accessToken.value = res.data.access_token;
    refreshToken.value = res.data.refresh_token;
    storage.setToken(res.data.access_token);
    storage.setRefreshToken(res.data.refresh_token);
    await fetchUser();
  }

  async function fetchUser() {
    const res: any = await authApi.getMe();
    user.value = res.data;
  }

  function logout() {
    accessToken.value = "";
    refreshToken.value = "";
    user.value = null;
    storage.clearAuth();
  }

  async function register(data: { username: string; password: string; confirm_password: string }) {
    const res: any = await authApi.register(data);
    return res;
  }

  return {
    accessToken,
    refreshToken,
    user,
    isLoggedIn,
    role,
    username,
    login,
    fetchUser,
    logout,
    register,
  };
});
