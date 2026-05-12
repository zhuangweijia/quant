import type { Router } from "vue-router";
import { useAuthStore } from "@/stores/auth";

export function setupRouterGuards(router: Router) {
  router.beforeEach((to, _from, next) => {
    const authStore = useAuthStore();

    if (to.meta.requiresAuth !== false && !authStore.isLoggedIn) {
      next({ name: "Login", query: { redirect: to.fullPath } });
      return;
    }

    if (to.meta.permission === "trade" && authStore.role === "viewer") {
      next({ name: "NotFound" });
      return;
    }

    if (to.name === "Login" && authStore.isLoggedIn) {
      next({ name: "Dashboard" });
      return;
    }

    document.title = `${(to.meta.title as string) || "QuantPlatform"} - QuantPlatform`;
    next();
  });
}
