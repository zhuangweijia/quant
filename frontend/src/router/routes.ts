import type { RouteRecordRaw } from "vue-router";
import AppLayout from "@/components/layout/AppLayout.vue";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "Login",
    component: () => import("@/views/login/LoginView.vue"),
    meta: { requiresAuth: false, title: "登录" },
  },
  {
    path: "/",
    component: AppLayout,
    redirect: "/dashboard",
    meta: { requiresAuth: true },
    children: [
      {
        path: "dashboard",
        name: "Dashboard",
        component: () => import("@/views/dashboard/DashboardView.vue"),
        meta: { title: "看板", icon: "Odometer" },
      },
      {
        path: "ranking",
        name: "Ranking",
        component: () => import("@/views/ranking/RankingView.vue"),
        meta: { title: "排名表", icon: "Trophy" },
      },
      {
        path: "stock/:symbol",
        name: "StockDetail",
        component: () => import("@/views/stock-detail/StockDetailView.vue"),
        meta: { title: "个股详情" },
      },
      {
        path: "market",
        name: "Market",
        component: () => import("@/views/market/MarketView.vue"),
        meta: { title: "行情", icon: "TrendCharts" },
      },
      {
        path: "model",
        name: "Model",
        component: () => import("@/views/model/ModelView.vue"),
        meta: { title: "模型", icon: "BrainCircuit" },
      },
      {
        path: "settings",
        name: "Settings",
        component: () => import("@/views/settings/SettingsView.vue"),
        meta: { title: "设置", icon: "Tools" },
      },
    ],
  },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: () => import("@/components/error/NotFound.vue"),
    meta: { requiresAuth: false },
  },
];

export default routes;
