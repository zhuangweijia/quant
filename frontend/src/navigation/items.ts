import type { Component } from 'vue'
import {
  Activity,
  BrainCircuit,
  BriefcaseBusiness,
  CalendarCheck2,
  CandlestickChart,
  ListFilter,
} from 'lucide-vue-next'

export interface NavigationItem {
  title: string
  path: string
  icon: Component
}

const primaryNav: NavigationItem[] = [
  { title: '今日', path: '/today', icon: CalendarCheck2 },
  { title: '持仓', path: '/portfolio', icon: BriefcaseBusiness },
  { title: '选股', path: '/selection', icon: ListFilter },
  { title: '市场', path: '/market', icon: CandlestickChart },
]

const adminNav: NavigationItem[] = [
  { title: '分析任务', path: '/admin/tasks', icon: Activity },
  { title: '模型与回测', path: '/model', icon: BrainCircuit },
]

export function getPrimaryNav(_role: string): NavigationItem[] {
  return primaryNav
}

export function getAdminNav(role: string): NavigationItem[] {
  return role === 'admin' ? adminNav : []
}
