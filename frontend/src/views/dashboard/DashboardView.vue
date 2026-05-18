<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { dashboardApi } from '@/api/dashboard'
import { tradeApi } from '@/api/trade'
import { useTradeStore } from '@/stores/trade'
import { useRiskStore } from '@/stores/risk'
import { BasicPage } from '@/components/global-layout'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import {
  Card as UiCard,
  CardHeader as UiCardHeader,
  CardContent as UiCardContent,
  CardTitle as UiCardTitle,
  CardDescription as UiCardDescription,
} from '@/components/ui/card'
import {
  Table as UiTable,
  TableHeader as UiTableHeader,
  TableBody as UiTableBody,
  TableRow as UiTableRow,
  TableHead as UiTableHead,
  TableCell as UiTableCell,
} from '@/components/ui/table'
import UiSkeleton from '@/components/ui/skeleton/Skeleton.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart, PieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import {
  Activity,
  ArrowUpRight,
  BriefcaseBusiness,
  Sparkles,
} from 'lucide-vue-next'
import { formatCurrency, formatPercent, formatCompactNumber, formatDate } from '@/utils/format'

use([TitleComponent, TooltipComponent, LegendComponent, GridComponent, DataZoomComponent, LineChart, PieChart, CanvasRenderer])

const router = useRouter()
const tradeStore = useTradeStore()
const riskStore = useRiskStore()
const overview = ref<any>(null)
const equityRange = ref('1M')
const loading = ref(false)

const equityOption = ref<any>({})
const positionOption = ref<any>({})
const recentOrders = ref<any[]>([])
const strategyRanking = ref<any[]>([])
const rangeOptions = ['1D', '1W', '1M', '3M', '1Y', 'ALL']

async function loadData() {
  loading.value = true
  try {
    const [overviewRes, equityRes, rankRes, ordersRes] = await Promise.allSettled([
      dashboardApi.getOverview(),
      dashboardApi.getEquityCurve({ range: equityRange.value }),
      dashboardApi.getStrategyRanking(),
      tradeApi.getOrders({ page: 1, page_size: 5 }),
    ])

    if (overviewRes.status === 'fulfilled') overview.value = (overviewRes.value as any).data
    if (ordersRes.status === 'fulfilled') recentOrders.value = (ordersRes.value as any).data?.items || []
    if (rankRes.status === 'fulfilled') strategyRanking.value = (rankRes.value as any).data || []

    if (equityRes.status === 'fulfilled') {
      const points = (equityRes.value as any).data || []
      equityOption.value = {
        tooltip: { trigger: 'axis' },
        grid: { left: 80, right: 30, top: 30, bottom: 40 },
        xAxis: { type: 'category', data: points.map((p: any) => p.date), boundaryGap: false },
        yAxis: { type: 'value', scale: true, axisLabel: { formatter: (v: number) => formatCompactNumber(v) } },
        dataZoom: [{ type: 'inside' }],
        series: [
          {
            name: '权益',
            type: 'line',
            data: points.map((p: any) => p.equity),
            smooth: true,
            lineStyle: { width: 2, color: 'hsl(var(--primary))' },
            areaStyle: {
              color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
                { offset: 0, color: 'rgba(59,130,246,0.3)' },
                { offset: 1, color: 'rgba(59,130,246,0.02)' },
              ] },
            },
          },
        ],
      }
    }

    if (overview.value) {
      await tradeStore.fetchPositions()
      const positions = tradeStore.positions
      const posData = positions.slice(0, 6).map((p: any) => ({
        name: p.symbol,
        value: parseFloat(p.qty) * parseFloat(p.avg_price || 0),
      }))
      positionOption.value = {
        tooltip: { trigger: 'item', formatter: '{b}: ¥{c}' },
        series: [{
          type: 'pie', radius: ['40%', '70%'],
          data: posData.length ? posData : [{ name: '暂无持仓', value: 1 }],
          label: { fontSize: 12 },
        }],
      }
    }
  } catch {
    toast.error('看板数据加载失败')
  } finally {
    loading.value = false
  }
}

function onRangeChange() { loadData() }

function getPnlColor(val: any) {
  const n = Number(val)
  if (n > 0) return 'text-green-600 dark:text-green-400'
  if (n < 0) return 'text-red-600 dark:text-red-400'
  return ''
}

function orderStatusVariant(status: string) {
  if (status === 'filled') return 'default'
  if (status === 'cancelled' || status === 'rejected') return 'destructive'
  return 'secondary'
}

function orderStatusLabel(status: string) {
  return ({ filled: '已成交', pending: '待成交', submitted: '已提交', cancelled: '已撤单', rejected: '已拒绝' } as Record<string, string>)[status] || status
}

onMounted(() => {
  loadData()
  riskStore.fetchUnreadCount()
})
</script>

<template>
  <BasicPage title="看板" description="资金、策略和执行流概览">
    <template #actions>
      <Badge variant="secondary">{{ overview?.mode === 'paper' ? '模拟盘' : '实盘' }}</Badge>
      <Badge variant="outline">{{ overview?.today_trades || 0 }} 笔今日交易</Badge>
    </template>

    <div class="space-y-6">
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <UiCard>
          <UiCardHeader class="flex flex-row items-center justify-between pb-2 space-y-0">
            <UiCardTitle class="text-sm font-medium text-muted-foreground">总资产</UiCardTitle>
            <BriefcaseBusiness class="size-4 text-muted-foreground" />
          </UiCardHeader>
          <UiCardContent>
            <div v-if="loading" class="space-y-2">
              <UiSkeleton class="h-8 w-32" />
              <UiSkeleton class="h-4 w-20" />
            </div>
            <template v-else>
              <div class="text-2xl font-bold">{{ formatCurrency(overview?.total_equity) }}</div>
              <p class="text-xs text-muted-foreground mt-1">
                {{ overview?.mode === 'paper' ? '模拟盘' : '实盘' }}
              </p>
            </template>
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader class="flex flex-row items-center justify-between pb-2 space-y-0">
            <UiCardTitle class="text-sm font-medium text-muted-foreground">日盈亏</UiCardTitle>
            <Activity class="size-4 text-muted-foreground" />
          </UiCardHeader>
          <UiCardContent>
            <div v-if="loading" class="space-y-2">
              <UiSkeleton class="h-8 w-32" />
              <UiSkeleton class="h-4 w-20" />
            </div>
            <template v-else>
              <div class="text-2xl font-bold" :class="getPnlColor(overview?.daily_pnl)">{{ formatCurrency(overview?.daily_pnl) }}</div>
              <p class="text-xs mt-1" :class="getPnlColor(overview?.daily_pnl_pct)">{{ formatPercent(overview?.daily_pnl_pct) }}</p>
            </template>
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader class="flex flex-row items-center justify-between pb-2 space-y-0">
            <UiCardTitle class="text-sm font-medium text-muted-foreground">总盈亏</UiCardTitle>
            <ArrowUpRight class="size-4 text-muted-foreground" />
          </UiCardHeader>
          <UiCardContent>
            <div v-if="loading" class="space-y-2">
              <UiSkeleton class="h-8 w-32" />
              <UiSkeleton class="h-4 w-20" />
            </div>
            <template v-else>
              <div class="text-2xl font-bold" :class="getPnlColor(overview?.total_pnl)">{{ formatCurrency(overview?.total_pnl) }}</div>
              <p class="text-xs mt-1" :class="getPnlColor(overview?.total_pnl_pct)">{{ formatPercent(overview?.total_pnl_pct) }}</p>
            </template>
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader class="flex flex-row items-center justify-between pb-2 space-y-0">
            <UiCardTitle class="text-sm font-medium text-muted-foreground">运行策略</UiCardTitle>
            <Sparkles class="size-4 text-muted-foreground" />
          </UiCardHeader>
          <UiCardContent>
            <div v-if="loading" class="space-y-2">
              <UiSkeleton class="h-8 w-24" />
              <UiSkeleton class="h-4 w-32" />
            </div>
            <template v-else>
              <div class="text-2xl font-bold">{{ overview?.running_strategies || 0 }} / {{ overview?.total_strategies || 0 }}</div>
              <p class="text-xs text-muted-foreground mt-1">未读风控通知：{{ riskStore.unreadCount }}</p>
            </template>
          </UiCardContent>
        </UiCard>
      </div>

      <div class="grid gap-6 lg:grid-cols-[1.6fr_0.84fr]">
        <UiCard>
          <UiCardHeader>
            <div class="flex items-center justify-between">
              <div>
                <UiCardTitle>权益曲线</UiCardTitle>
                <UiCardDescription>净值走势与基准对比</UiCardDescription>
              </div>
              <div class="flex gap-1">
                <Button
                  v-for="range in rangeOptions"
                  :key="range"
                  :variant="equityRange === range ? 'default' : 'ghost'"
                  size="sm"
                  class="h-7 px-2 text-xs"
                  @click="equityRange = range; onRangeChange()"
                >
                  {{ range }}
                </Button>
              </div>
            </div>
          </UiCardHeader>
          <UiCardContent>
            <v-chart :option="equityOption" style="height: 320px" autoresize />
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader>
            <UiCardTitle>持仓分布</UiCardTitle>
            <UiCardDescription>Top 6 持仓</UiCardDescription>
          </UiCardHeader>
          <UiCardContent>
            <v-chart :option="positionOption" style="height: 320px" autoresize />
          </UiCardContent>
        </UiCard>
      </div>

      <div class="grid gap-6 lg:grid-cols-2">
        <UiCard>
          <UiCardHeader>
            <UiCardTitle>策略表现</UiCardTitle>
            <UiCardDescription>按收益排名</UiCardDescription>
          </UiCardHeader>
          <UiCardContent>
            <UiTable>
              <UiTableHeader>
                <UiTableRow>
                  <UiTableHead>策略名称</UiTableHead>
                  <UiTableHead>总收益</UiTableHead>
                  <UiTableHead>夏普比率</UiTableHead>
                  <UiTableHead>最大回撤</UiTableHead>
                </UiTableRow>
              </UiTableHeader>
              <UiTableBody>
                <UiTableRow v-for="row in strategyRanking" :key="row.strategy_name">
                  <UiTableCell class="font-medium">{{ row.strategy_name }}</UiTableCell>
                  <UiTableCell :class="getPnlColor(row.total_return)">{{ formatPercent(row.total_return / 100) }}</UiTableCell>
                  <UiTableCell>{{ Number(row.sharpe_ratio).toFixed(2) }}</UiTableCell>
                  <UiTableCell class="text-red-600 dark:text-red-400">{{ Number(row.max_drawdown).toFixed(2) }}%</UiTableCell>
                </UiTableRow>
                <UiTableRow v-if="!strategyRanking.length && !loading">
                  <UiTableCell :colspan="4" class="h-24 text-center text-muted-foreground">暂无策略表现数据</UiTableCell>
                </UiTableRow>
              </UiTableBody>
            </UiTable>
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader>
            <UiCardTitle>最近订单</UiCardTitle>
            <UiCardDescription>最近 5 笔执行记录</UiCardDescription>
          </UiCardHeader>
          <UiCardContent>
            <UiTable>
              <UiTableHeader>
                <UiTableRow>
                  <UiTableHead>标的</UiTableHead>
                  <UiTableHead>方向</UiTableHead>
                  <UiTableHead>数量</UiTableHead>
                  <UiTableHead>状态</UiTableHead>
                  <UiTableHead>时间</UiTableHead>
                </UiTableRow>
              </UiTableHeader>
              <UiTableBody>
                <UiTableRow v-for="row in recentOrders" :key="row.id || `${row.symbol}-${row.created_at}`">
                  <UiTableCell class="font-medium">{{ row.symbol }}</UiTableCell>
                  <UiTableCell :class="row.side === 'buy' ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'">
                    {{ row.side === 'buy' ? '买入' : '卖出' }}
                  </UiTableCell>
                  <UiTableCell>{{ Number(row.filled_qty || row.qty).toFixed(2) }}</UiTableCell>
                  <UiTableCell>
                    <Badge :variant="orderStatusVariant(row.status) as any">{{ orderStatusLabel(row.status) }}</Badge>
                  </UiTableCell>
                  <UiTableCell class="text-muted-foreground">{{ formatDate(row.created_at) }}</UiTableCell>
                </UiTableRow>
                <UiTableRow v-if="!recentOrders.length && !loading">
                  <UiTableCell :colspan="5" class="h-24 text-center text-muted-foreground">暂无订单记录</UiTableCell>
                </UiTableRow>
              </UiTableBody>
            </UiTable>
          </UiCardContent>
        </UiCard>
      </div>
    </div>
  </BasicPage>
</template>
