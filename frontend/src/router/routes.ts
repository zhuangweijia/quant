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
        path: "market",
        name: "Market",
        component: () => import("@/views/market/MarketView.vue"),
        meta: { title: "行情", icon: "TrendCharts" },
      },
      {
        path: "strategy",
        name: "StrategyList",
        component: () => import("@/views/strategy/StrategyListView.vue"),
        meta: { title: "策略", icon: "Setting" },
      },
      {
        path: "strategy/create",
        name: "StrategyCreate",
        component: () => import("@/views/strategy/StrategyEditView.vue"),
        meta: { title: "创建策略", permission: "trade" },
      },
      {
        path: "strategy/:id/edit",
        name: "StrategyEdit",
        component: () => import("@/views/strategy/StrategyEditView.vue"),
        meta: { title: "编辑策略", permission: "trade" },
      },
      {
        path: "backtest",
        name: "Backtest",
        component: () => import("@/views/backtest/BacktestView.vue"),
        meta: { title: "回测", icon: "DataAnalysis", permission: "trade" },
      },
      {
        path: "trade",
        name: "Trade",
        component: () => import("@/views/trade/TradeView.vue"),
        meta: { title: "交易", icon: "Money", permission: "trade" },
      },
      {
        path: "risk",
        name: "Risk",
        component: () => import("@/views/risk/RiskView.vue"),
        meta: { title: "风控", icon: "Shield", permission: "trade" },
      },
      {
        path: "settings",
        name: "Settings",
        component: () => import("@/views/settings/SettingsView.vue"),
        meta: { title: "设置", icon: "Tools", permission: "trade" },
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
