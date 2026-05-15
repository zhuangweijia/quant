const TOKEN_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

export const storage = {
  get(key: string, defaultValue: string = ""): string {
    try {
      return localStorage.getItem(key) || defaultValue;
    } catch {
      return defaultValue;
    }
  },

  set(key: string, value: string): void {
    try {
      localStorage.setItem(key, value);
    } catch {
      // ignore
    }
  },

  remove(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch {
      // ignore
    }
  },

  getToken(): string {
    return this.get(TOKEN_KEY);
  },

  setToken(token: string): void {
    this.set(TOKEN_KEY, token);
  },

  getRefreshToken(): string {
    return this.get(REFRESH_KEY);
  },

  setRefreshToken(token: string): void {
    this.set(REFRESH_KEY, token);
  },

  clearAuth(): void {
    this.remove(TOKEN_KEY);
    this.remove(REFRESH_KEY);
  },
};
