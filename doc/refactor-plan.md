# Quant 前端重构计划 — shadcn-vue 极简风格

## 现状分析

| 维度 | 当前状态 | 目标状态 |
|------|---------|---------|
| UI 组件库 | Element Plus (半数页面) + 少量 shadcn 组件 | 全部 shadcn-vue (60+ 组件) |
| 样式方案 | tokens.css + global.scss + Element 覆写 | Tailwind CSS v4 + CSS Variables 主题系统 |
| 数据获取 | 手动 axios + Pinia store action | TanStack Vue Query (缓存/失效/重试) |
| 表单验证 | 无统一方案 | VeeValidate + Zod |
| 表格 | Element Plus el-table | TanStack Vue Table (可复用 DataTable 组件) |
| 通知 | ElMessage / ElMessageBox | vue-sonner (toast) + shadcn Dialog |
| 布局 | 自定义 Sidebar/Header | shadcn-vue Sidebar 组件系统 |
| 主题 | oklch CSS Variables (2套) | 多主题 (8色) + 圆角 + 暗色模式 |
| HTTP 客户端 | axios | 保留 axios |
| 状态管理 | 6 个 Pinia store (含服务端数据) | Pinia (仅客户端状态) + TanStack Query (服务端数据) |

---

## 阶段一：基础设施搭建 (1-2 天)

1. **安装核心依赖**
   - `reka-ui` (shadcn-vue 底层原语)
   - `@vueuse/core` (composables 工具集)
   - `@tanstack/vue-query` (服务端状态管理)
   - `vee-validate` + `zod` + `@vee-validate/zod` (表单验证)
   - `vue-sonner` (Toast 通知)
   - `@tanstack/vue-table` (高级表格)
   - `tw-animate-css` (动画)

2. **使用 shadcn-vue CLI 初始化组件系统**

3. **安装所需的 shadcn-vue 组件**
   - button, card, input, badge, dialog, dropdown-menu, select, table, tabs, form, field, label, sonner, popover, command, sheet, separator, avatar, scroll-area, sidebar, skeleton, switch, checkbox, radio-group, textarea, tooltip, alert, alert-dialog, breadcrumb, pagination, progress, collapsible, drawer

4. **重构主题系统**
   - 用 shadcn-vue-admin 的 index.css + themes.css 替换 tokens.css + global.scss
   - 实现 8 色主题 + 圆角控制 + light/dark/system 三模式

5. **移除 Element Plus**
   - 从 package.json 移除 element-plus 及 @element-plus/icons-vue
   - 从 main.ts 移除 app.use(ElementPlus)
   - 移除 Vite 插件中的 ElementPlusResolver

---

## 阶段二：核心框架层 (2-3 天)

6. **重构布局系统**
   - 用 shadcn-vue 的 Sidebar 组件重写 AppLayout
   - SidebarProvider > AppSidebar + SidebarInset > Header + Content
   - Sidebar: Logo, 导航菜单, 用户头像/退出
   - Header: SidebarTrigger + 页面标题 + 主题切换 + 通知 + 用户菜单

7. **搭建 DataTable 可复用组件**
   - DataTable.vue, ColumnHeader.vue, TablePagination.vue, TableLoading.vue
   - 支持列排序/筛选/分页/骨架屏加载

8. **搭建页面布局组件**
   - BasicPage — 粘性头部 (标题 + 描述 + 操作按钮) + 内容区

9. **重构 API 层**
   - 保留 axios，将每个 API 模块改为 TanStack Query hooks

10. **实现 Toast 通知系统**
    - 全局挂载 Toaster 替代 ElMessage / ElMessageBox
    - 确认弹窗用 shadcn AlertDialog 组件

---

## 阶段三：页面逐页重构 (5-7 天)

### 3.1 LoginView (0.5 天)
- shadcn Card + Input + Button
- VeeValidate + Zod 校验

### 3.2 DashboardView (1 天)
- shadcn Card + Badge + Tabs 重构卡片布局
- ECharts 保留，用 shadcn 卡片包裹

### 3.3 MarketView (1 天)
- 自选股列表：DataTable 组件
- K线图：shadcn Tabs + Select + ECharts
- 搜索/添加自选：shadcn Command
- 实时 Tick：shadcn Card + Badge

### 3.4 StrategyListView + StrategyEditView (1.5 天)
- 策略列表：DataTable
- 创建/编辑：VeeValidate + Zod 表单
- 策略日志：Dialog + ScrollArea
- 启动/停止确认：AlertDialog

### 3.5 BacktestView (1 天)
- 参数表单 + 运行进度
- 结果展示：DataTable + ECharts

### 3.6 TradeView (1 天)
- 持仓/委托/成交：3 个 DataTable (Tabs 切换)
- 下单面板 + 实时更新

### 3.7 RiskView (0.5 天)
- 规则列表 + 开关 + 告警列表

### 3.8 SettingsView (1 天)
- TwoColLayout 侧边导航
- 各子页面：Card + Form

---

## 阶段四：打磨与优化 (1-2 天)

11. **Command Menu (Ctrl+K)**
12. **骨架屏加载态**
13. **空状态处理**
14. **响应式优化**
15. **动画过渡**

---

## 关键架构决策

| 决策点 | 方案 | 理由 |
|--------|------|------|
| 路由方式 | 保留手动路由 | 页面数量少，更可控 |
| HTTP 客户端 | 保留 axios | 已有完善的拦截器/刷新 token 逻辑 |
| WebSocket | 保留现有方案 | 实时性要求高，Pinia store 管理合适 |
| 状态管理 | Pinia (客户端) + TanStack Query (服务端) | 关注点分离 |
| i18n | 暂不引入 | 已全中文，无国际化需求 |
| 文件路由 | 暂不引入 | 迁移成本高，收益不明显 |

---

## 预估总工时：10-14 天
