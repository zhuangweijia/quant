# QuantPlatform 前端技术设计文档

> 版本: v1.0  
> 日期: 2026-05-13

---

## 目录

- [1. 技术选型与依赖](#1-技术选型与依赖)
- [2. 项目结构](#2-项目结构)
- [3. 构建配置](#3-构建配置)
- [4. 路由设计](#4-路由设计)
- [5. 状态管理（Pinia）](#5-状态管理pinia)
- [6. API 封装层](#6-api-封装层)
- [7. WebSocket 封装](#7-websocket-封装)
- [8. 页面设计](#8-页面设计)
- [9. 组件设计](#9-组件设计)
- [10. 图表组件（ECharts）](#10-图表组件echarts)
- [11. 权限控制](#11-权限控制)
- [12. 主题与样式](#12-主题与样式)
- [13. 国际化（可选）](#13-国际化可选)
- [14. 性能优化](#14-性能优化)
- [15. 测试策略](#15-测试策略)

---

## 1. 技术选型与依赖

### 1.1 核心框架

| 依赖 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4+ | 前端框架 |
| TypeScript | 5.x | 类型安全 |
| Vite | 5.x | 构建工具 |
| Vue Router | 4.x | 路由管理 |
| Pinia | 2.x | 状态管理 |

### 1.2 UI 与图表

| 依赖 | 版本 | 用途 |
|------|------|------|
| Element Plus | 2.x | UI 组件库 |
| @element-plus/icons-vue | 2.x | 图标库 |
| ECharts | 5.x | 图表库 |
| vue-echarts | 6.x | ECharts Vue 组件封装 |
| echarts-wordcloud | 2.x | 词云图（可选） |

### 1.3 工具库

| 依赖 | 版本 | 用途 |
|------|------|------|
| axios | 1.x | HTTP 客户端 |
| dayjs | 1.x | 日期处理 |
| lodash-es | 4.x | 工具函数（按需引入） |
| nprogress | 0.2 | 页面加载进度条 |
| numeral | 2.x | 数字格式化 |

### 1.4 代码编辑器

| 依赖 | 版本 | 用途 |
|------|------|------|
| monaco-editor | 0.45+ | 代码编辑器（策略编写） |
| @monaco-editor/loader | 1.x | Monaco 加载器 |

### 1.5 开发工具

| 依赖 | 版本 | 用途 |
|------|------|------|
| ESLint | 8.x | 代码检查 |
| Prettier | 3.x | 代码格式化 |
| @vue/eslint-config-typescript | - | Vue + TS ESLint 配置 |
| eslint-plugin-vue | 9.x | Vue 专属规则 |
| sass | 1.x | CSS 预处理器 |
| unplugin-auto-import | - | API 自动导入 |
| unplugin-vue-components | - | 组件自动注册 |

---

## 2. 项目结构

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── env.d.ts
├── .env                          # 环境变量
├── .env.development              # 开发环境
├── .env.production               # 生产环境
├── .eslintrc.cjs
├── .prettierrc.json
├── Dockerfile
├── nginx.conf                    # 生产环境 Nginx 配置
│
├── public/
│   └── favicon.ico
│
└── src/
    ├── main.ts                   # 应用入口
    ├── App.vue                   # 根组件
    ├── env.d.ts                  # 环境变量类型声明
    │
    ├── router/
    │   ├── index.ts              # 路由实例 + 全局守卫
    │   ├── routes.ts             # 路由表定义
    │   └── guards.ts             # 路由守卫逻辑
    │
    ├── stores/                   # Pinia Store
    │   ├── index.ts              # Pinia 实例
    │   ├── auth.ts               # 认证状态
    │   ├── market.ts             # 行情数据
    │   ├── strategy.ts           # 策略管理
    │   ├── backtest.ts           # 回测状态
    │   ├── trade.ts              # 交易状态
    │   ├── risk.ts               # 风控状态
    │   └── dashboard.ts          # 看板数据
    │
    ├── api/                      # API 调用封装
    │   ├── client.ts             # Axios 实例 + 拦截器
    │   ├── auth.ts               # 认证 API
    │   ├── market.ts             # 行情 API
    │   ├── strategy.ts           # 策略 API
    │   ├── backtest.ts           # 回测 API
    │   ├── trade.ts              # 交易 API
    │   ├── risk.ts               # 风控 API
    │   ├── dashboard.ts          # 看板 API
    │   └── settings.ts           # 设置 API
    │
    ├── composables/              # 组合式函数
    │   ├── useWebSocket.ts       # WebSocket 连接管理
    │   ├── useChart.ts           # ECharts 通用逻辑
    │   ├── usePagination.ts      # 分页逻辑
    │   ├── useForm.ts            # 表单逻辑
    │   ├── usePermission.ts      # 权限判断
    │   └── useTheme.ts           # 主题切换
    │
    ├── views/                    # 页面视图
    │   ├── login/
    │   │   └── LoginView.vue
    │   ├── dashboard/
    │   │   ├── DashboardView.vue
    │   │   ├── EquityCurve.vue
    │   │   ├── StrategyRanking.vue
    │   │   ├── PositionPie.vue
    │   │   ├── RecentTrades.vue
    │   │   └── SystemStatus.vue
    │   ├── market/
    │   │   ├── MarketView.vue
    │   │   ├── SymbolSearch.vue
    │   │   └── KlinePanel.vue
    │   ├── strategy/
    │   │   ├── StrategyListView.vue
    │   │   ├── StrategyEditView.vue
    │   │   └── StrategyLogs.vue
    │   ├── backtest/
    │   │   ├── BacktestView.vue
    │   │   ├── BacktestConfig.vue
    │   │   ├── BacktestProgress.vue
    │   │   ├── BacktestReport.vue
    │   │   └── BacktestCompare.vue
    │   ├── trade/
    │   │   ├── TradeView.vue
    │   │   ├── OrderForm.vue
    │   │   ├── PositionTable.vue
    │   │   ├── OrderHistory.vue
    │   │   └── OrderBook.vue
    │   ├── risk/
    │   │   ├── RiskView.vue
    │   │   ├── RuleEditor.vue
    │   │   └── AlertList.vue
    │   └── settings/
    │       ├── SettingsView.vue
    │       ├── ExchangeConfig.vue
    │       ├── NotificationConfig.vue
    │       └── SystemParams.vue
    │
    ├── components/               # 公共组件
    │   ├── layout/
    │   │   ├── AppLayout.vue     # 主布局
    │   │   ├── Sidebar.vue       # 侧边导航
    │   │   ├── Header.vue        # 顶部栏
    │   │   └── Breadcrumb.vue    # 面包屑
    │   ├── charts/
    │   │   ├── KlineChart.vue    # K线图
    │   │   ├── EquityCurveChart.vue  # 权益曲线
    │   │   ├── DrawdownChart.vue     # 回撤曲线
    │   │   ├── PositionPieChart.vue  # 持仓饼图
    │   │   ├── MonthlyHeatmap.vue    # 月度收益热力图
    │   │   └── PnlBarChart.vue       # PnL 柱状图
    │   ├── trade/
    │   │   ├── OrderForm.vue     # 下单表单
    │   │   ├── PositionTable.vue # 持仓表格
    │   │   └── OrderTable.vue    # 订单表格
    │   ├── common/
    │   │   ├── PageContainer.vue # 页面容器
    │   │   ├── StatusTag.vue     # 状态标签
    │   │   ├── MarketTag.vue     # 市场标签
    │   │   ├── NumberDisplay.vue # 数字展示（涨跌色）
    │   │   ├── CodeEditor.vue    # Monaco 编辑器封装
    │   │   ├── ConfirmDialog.vue # 确认对话框
    │   │   └── EmptyState.vue    # 空状态占位
    │   └── error/
    │       ├── NotFound.vue      # 404
    │       └── Forbidden.vue     # 403
    │
    ├── types/                    # TypeScript 类型定义
    │   ├── api.d.ts              # API 响应类型
    │   ├── market.d.ts           # 行情相关类型
    │   ├── strategy.d.ts         # 策略相关类型
    │   ├── trade.d.ts            # 交易相关类型
    │   ├── risk.d.ts             # 风控相关类型
    │   ├── dashboard.d.ts        # 看板相关类型
    │   └── common.d.ts           # 通用类型
    │
    ├── styles/                   # 全局样式
    │   ├── variables.scss        # SCSS 变量
    │   ├── reset.scss            # 样式重置
    │   ├── global.scss           # 全局样式
    │   ├── element-override.scss # Element Plus 覆盖
    │   ├── themes/
    │   │   ├── light.scss        # 亮色主题
    │   │   └── dark.scss         # 暗色主题
    │   └── mixins.scss           # SCSS Mixins
    │
    └── utils/                    # 工具函数
        ├── format.ts             # 格式化（数字、日期、百分比）
        ├── validate.ts           # 校验规则
        ├── storage.ts            # localStorage 封装
        └── constants.ts          # 常量定义
```

---

## 3. 构建配置

### 3.1 vite.config.ts

```typescript
import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());

  return {
    plugins: [
      vue(),
      AutoImport({
        imports: ["vue", "vue-router", "pinia"],
        resolvers: [ElementPlusResolver()],
        dts: "src/auto-imports.d.ts",
      }),
      Components({
        resolvers: [ElementPlusResolver()],
        dts: "src/components.d.ts",
      }),
    ],
    resolve: {
      alias: {
        "@": resolve(__dirname, "src"),
      },
    },
    server: {
      port: 3000,
      proxy: {
        "/api": {
          target: env.VITE_API_BASE_URL || "http://localhost:8000",
          changeOrigin: true,
        },
        "/ws": {
          target: env.VITE_WS_URL || "ws://localhost:8000",
          ws: true,
        },
      },
    },
    build: {
      target: "es2020",
      outDir: "dist",
      sourcemap: false,
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          manualChunks: {
            vue: ["vue", "vue-router", "pinia"],
            elementPlus: ["element-plus"],
            echarts: ["echarts", "vue-echarts"],
            monaco: ["monaco-editor"],
          },
        },
      },
    },
  };
});
```

### 3.2 环境变量

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000

# .env.production
VITE_API_BASE_URL=/
VITE_WS_URL=wss://your-domain.com
```

### 3.3 TypeScript 配置

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "noEmit": true,
    "paths": {
      "@/*": ["./src/*"]
    },
    "types": ["vite/client"]
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.vue", "env.d.ts"]
}
```

---

## 4. 路由设计

### 4.1 路由表

```typescript
// src/router/routes.ts
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
        meta: { title: "行情", icon: "TrendCharts", permission: "view" },
      },
      {
        path: "strategy",
        name: "Strategy",
        redirect: "/strategy/list",
        meta: { title: "策略", icon: "Setting" },
        children: [
          {
            path: "list",
            name: "StrategyList",
            component: () => import("@/views/strategy/StrategyListView.vue"),
            meta: { title: "策略列表" },
          },
          {
            path: "create",
            name: "StrategyCreate",
            component: () => import("@/views/strategy/StrategyEditView.vue"),
            meta: { title: "创建策略", permission: "trade" },
          },
          {
            path: ":id/edit",
            name: "StrategyEdit",
            component: () => import("@/views/strategy/StrategyEditView.vue"),
            meta: { title: "编辑策略", permission: "trade" },
          },
          {
            path: ":id/logs",
            name: "StrategyLogs",
            component: () => import("@/views/strategy/StrategyLogs.vue"),
            meta: { title: "策略日志" },
          },
        ],
      },
      {
        path: "backtest",
        name: "Backtest",
        redirect: "/backtest/index",
        meta: { title: "回测", icon: "DataAnalysis" },
        children: [
          {
            path: "index",
            name: "BacktestIndex",
            component: () => import("@/views/backtest/BacktestView.vue"),
            meta: { title: "回测中心", permission: "trade" },
          },
          {
            path: "result/:id",
            name: "BacktestResult",
            component: () => import("@/views/backtest/BacktestReport.vue"),
            meta: { title: "回测报告" },
          },
          {
            path: "compare",
            name: "BacktestCompare",
            component: () => import("@/views/backtest/BacktestCompare.vue"),
            meta: { title: "回测对比" },
          },
        ],
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
        redirect: "/risk/rules",
        meta: { title: "风控", icon: "Shield" },
        children: [
          {
            path: "rules",
            name: "RiskRules",
            component: () => import("@/views/risk/RiskView.vue"),
            meta: { title: "风控规则", permission: "trade" },
          },
          {
            path: "alerts",
            name: "RiskAlerts",
            component: () => import("@/views/risk/AlertList.vue"),
            meta: { title: "告警记录" },
          },
        ],
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
    path: "/403",
    name: "Forbidden",
    component: () => import("@/components/error/Forbidden.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/:pathMatch(.*)*",
    name: "NotFound",
    component: () => import("@/components/error/NotFound.vue"),
    meta: { requiresAuth: false },
  },
];

export default routes;
```

### 4.2 路由守卫

```typescript
// src/router/guards.ts
import type { Router } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import NProgress from "nprogress";

export function setupRouterGuards(router: Router) {
  router.beforeEach((to, _from, next) => {
    NProgress.start();

    const authStore = useAuthStore();

    if (to.meta.requiresAuth !== false && !authStore.isLoggedIn) {
      next({ name: "Login", query: { redirect: to.fullPath } });
      return;
    }

    if (to.meta.permission === "trade" && authStore.role === "viewer") {
      next({ name: "Forbidden" });
      return;
    }

    if (to.name === "Login" && authStore.isLoggedIn) {
      next({ name: "Dashboard" });
      return;
    }

    document.title = `${to.meta.title || "QuantPlatform"} - QuantPlatform`;
    next();
  });

  router.afterEach(() => {
    NProgress.done();
  });
}
```

### 4.3 路由实例

```typescript
// src/router/index.ts
import { createRouter, createWebHistory } from "vue-router";
import routes from "./routes";
import { setupRouterGuards } from "./guards";

const router = createRouter({
  history: createWebHistory(),
  routes,
});

setupRouterGuards(router);

export default router;
```

---

## 5. 状态管理（Pinia）

### 5.1 Auth Store

```typescript
// src/stores/auth.ts
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { authApi } from "@/api/auth";
import { storage } from "@/utils/storage";

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref<string>(storage.get("access_token", ""));
  const refreshToken = ref<string>(storage.get("refresh_token", ""));
  const user = ref<UserInfo | null>(null);

  const isLoggedIn = computed(() => !!accessToken.value);
  const role = computed(() => user.value?.role || "");
  const username = computed(() => user.value?.username || "");

  async function login(credentials: LoginRequest) {
    const res = await authApi.login(credentials);
    accessToken.value = res.data.access_token;
    refreshToken.value = res.data.refresh_token;
    storage.set("access_token", res.data.access_token);
    storage.set("refresh_token", res.data.refresh_token);
    await fetchUser();
  }

  async function fetchUser() {
    const res = await authApi.getMe();
    user.value = res.data;
  }

  async function logout() {
    accessToken.value = "";
    refreshToken.value = "";
    user.value = null;
    storage.remove("access_token");
    storage.remove("refresh_token");
  }

  async function refreshAccessToken() {
    const res = await authApi.refresh(refreshToken.value);
    accessToken.value = res.data.access_token;
    storage.set("access_token", res.data.access_token);
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
    refreshAccessToken,
  };
});
```

### 5.2 Market Store

```typescript
// src/stores/market.ts
import { defineStore } from "pinia";
import { ref } from "vue";
import { marketApi } from "@/api/market";

export const useMarketStore = defineStore("market", () => {
  const watchedSymbols = ref<WatchedSymbol[]>([]);
  const tickData = ref<Record<string, TickData>>({});
  const searchResults = ref<SymbolInfo[]>([]);

  async function searchSymbols(keyword: string, market?: string) {
    const res = await marketApi.searchSymbols(keyword, market);
    searchResults.value = res.data;
  }

  async function fetchKlines(params: KlineRequest) {
    const res = await marketApi.getKlines(params);
    return res.data;
  }

  function updateTick(symbol: string, data: TickData) {
    tickData.value[symbol] = data;
  }

  return {
    watchedSymbols,
    tickData,
    searchResults,
    searchSymbols,
    fetchKlines,
    updateTick,
  };
});
```

### 5.3 Strategy Store

```typescript
// src/stores/strategy.ts
import { defineStore } from "pinia";
import { ref } from "vue";
import { strategyApi } from "@/api/strategy";

export const useStrategyStore = defineStore("strategy", () => {
  const strategies = ref<StrategyListItem[]>([]);
  const currentStrategy = ref<StrategyDetail | null>(null);
  const pagination = ref({ total: 0, page: 1, pageSize: 20 });

  async function fetchStrategies(params?: StrategyListParams) {
    const res = await strategyApi.list(params);
    strategies.value = res.data.items;
    pagination.value.total = res.data.total;
    pagination.value.page = res.data.page;
  }

  async function createStrategy(data: StrategyCreateRequest) {
    await strategyApi.create(data);
    await fetchStrategies();
  }

  async function updateStrategy(id: string, data: StrategyUpdateRequest) {
    await strategyApi.update(id, data);
  }

  async function deleteStrategy(id: string) {
    await strategyApi.remove(id);
    await fetchStrategies();
  }

  async function startStrategy(id: string) {
    await strategyApi.start(id);
    await fetchStrategies();
  }

  async function stopStrategy(id: string) {
    await strategyApi.stop(id);
    await fetchStrategies();
  }

  async function fetchStrategyDetail(id: string) {
    const res = await strategyApi.get(id);
    currentStrategy.value = res.data;
  }

  return {
    strategies,
    currentStrategy,
    pagination,
    fetchStrategies,
    createStrategy,
    updateStrategy,
    deleteStrategy,
    startStrategy,
    stopStrategy,
    fetchStrategyDetail,
  };
});
```

### 5.4 Trade Store

```typescript
// src/stores/trade.ts
import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { tradeApi } from "@/api/trade";

export const useTradeStore = defineStore("trade", () => {
  const positions = ref<Position[]>([]);
  const orders = ref<Order[]>([]);
  const account = ref<AccountInfo>({
    cash: 0,
    equity: 0,
    buying_power: 0,
    daily_pnl: 0,
    total_pnl: 0,
  });

  const totalPositionValue = computed(() =>
    positions.value.reduce((sum, p) => sum + p.market_value, 0)
  );

  const unrealizedPnl = computed(() =>
    positions.value.reduce((sum, p) => sum + p.unrealized_pnl, 0)
  );

  async function fetchPositions() {
    const res = await tradeApi.getPositions();
    positions.value = res.data;
  }

  async function fetchOrders(params?: OrderListParams) {
    const res = await tradeApi.getOrders(params);
    orders.value = res.data.items;
  }

  async function submitOrder(data: OrderRequest) {
    await tradeApi.submitOrder(data);
    await fetchPositions();
  }

  async function cancelOrder(orderId: string) {
    await tradeApi.cancelOrder(orderId);
    await fetchOrders();
  }

  function updatePositionFromWs(data: PositionUpdate) {
    const idx = positions.value.findIndex((p) => p.symbol === data.symbol);
    if (idx >= 0) {
      positions.value[idx] = { ...positions.value[idx], ...data };
    }
  }

  function updateOrderFromWs(data: OrderUpdate) {
    const idx = orders.value.findIndex((o) => o.id === data.order_id);
    if (idx >= 0) {
      orders.value[idx] = { ...orders.value[idx], ...data };
    }
  }

  return {
    positions,
    orders,
    account,
    totalPositionValue,
    unrealizedPnl,
    fetchPositions,
    fetchOrders,
    submitOrder,
    cancelOrder,
    updatePositionFromWs,
    updateOrderFromWs,
  };
});
```

### 5.5 Backtest Store

```typescript
// src/stores/backtest.ts
import { defineStore } from "pinia";
import { ref } from "vue";
import { backtestApi } from "@/api/backtest";

export const useBacktestStore = defineStore("backtest", () => {
  const results = ref<BacktestResultListItem[]>([]);
  const currentResult = ref<BacktestResultDetail | null>(null);
  const isRunning = ref(false);
  const progress = ref(0);
  const compareIds = ref<string[]>([]);

  async function runBacktest(params: BacktestRunRequest) {
    isRunning.value = true;
    progress.value = 0;
    try {
      const res = await backtestApi.run(params);
      currentResult.value = res.data;
    } finally {
      isRunning.value = false;
    }
  }

  function updateProgress(data: { progress: number; status: string }) {
    progress.value = data.progress;
    if (data.status === "completed" || data.status === "failed") {
      isRunning.value = false;
    }
  }

  async function fetchResults(params?: BacktestListParams) {
    const res = await backtestApi.getResults(params);
    results.value = res.data.items;
  }

  async function fetchResultDetail(id: string) {
    const res = await backtestApi.getResult(id);
    currentResult.value = res.data;
  }

  function toggleCompare(id: string) {
    const idx = compareIds.value.indexOf(id);
    if (idx >= 0) {
      compareIds.value.splice(idx, 1);
    } else if (compareIds.value.length < 5) {
      compareIds.value.push(id);
    }
  }

  return {
    results,
    currentResult,
    isRunning,
    progress,
    compareIds,
    runBacktest,
    updateProgress,
    fetchResults,
    fetchResultDetail,
    toggleCompare,
  };
});
```

### 5.6 Dashboard Store

```typescript
// src/stores/dashboard.ts
import { defineStore } from "pinia";
import { ref } from "vue";
import { dashboardApi } from "@/api/dashboard";

export const useDashboardStore = defineStore("dashboard", () => {
  const overview = ref<DashboardOverview | null>(null);
  const equityCurve = ref<EquityCurvePoint[]>([]);
  const strategyRanking = ref<StrategyRankItem[]>([]);

  async function fetchOverview() {
    const res = await dashboardApi.getOverview();
    overview.value = res.data;
  }

  async function fetchEquityCurve(range: string = "1M") {
    const res = await dashboardApi.getEquityCurve(range);
    equityCurve.value = res.data;
  }

  async function fetchStrategyRanking() {
    const res = await dashboardApi.getStrategyRanking();
    strategyRanking.value = res.data;
  }

  return { overview, equityCurve, strategyRanking, fetchOverview, fetchEquityCurve, fetchStrategyRanking };
});
```

---

## 6. API 封装层

### 6.1 Axios 实例

```typescript
// src/api/client.ts
import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/stores/auth";
import { ElMessage } from "element-plus";

const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// 请求拦截器
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore();
    if (authStore.accessToken) {
      config.headers.Authorization = `Bearer ${authStore.accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器
client.interceptors.response.use(
  (response) => {
    const { code, message, data } = response.data;
    if (code !== 0) {
      ElMessage.error(message || "请求失败");
      return Promise.reject(new Error(message));
    }
    return response.data;
  },
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore();
      try {
        await authStore.refreshAccessToken();
        return client.request(error.config!);
      } catch {
        authStore.logout();
        window.location.href = "/login";
      }
    }
    const msg = error.response?.data?.message || error.message || "网络错误";
    ElMessage.error(msg);
    return Promise.reject(error);
  }
);

export default client;
```

### 6.2 API 模块示例

```typescript
// src/api/strategy.ts
import client from "./client";
import type {
  StrategyCreateRequest,
  StrategyUpdateRequest,
  StrategyListParams,
  StrategyDetail,
  StrategyListItem,
} from "@/types/strategy";
import type { PageResponse, ResponseBase } from "@/types/common";

export const strategyApi = {
  list: (params?: StrategyListParams) =>
    client.get<ResponseBase<PageResponse<StrategyListItem>>>("/api/v1/strategies", { params }),

  get: (id: string) =>
    client.get<ResponseBase<StrategyDetail>>(`/api/v1/strategies/${id}`),

  create: (data: StrategyCreateRequest) =>
    client.post<ResponseBase<StrategyDetail>>("/api/v1/strategies", data),

  update: (id: string, data: StrategyUpdateRequest) =>
    client.put<ResponseBase<StrategyDetail>>(`/api/v1/strategies/${id}`, data),

  remove: (id: string) =>
    client.delete<ResponseBase<null>>(`/api/v1/strategies/${id}`),

  start: (id: string) =>
    client.post<ResponseBase<null>>(`/api/v1/strategies/${id}/start`),

  stop: (id: string) =>
    client.post<ResponseBase<null>>(`/api/v1/strategies/${id}/stop`),

  getLogs: (id: string, params?: { page?: number; page_size?: number; level?: string }) =>
    client.get<ResponseBase<PageResponse<StrategyLogItem>>>(`/api/v1/strategies/${id}/logs`, { params }),
};
```

```typescript
// src/api/trade.ts
import client from "./client";
import type { OrderRequest, Order, Position, OrderListParams } from "@/types/trade";
import type { PageResponse, ResponseBase } from "@/types/common";

export const tradeApi = {
  submitOrder: (data: OrderRequest) =>
    client.post<ResponseBase<Order>>("/api/v1/trade/order", data),

  cancelOrder: (orderId: string) =>
    client.delete<ResponseBase<null>>(`/api/v1/trade/order/${orderId}`),

  getOrders: (params?: OrderListParams) =>
    client.get<ResponseBase<PageResponse<Order>>>("/api/v1/trade/orders", { params }),

  getPositions: () =>
    client.get<ResponseBase<Position[]>>("/api/v1/trade/positions"),
};
```

---

## 7. WebSocket 封装

### 7.1 WebSocket 管理器

```typescript
// src/composables/useWebSocket.ts
import { ref, onUnmounted } from "vue";
import { useAuthStore } from "@/stores/auth";

interface WsOptions {
  url: string;
  onMessage?: (data: any) => void;
  onOpen?: () => void;
  onClose?: () => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket(options: WsOptions) {
  const {
    url,
    onMessage,
    onOpen,
    onClose,
    reconnect = true,
    reconnectInterval = 5000,
    maxReconnectAttempts = 10,
  } = options;

  const authStore = useAuthStore();
  const connected = ref(false);
  const reconnectAttempts = ref(0);

  let ws: WebSocket | null = null;
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;

  function connect() {
    const wsUrl = `${url}?token=${authStore.accessToken}`;
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      connected.value = true;
      reconnectAttempts.value = 0;
      startHeartbeat();
      onOpen?.();
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch {
        // ignore
      }
    };

    ws.onclose = () => {
      connected.value = false;
      stopHeartbeat();
      onClose?.();
      if (reconnect && reconnectAttempts.value < maxReconnectAttempts) {
        reconnectAttempts.value++;
        setTimeout(connect, reconnectInterval);
      }
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  function send(data: object) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }

  function startHeartbeat() {
    heartbeatTimer = setInterval(() => {
      send({ type: "ping" });
    }, 30000);
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  function disconnect() {
    reconnectAttempts.value = maxReconnectAttempts; // prevent reconnect
    stopHeartbeat();
    ws?.close();
    ws = null;
  }

  onUnmounted(() => {
    disconnect();
  });

  return { connected, connect, disconnect, send };
}
```

### 7.2 WebSocket 使用示例

```typescript
// 在 App.vue 或 AppLayout.vue 中初始化
const { connect: connectMarket, send: sendMarket } = useWebSocket({
  url: `${wsBaseUrl}/ws/market`,
  onMessage: (data) => {
    if (data.type === "tick") {
      marketStore.updateTick(data.data.symbol, data.data);
    }
  },
});

const { connect: connectTrade } = useWebSocket({
  url: `${wsBaseUrl}/ws/trade`,
  onMessage: (data) => {
    if (data.type === "order_update") {
      tradeStore.updateOrderFromWs(data.data);
    } else if (data.type === "risk_alert") {
      riskStore.addAlert(data.data);
      ElNotification({
        title: data.data.title,
        message: data.data.message,
        type: data.data.level === "error" ? "error" : "warning",
      });
    } else if (data.type === "backtest_progress") {
      backtestStore.updateProgress(data.data);
    }
  },
});

// 登录后连接
watch(() => authStore.isLoggedIn, (val) => {
  if (val) {
    connectMarket();
    connectTrade();
  }
});
```

---

## 8. 页面设计

### 8.1 登录页 LoginView.vue

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│              ┌─────────────────────┐                 │
│              │   QuantPlatform     │                 │
│              │   ─────────────     │                 │
│              │                     │                 │
│              │  ┌───────────────┐  │                 │
│              │  │ 用户名         │  │                 │
│              │  └───────────────┘  │                 │
│              │  ┌───────────────┐  │                 │
│              │  │ 密码           │  │                 │
│              │  └───────────────┘  │                 │
│              │                     │                 │
│              │  ┌───────────────┐  │                 │
│              │  │    登  录     │  │                 │
│              │  └───────────────┘  │                 │
│              │                     │                 │
│              └─────────────────────┘                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### 8.2 Dashboard 页面布局

```
┌─────────────────────────────────────────────────────────────────┐
│ Header: QuantPlatform  |  搜索  |  🔔 告警(3)  |  用户名 ▼     │
├────────┬────────────────────────────────────────────────────────┤
│        │  Dashboard                                               │
│ 侧边栏  │                                                         │
│        │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│ ▸ 看板  │  │ 总资产    │ │ 日盈亏    │ │ 总盈亏    │ │ 运行策略  │  │
│ ▸ 行情  │  │ ¥1,234,567│ │ +¥12,345 │ │ +¥234,567│ │ 3/10     │  │
│ ▸ 策略  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│ ▸ 回测  │                                                         │
│ ▸ 交易  │  ┌────────────────────────┬───────────────────────┐   │
│ ▸ 风控  │  │                        │                       │   │
│ ▸ 设置  │  │   权益曲线 (ECharts)    │   持仓分布 (饼图)      │   │
│        │  │                        │                       │   │
│        │  │                        │                       │   │
│        │  └────────────────────────┴───────────────────────┘   │
│        │                                                         │
│        │  ┌────────────────────────┬───────────────────────┐   │
│        │  │  策略表现排名            │  最近交易              │   │
│        │  │  ┌──┬────┬───┬───┬──┐  │  ┌──┬──┬──┬──┬──┬──┐  │   │
│        │  │  │名│策略 │收益│夏普│回撤│ │  │时│标的│方│价│量│盈│  │   │
│        │  │  └──┴────┴───┴───┴──┘  │  └──┴──┴──┴──┴──┴──┘  │   │
│        │  └────────────────────────┴───────────────────────┘   │
└────────┴────────────────────────────────────────────────────────┘
```

### 8.3 行情页 MarketView.vue

```
┌────────────────────────────────────────────────────────────┐
│  行情监控                                                   │
│                                                             │
│  ┌──────────────────────────────────────┐  ┌────────────┐  │
│  │  搜索标的: [________________] 🔍      │  │ 我的关注    │  │
│  │  筛选: [A股] [美股] [加密货币]         │  │ BTCUSDT ★  │  │
│  │                                       │  │ AAPL     ★  │  │
│  │  ┌──────┬───────┬──────┬──────┐      │  │ 600519   ★  │  │
│  │  │ 代码  │ 名称   │ 最新价 │ 涨跌幅│      │  │            │  │
│  │  ├──────┼───────┼──────┼──────┤      │  │            │  │
│  │  │600519│贵州茅台│1856.0│+2.3%│      │  │            │  │
│  │  │AAPL  │苹果    │189.45│-0.5%│      │  │            │  │
│  │  │BTC.. │比特币  │62345 │+3.2%│      │  │            │  │
│  │  └──────┴───────┴──────┴──────┘      │  └────────────┘  │
│  └──────────────────────────────────────┘                   │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  BTCUSDT - 加密货币 - 1D                               │  │
│  │  ┌────────────────────────────────────────────────┐  │  │
│  │  │                                                  │  │  │
│  │  │            K线图 (ECharts Candlestick)            │  │  │
│  │  │                                                  │  │  │
│  │  │  MA5 ─── MA10 ─── MA20 ───                       │  │  │
│  │  │                                                  │  │  │
│  │  │  ┌──────────────────────────────────────────┐   │  │  │
│  │  │  │         成交量 (Volume Bar)                │   │  │  │
│  │  │  └──────────────────────────────────────────┘   │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │  周期: [1m] [5m] [15m] [1h] [4h] [1D] [1W]         │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### 8.4 策略编辑页 StrategyEditView.vue

```
┌──────────────────────────────────────────────────────────────┐
│  创建策略 / 编辑策略                                          │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ 基本信息                                              │    │
│  │  策略名称: [________________________]                  │    │
│  │  目标市场: [A股 ▼]                                     │    │
│  │  策略描述: [________________________]                  │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ 策略代码                                    Python ▼  │    │
│  │  ┌──────────────────────────────────────────────────┐│    │
│  │  │  import numpy as np                               ││    │
│  │  │  from app.core.types import BaseStrategy, BarData ││    │
│  │  │                                                    ││    │
│  │  │  class MACrossStrategy(BaseStrategy):              ││    │
│  │  │      def on_init(self, ctx):                       ││    │
│  │  │          self.short_period = self.params.get(5)    ││    │
│  │  │          self.long_period = self.params.get(20)    ││    │
│  │  │                                                    ││    │
│  │  │      def on_bar(self, bar: BarData):               ││    │
│  │  │          bars = self.get_bars(bar.symbol, 30)      ││    │
│  │  │          # ... 策略逻辑                             ││    │
│  │  │          ┌─── Monaco Editor ───┐                   ││    │
│  │  │          │                     │                   ││    │
│  │  │          │                     │                   ││    │
│  │  │          └─────────────────────┘                   ││    │
│  │  └──────────────────────────────────────────────────┘│    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ 策略参数 (JSON)                                       │    │
│  │  ┌──────────────────────────────────────────────────┐│    │
│  │  │  {                                                ││    │
│  │  │    "short_period": 5,                             ││    │
│  │  │    "long_period": 20                              ││    │
│  │  │  }                                                ││    │
│  │  └──────────────────────────────────────────────────┘│    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  [验证代码]  [保存草稿]  [保存并回测]                          │
└──────────────────────────────────────────────────────────────┘
```

### 8.5 回测报告页 BacktestReport.vue

```
┌──────────────────────────────────────────────────────────────────┐
│  回测报告 - MA Cross Strategy                                     │
│                                                                   │
│  ┌───────────┬───────────┬───────────┬───────────┬──────────┐   │
│  │ 总收益率    │ 年化收益率  │ 夏普比率   │ 最大回撤   │ 胜率      │   │
│  │ +45.67%   │ +23.45%   │ 1.82      │ -12.34%   │ 58.3%    │   │
│  └───────────┴───────────┴───────────┴───────────┴──────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  权益曲线                                                 │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  —— 策略权益    —— 基准                           │   │   │
│  │  │         ___                                      │   │   │
│  │  │       _/   \___                                  │   │   │
│  │  │     _/         \____                             │   │   │
│  │  │  __/                \______                      │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  回撤曲线                                                 │   │
│  │  ┌──────────────────────────────────────────────────┐   │   │
│  │  │  ▼▼▼▼                                              │   │   │
│  │  │     ▼▼▼▼▼                                         │   │   │
│  │  └──────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  月度收益热力图                                            │   │
│  │        1月   2月   3月   4月   5月  ...  12月              │   │
│  │  2024  +2.1  +1.5  -0.8  +3.2  +1.1  ...  +2.3           │   │
│  │  2025  +0.5  +3.1  +1.2  -1.1  ...                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  交易明细                               导出CSV          │   │
│  │  ┌──┬──────┬────┬────┬─────┬─────┬─────┬─────┬────┐   │   │
│  │  │ #│ 时间  │标的 │方向 │ 开仓价│平仓价│数量  │盈亏  │持期│   │   │
│  │  ├──┼──────┼────┼────┼─────┼─────┼─────┼─────┼────┤   │   │
│  │  │ 1│ 01-15│BTC │买入 │58000│60200│ 0.5 │+$1100│ 3d │   │   │
│  │  │ 2│ 01-20│ETH │卖出 │3200 │3050 │ 5.0 │ +$750│ 1d │   │   │
│  │  └──┴──────┴────┴────┴─────┴─────┴─────┴─────┴────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 8.6 交易页 TradeView.vue

```
┌──────────────────────────────────────────────────────────────────┐
│  交易                                                            │
│                                                                   │
│  ┌─────────────────────────┐  ┌────────────────────────────────┐│
│  │ 账户信息                  │  │ 下单                            ││
│  │                           │  │                                 ││
│  │ 总资产: ¥1,234,567.00    │  │ 标的: [BTCUSDT___] 🔍          ││
│  │ 可用:   ¥856,789.00      │  │ 市场: [加密货币 ▼]              ││
│  │ 持仓值: ¥377,778.00      │  │ 类型: [市价] [限价] [止损]      ││
│  │ 日盈亏: +¥12,345.00      │  │ 方向: [买入] [卖出]             ││
│  │                           │  │ 数量: [___________]             ││
│  │ 模式: 🟢 模拟盘           │  │ 价格: [___________] (限价)      ││
│  └─────────────────────────┘  │ 预估金额: ¥62,345.00            ││
│                                │                                 ││
│                                │ [确认下单]                       ││
│                                └────────────────────────────────┘│
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  当前持仓                                                  │   │
│  │  ┌──────┬──────┬─────┬──────┬──────┬──────┬──────┐      │   │
│  │  │ 标的  │ 市场  │ 数量 │ 均价  │ 现价  │ 盈亏  │盈亏% │      │   │
│  │  ├──────┼──────┼─────┼──────┼──────┼──────┼──────┤      │   │
│  │  │BTCUSDT│加密货币│ 0.5 │58000 │62345 │+¥2,172│+3.7%│      │   │
│  │  │AAPL   │美股   │ 100 │178.50│189.45│+$1,095│+6.1%│      │   │
│  │  └──────┴──────┴─────┴──────┴──────┴──────┴──────┘      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  订单历史                                                  │   │
│  │  ┌──────┬──────┬─────┬─────┬──────┬──────┬──────┐       │   │
│  │  │ 时间  │ 标的  │方向 │ 类型 │ 价格  │ 数量  │ 状态  │       │   │
│  │  ├──────┼──────┼─────┼─────┼──────┼──────┼──────┤       │   │
│  │  │10:30 │BTC   │买入 │市价  │62345 │ 0.5  │已成交│       │   │
│  │  │10:25 │ETH   │卖出 │限价  │3200  │ 3.0  │已成交│       │   │
│  │  └──────┴──────┴─────┴─────┴──────┴──────┴──────┘       │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 8.7 风控页 RiskView.vue

```
┌──────────────────────────────────────────────────────────────┐
│  风控管理                                                     │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  风控规则                              [+ 添加规则]       ││
│  │                                                           ││
│  │  ┌─────────────────────────────────────────────────┐    ││
│  │  │ 📌 全局规则                                      │    ││
│  │  │  ├── 日亏损限额    ¥50,000/天          [开] [✏] [🗑] ││
│  │  │  ├── 日交易次数    50次/天              [开] [✏] [🗑] ││
│  │  │  ├── 单笔最大金额  ¥100,000            [开] [✏] [🗑] ││
│  │  │  └── 黑名单        无                   [开] [✏] [🗑] ││
│  │  └─────────────────────────────────────────────────┘    ││
│  │                                                           ││
│  │  ┌─────────────────────────────────────────────────┐    ││
│  │  │ 📌 MA Cross Strategy                            │    ││
│  │  │  ├── 止损线      -10%                  [开] [✏] [🗑] ││
│  │  │  ├── 止盈线      +30%                  [开] [✏] [🗑] ││
│  │  │  └── 最大仓位    总资产的30%            [开] [✏] [🗑] ││
│  │  └─────────────────────────────────────────────────┘    ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  告警记录                              [全部标为已读]      ││
│  │  ┌──────┬──────┬────────────────────────┬──────┐        ││
│  │  │ 时间  │ 级别  │ 消息                    │ 状态  │        ││
│  │  ├──────┼──────┼────────────────────────┼──────┤        ││
│  │  │10:30 │ ⚠ 警告│ BTCUSDT 浮亏达 -8.5%    │ 未读  │        ││
│  │  │09:15 │ ℹ 信息│ MA Cross 策略已启动      │ 已读  │        ││
│  │  │09:00 │ ❌ 错误│ 日亏损限额已触发，停止交易│ 已读  │        ││
│  │  └──────┴──────┴────────────────────────┴──────┘        ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 8.8 设置页 SettingsView.vue

```
┌──────────────────────────────────────────────────────────────┐
│  系统设置                                                     │
│                                                               │
│  [交易所配置] [通知配置] [系统参数]                             │
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  交易所 API 配置                                          ││
│  │                                                           ││
│  │  Binance (加密货币)                              [已连接 ●] ││
│  │  API Key:    [abcd****efgh]          [测试连接]            ││
│  │  API Secret: [••••••••••••••]         [显示]               ││
│  │  网络:      [主网 ▼]                                    ││
│  │                                                           ││
│  │  Alpaca (美股)                                    [未连接 ○] ││
│  │  API Key:    [APCK****WXYZ]          [测试连接]            ││
│  │  API Secret: [••••••••••••••]         [显示]               ││
│  │  环境:      [模拟盘 ▼]                                  ││
│  │                                                           ││
│  │  交易模式:  [⚪ 模拟盘]  [⚪ 实盘]                        ││
│  │                                                           ││
│  │  [保存配置]                                               ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

---

## 9. 组件设计

### 9.1 布局组件

#### AppLayout.vue

```
┌─────────────────────────────────────────────────────────┐
│  Header (64px)                                          │
├─────────┬───────────────────────────────────────────────┤
│         │                                               │
│ Sidebar │                                               │
│ (220px) │              <router-view />                  │
│         │                                               │
│         │                                               │
│         │                                               │
│         │                                               │
│         │                                               │
└─────────┴───────────────────────────────────────────────┘
```

- Sidebar 可折叠，折叠后只显示图标（64px）
- Header 包含：Logo、搜索框、告警铃铛、主题切换、用户下拉菜单
- 支持暗色/亮色主题切换

#### Sidebar.vue

```vue
<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { usePermission } from "@/composables/usePermission";

const { hasPermission } = usePermission();
const isCollapsed = ref(false);

const menuItems = computed(() =>
  [
    { title: "看板", icon: "Odometer", path: "/dashboard", permission: null },
    { title: "行情", icon: "TrendCharts", path: "/market", permission: "view" },
    { title: "策略", icon: "Setting", path: "/strategy/list", permission: "view" },
    { title: "回测", icon: "DataAnalysis", path: "/backtest/index", permission: "trade" },
    { title: "交易", icon: "Money", path: "/trade", permission: "trade" },
    { title: "风控", icon: "Shield", path: "/risk/rules", permission: "trade" },
    { title: "设置", icon: "Tools", path: "/settings", permission: "trade" },
  ].filter((item) => !item.permission || hasPermission(item.permission))
);
</script>

<template>
  <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
    <el-menu
      :default-active="$route.path"
      :collapse="isCollapsed"
      router
    >
      <el-menu-item
        v-for="item in menuItems"
        :key="item.path"
        :index="item.path"
      >
        <el-icon><component :is="item.icon" /></el-icon>
        <template #title>{{ item.title }}</template>
      </el-menu-item>
    </el-menu>
  </el-aside>
</template>
```

### 9.2 通用组件

#### StatusTag.vue

```vue
<script setup lang="ts">
const statusMap: Record<string, { type: string; label: string }> = {
  draft: { type: "info", label: "草稿" },
  running: { type: "success", label: "运行中" },
  stopped: { type: "warning", label: "已停止" },
  pending: { type: "info", label: "待成交" },
  filled: { type: "success", label: "已成交" },
  cancelled: { type: "danger", label: "已撤单" },
  rejected: { type: "danger", label: "已拒绝" },
  partial_filled: { type: "warning", label: "部分成交" },
};

defineProps<{ status: string }>();
</script>

<template>
  <el-tag :type="statusMap[status]?.type || 'info'" size="small">
    {{ statusMap[status]?.label || status }}
  </el-tag>
</template>
```

#### NumberDisplay.vue

```vue
<script setup lang="ts">
import { computed } from "vue";
import numeral from "numeral";

const props = defineProps<{
  value: number;
  format?: string;
  prefix?: string;
  suffix?: string;
}>();

const displayValue = computed(() => {
  const fmt = props.format || "0,0.00";
  return numeral(props.value).format(fmt);
});

const isPositive = computed(() => props.value > 0);
const isNegative = computed(() => props.value < 0);
</script>

<template>
  <span
    :class="{
      'number-up': isPositive,
      'number-down': isNegative,
    }"
  >
    {{ prefix }}{{ displayValue }}{{ isPositive ? " ↑" : isNegative ? " ↓" : "" }}{{ suffix }}
  </span>
</template>

<style scoped>
.number-up { color: var(--el-color-danger); }
.number-down { color: var(--el-color-success); }
</style>
```

#### CodeEditor.vue

```vue
<script setup lang="ts">
import { ref, onMounted, shallowRef } from "vue";
import * as monaco from "monaco-editor";

const props = defineProps<{
  modelValue: string;
  language?: string;
  readOnly?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const editorContainer = ref<HTMLDivElement>();
const editor = shallowRef<monaco.editor.IStandaloneCodeEditor>();

onMounted(() => {
  if (!editorContainer.value) return;
  editor.value = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: props.language || "python",
    theme: "vs-dark",
    automaticLayout: true,
    minimap: { enabled: true },
    fontSize: 14,
    lineNumbers: "on",
    scrollBeyondLastLine: false,
    readOnly: props.readOnly,
  });
  editor.value.onDidChangeModelContent(() => {
    emit("update:modelValue", editor.value!.getValue());
  });
});
</script>

<template>
  <div ref="editorContainer" class="code-editor" />
</template>

<style scoped>
.code-editor {
  width: 100%;
  height: 500px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}
</style>
```

---

## 10. 图表组件（ECharts）

### 10.1 K线图 KlineChart.vue

```typescript
// src/components/charts/KlineChart.vue 核心配置
const option = computed(() => ({
  animation: false,
  tooltip: {
    trigger: "axis",
    axisPointer: { type: "cross" },
    formatter: formatKlineTooltip,
  },
  legend: {
    data: ["K线", "MA5", "MA10", "MA20"],
  },
  grid: [
    { left: "10%", right: "8%", height: "60%" },
    { left: "10%", right: "8%", top: "72%", height: "16%" },
  ],
  xAxis: [
    {
      type: "category",
      data: dates.value,
      boundaryGap: true,
      axisLine: { onZero: false },
      splitLine: { show: false },
    },
    {
      type: "category",
      gridIndex: 1,
      data: dates.value,
      boundaryGap: true,
      axisLine: { onZero: false },
      splitLine: { show: false },
    },
  ],
  yAxis: [
    { scale: true, splitArea: { show: true } },
    { scale: true, gridIndex: 1, splitNumber: 2 },
  ],
  dataZoom: [
    { type: "inside", xAxisIndex: [0, 1], start: 80, end: 100 },
    { show: true, xAxisIndex: [0, 1], type: "slider", top: "92%" },
  ],
  series: [
    {
      name: "K线",
      type: "candlestick",
      data: ohlc.value,
      itemStyle: {
        color: "#ef232a",       // 阳线填充色（涨）
        color0: "#14b143",      // 阴线填充色（跌）
        borderColor: "#ef232a", // 阳线边框
        borderColor0: "#14b143",// 阴线边框
      },
    },
    { name: "MA5", type: "line", data: ma5.value, smooth: true, lineStyle: { width: 1 } },
    { name: "MA10", type: "line", data: ma10.value, smooth: true, lineStyle: { width: 1 } },
    { name: "MA20", type: "line", data: ma20.value, smooth: true, lineStyle: { width: 1 } },
    {
      name: "成交量",
      type: "bar",
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: volumes.value,
      itemStyle: {
        color: function (params: any) {
          return ohlc.value[params.dataIndex][1] >= ohlc.value[params.dataIndex][0]
            ? "#ef232a"
            : "#14b143";
        },
      },
    },
  ],
}));
```

### 10.2 权益曲线 EquityCurveChart.vue

```typescript
const option = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { data: ["策略权益", "基准"] },
  grid: { left: "10%", right: "5%", top: "15%", bottom: "20%" },
  xAxis: { type: "category", data: dates.value },
  yAxis: { type: "value", scale: true },
  dataZoom: [{ type: "inside" }, { type: "slider" }],
  series: [
    {
      name: "策略权益",
      type: "line",
      data: equity.value,
      smooth: true,
      lineStyle: { width: 2, color: "#409EFF" },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: "rgba(64,158,255,0.3)" },
          { offset: 1, color: "rgba(64,158,255,0.05)" },
        ]),
      },
    },
    {
      name: "基准",
      type: "line",
      data: benchmark.value,
      lineStyle: { width: 1, type: "dashed", color: "#999" },
    },
  ],
}));
```

### 10.3 持仓饼图 PositionPieChart.vue

```typescript
const option = computed(() => ({
  tooltip: { trigger: "item", formatter: "{b}: ¥{c} ({d}%)" },
  legend: { orient: "vertical", left: "left" },
  series: [
    {
      type: "pie",
      radius: ["40%", "70%"],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6, borderColor: "#fff", borderWidth: 2 },
      label: { show: true, formatter: "{b}\n{d}%" },
      data: positionData.value.map((p) => ({
        name: p.symbol,
        value: p.market_value,
      })),
    },
  ],
}));
```

### 10.4 月度收益热力图 MonthlyHeatmap.vue

```typescript
const option = computed(() => ({
  tooltip: {
    formatter: (params: any) => {
      return `${params.data[0]}年${params.data[1]}月: ${params.data[2]}%`;
    },
  },
  visualMap: {
    min: -10,
    max: 10,
    calculable: true,
    orient: "horizontal",
    left: "center",
    bottom: "5%",
    inRange: {
      color: ["#14b143", "#f5f5f5", "#ef232a"],
    },
  },
  calendar: {
    top: 60,
    left: 30,
    right: 30,
    cellSize: ["auto", 40],
    range: yearRange.value,
    monthLabel: { nameMap: "CN" },
  },
  series: [
    {
      type: "heatmap",
      coordinateSystem: "calendar",
      data: monthlyReturns.value,
    },
  ],
}));
```

---

## 11. 权限控制

### 11.1 权限组合式函数

```typescript
// src/composables/usePermission.ts
import { computed } from "vue";
import { useAuthStore } from "@/stores/auth";

export function usePermission() {
  const authStore = useAuthStore();

  const isRole = (role: string) => computed(() => authStore.role === role);
  const isAdmin = isRole("admin");

  function hasPermission(permission: string): boolean {
    if (authStore.role === "admin") return true;
    if (permission === "view") return true;
    if (permission === "trade") return authStore.role === "trader";
    return false;
  }

  return { isRole, isAdmin, hasPermission };
}
```

### 11.2 指令式权限控制

```typescript
// src/directives/permission.ts
import type { Directive } from "vue";
import { useAuthStore } from "@/stores/auth";

export const vPermission: Directive<HTMLElement, string> = {
  mounted(el, binding) {
    const authStore = useAuthStore();
    const permission = binding.value;
    if (!permission) return;
    if (authStore.role === "admin") return;
    if (permission === "view") return;
    if (permission === "trade" && authStore.role !== "trader") {
      el.parentNode?.removeChild(el);
    }
  },
};
```

---

## 12. 主题与样式

### 12.1 SCSS 变量

```scss
// src/styles/variables.scss
:root {
  // 主题色
  --qp-primary: #409EFF;
  --qp-success: #67C23A;
  --qp-warning: #E6A23C;
  --qp-danger: #F56C6C;
  --qp-info: #909399;

  // 涨跌色（A股风格: 红涨绿跌）
  --qp-up: #F56C6C;
  --qp-down: #67C23A;

  // 布局
  --qp-header-height: 64px;
  --qp-sidebar-width: 220px;
  --qp-sidebar-collapsed-width: 64px;

  // 背景
  --qp-bg-page: #f0f2f5;
  --qp-bg-card: #ffffff;
  --qp-bg-sidebar: #304156;

  // 文字
  --qp-text-primary: #303133;
  --qp-text-regular: #606266;
  --qp-text-secondary: #909399;
  --qp-text-placeholder: #C0C4CC;

  // 边框
  --qp-border-color: #DCDFE6;
  --qp-border-radius: 4px;
}

// 暗色主题
html.dark {
  --qp-bg-page: #141414;
  --qp-bg-card: #1d1e1f;
  --qp-bg-sidebar: #1d1e1f;
  --qp-text-primary: #E5EAF3;
  --qp-text-regular: #CFD3DC;
  --qp-text-secondary: #A3A6AD;
  --qp-border-color: #4C4D4F;
}
```

### 12.2 主题切换

```typescript
// src/composables/useTheme.ts
import { ref } from "vue";
import { storage } from "@/utils/storage";

export function useTheme() {
  const theme = ref<"light" | "dark">(
    storage.get("theme", window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")
  );

  function toggleTheme() {
    theme.value = theme.value === "light" ? "dark" : "light";
    applyTheme();
  }

  function applyTheme() {
    document.documentElement.classList.toggle("dark", theme.value === "dark");
    storage.set("theme", theme.value);
  }

  applyTheme();

  return { theme, toggleTheme };
}
```

---

## 13. 国际化（可选）

暂不实现，UI 默认中文。预留 i18n 接口：

- 所有用户可见文本集中定义在常量或未来迁移到 `locales/zh-CN.ts`
- Element Plus 中文包已内置

---

## 14. 性能优化

### 14.1 构建优化

| 策略 | 实现 |
|------|------|
| 路由懒加载 | 所有页面组件使用 `() => import(...)` |
| 组件自动导入 | unplugin-vue-components + unplugin-auto-import |
| 第三方库分包 | Vite manualChunks |
| Monaco Editor 懒加载 | 仅在策略编辑页按需加载 |
| Tree Shaking | lodash-es、Element Plus 按需引入 |

### 14.2 运行时优化

| 策略 | 场景 |
|------|------|
| `shallowRef` | 大型 ECharts 实例、大量数据对象 |
| `computed` 缓存 | 派生数据（总持仓、浮盈等） |
| `v-memo` | 大列表渲染优化 |
| 虚拟滚动 | 订单历史等长列表（Element Plus Virtual Table） |
| WebSocket 节流 | 行情 Tick 数据 200ms 节流更新UI |
| `debounce` | 搜索输入、窗口 resize |

### 14.3 缓存策略

| 数据 | 策略 |
|------|------|
| 用户信息 | Pinia + sessionStorage |
| Token | localStorage |
| 策略列表 | Pinia（页面级缓存，切换回页面时刷新） |
| K线数据 | 内存缓存最近查看的 10 个标的 |
| 回测结果 | 不缓存，每次从API拉取 |

---

## 15. 测试策略

### 15.1 测试工具

| 工具 | 用途 |
|------|------|
| Vitest | 单元测试 |
| @vue/test-utils | Vue 组件测试 |
| @pinia/testing | Pinia Store 测试 |
| happy-dom | DOM 环境 |
| cypress | E2E 测试（可选） |

### 15.2 测试分层

```
tests/
├── unit/
│   ├── utils/
│   │   ├── format.test.ts       # 数字/日期格式化
│   │   └── validate.test.ts     # 校验规则
│   ├── stores/
│   │   ├── auth.test.ts         # 认证 Store
│   │   └── trade.test.ts        # 交易 Store
│   └── composables/
│       └── usePermission.test.ts # 权限判断
├── component/
│   ├── StatusTag.test.ts
│   ├── NumberDisplay.test.ts
│   └── OrderForm.test.ts
└── e2e/                         # (Cypress)
    ├── login.cy.ts
    ├── strategy-crud.cy.ts
    └── trade-flow.cy.ts
```

### 15.3 测试覆盖率目标

| 类型 | 目标 |
|------|------|
| 工具函数 | ≥ 90% |
| Store | ≥ 80% |
| 组件 | ≥ 60% |
| 整体 | ≥ 70% |

### 15.4 示例测试

```typescript
// tests/unit/utils/format.test.ts
import { describe, it, expect } from "vitest";
import { formatNumber, formatPercent, formatCurrency } from "@/utils/format";

describe("formatNumber", () => {
  it("should format with comma separators", () => {
    expect(formatNumber(1234567.89)).toBe("1,234,567.89");
  });
});

describe("formatPercent", () => {
  it("should format positive percent with + sign", () => {
    expect(formatPercent(0.0567)).toBe("+5.67%");
  });
  it("should format negative percent", () => {
    expect(formatPercent(-0.0321)).toBe("-3.21%");
  });
});

// tests/unit/stores/auth.test.ts
import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "@/stores/auth";

describe("AuthStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("should not be logged in initially", () => {
    const store = useAuthStore();
    expect(store.isLoggedIn).toBe(false);
  });

  it("should be logged in after login", async () => {
    const store = useAuthStore();
    vi.spyOn(authApi, "login").mockResolvedValue({
      data: { access_token: "test-token", refresh_token: "refresh-token" },
    });
    vi.spyOn(authApi, "getMe").mockResolvedValue({
      data: { id: "1", username: "test", role: "trader" },
    });
    await store.login({ username: "test", password: "Test1234" });
    expect(store.isLoggedIn).toBe(true);
    expect(store.username).toBe("test");
  });
});
```
