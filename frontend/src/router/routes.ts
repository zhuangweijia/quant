import type { RouteRecordRaw } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { requiresAuth: false, title: '登录' },
  },
  {
    path: '/',
    component: AppLayout,
    redirect: '/today',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        redirect: '/today',
      },
      {
        path: 'ranking',
        redirect: '/selection',
      },
      {
        path: 'today',
        name: 'Today',
        component: () => import('@/views/today/TodayView.vue'),
        meta: { title: '今日', icon: 'CalendarCheck2' },
      },
      {
        path: 'portfolio/setup',
        name: 'PortfolioSetup',
        component: () => import('@/views/portfolio-setup/PortfolioSetupView.vue'),
        meta: { title: '初始化投资组合' },
      },
      {
        path: 'portfolio',
        name: 'Portfolio',
        component: () => import('@/views/portfolio/PortfolioView.vue'),
        meta: { title: '持仓', icon: 'BriefcaseBusiness' },
      },
      {
        path: 'selection',
        name: 'Selection',
        component: () => import('@/views/ranking/RankingView.vue'),
        meta: { title: '选股', icon: 'ListFilter' },
      },
      {
        path: 'stock/:symbol',
        name: 'StockDetail',
        component: () => import('@/views/stock-detail/StockDetailView.vue'),
        meta: { title: '个股详情' },
      },
      {
        path: 'market',
        name: 'Market',
        component: () => import('@/views/market/MarketView.vue'),
        meta: { title: '市场', icon: 'CandlestickChart' },
      },
      {
        path: 'admin/tasks',
        name: 'AnalysisTasks',
        component: () => import('@/views/admin/AnalysisTasksView.vue'),
        meta: { title: '分析任务', adminOnly: true, icon: 'Activity' },
      },
      {
        path: 'model',
        name: 'Model',
        component: () => import('@/views/model/ModelView.vue'),
        meta: { title: '模型与回测', adminOnly: true, icon: 'BrainCircuit' },
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/SettingsView.vue'),
        meta: { title: '设置', icon: 'Tools' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/components/error/NotFound.vue'),
    meta: { requiresAuth: false },
  },
]

export default routes
