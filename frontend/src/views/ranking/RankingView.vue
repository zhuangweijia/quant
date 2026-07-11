<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { rankingApi, type RankingItem } from '@/api/ranking'
import { useWebSocket } from '@/composables/useWebSocket'
import {
  Card as UiCard, CardContent as UiCardContent,
} from '@/components/ui/card'
import {
  Table as UiTable, TableHeader as UiTableHeader, TableBody as UiTableBody,
  TableRow as UiTableRow, TableHead as UiTableHead, TableCell as UiTableCell,
} from '@/components/ui/table'
import Badge from '@/components/ui/badge/Badge.vue'
import Button from '@/components/ui/button/Button.vue'
import { Trophy, ArrowUp, ArrowDown, Minus, RefreshCw } from 'lucide-vue-next'
import { toast } from 'vue-sonner'

const router = useRouter()
const loading = ref(true)
const items = ref<RankingItem[]>([])
const total = ref(0)
const currentDate = ref('')
const activeLabel = ref<string | undefined>(undefined)
const page = ref(1)
const pageSize = 30

const labels = [
  { value: undefined, label: '全部' },
  { value: '强推', label: '强推' },
  { value: '关注', label: '关注' },
  { value: '观望', label: '观望' },
  { value: '回避', label: '回避' },
]

async function fetchRankings() {
  loading.value = true
  try {
    const { data } = await rankingApi.getRankings({ date: 'today', label: activeLabel.value, page: page.value, size: pageSize })
    items.value = data.data.items
    total.value = data.data.total
    currentDate.value = data.data.date
  } catch { items.value = [] } finally { loading.value = false }
}

function labelVariant(label: string | null) {
  if (label === '强推') return 'default'
  if (label === '回避') return 'destructive'
  return 'outline'
}

function scoreColor(s: number) {
  if (s >= 0.7) return 'text-green-600 dark:text-green-400 font-bold'
  if (s < 0.3) return 'text-red-600 dark:text-red-400'
  return ''
}

function changeColor(c: number | null) {
  if (c === null) return 'text-blue-500'
  if (c > 0) return 'text-green-600 dark:text-green-400'
  if (c < 0) return 'text-red-600 dark:text-red-400'
  return ''
}

function changeIcon(c: number | null) {
  if (c === null) return null
  if (c > 0) return ArrowUp
  if (c < 0) return ArrowDown
  return Minus
}

function goToStock(symbol: string) { router.push(`/stock/${symbol}`) }

const { subscribe, onMessage } = useWebSocket()
const cleanups: (() => void)[] = []
onMounted(() => {
  fetchRankings()
  subscribe('analysis:ranking_ready')
  cleanups.push(onMessage('analysis:ranking_ready', () => { toast.success('排名已更新'); fetchRankings() }))
})
onUnmounted(() => cleanups.forEach(c => c()))
watch([activeLabel, page], () => fetchRankings())
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <Trophy class="size-6 text-primary" />
        <div>
          <h1 class="text-2xl font-bold">每日排名表</h1>
          <p class="text-sm text-muted-foreground">{{ currentDate }} · 共 {{ total }} 只</p>
        </div>
      </div>
      <Button variant="outline" size="sm" :disabled="loading" @click="fetchRankings">
        <RefreshCw class="size-4 mr-1" :class="{ 'animate-spin': loading }" />刷新
      </Button>
    </div>

    <div class="flex gap-2">
      <Button v-for="l in labels" :key="l.label" :variant="activeLabel === l.value ? 'default' : 'outline'" size="sm"
        @click="activeLabel = l.value; page = 1">{{ l.label }}</Button>
    </div>

    <UiCard>
      <UiCardContent class="p-0">
        <UiTable>
          <UiTableHeader>
            <UiTableRow>
              <UiTableHead class="w-16">排名</UiTableHead>
              <UiTableHead class="w-24">代码</UiTableHead>
              <UiTableHead>名称</UiTableHead>
              <UiTableHead class="w-24">评分</UiTableHead>
              <UiTableHead class="w-20">标签</UiTableHead>
              <UiTableHead class="w-24">较昨日</UiTableHead>
            </UiTableRow>
          </UiTableHeader>
          <UiTableBody>
            <UiTableRow v-for="item in items" :key="item.symbol"
              class="cursor-pointer hover:bg-muted/50"
              :class="{ 'bg-green-50/50 dark:bg-green-950/20': item.label === '强推', 'bg-red-50/50 dark:bg-red-950/20': item.label === '回避' }"
              @click="goToStock(item.symbol)">
              <UiTableCell class="font-mono font-bold">{{ item.rank }}</UiTableCell>
              <UiTableCell class="font-mono text-muted-foreground">{{ item.symbol }}</UiTableCell>
              <UiTableCell class="font-medium">{{ item.name || item.symbol }}</UiTableCell>
              <UiTableCell :class="scoreColor(item.score)">{{ item.score.toFixed(3) }}</UiTableCell>
              <UiTableCell><Badge :variant="labelVariant(item.label) as any" class="text-xs">{{ item.label || '-' }}</Badge></UiTableCell>
              <UiTableCell>
                <span v-if="item.rank_change === null" class="text-blue-500 text-xs font-medium">NEW</span>
                <span v-else :class="changeColor(item.rank_change)" class="flex items-center gap-0.5">
                  <component v-if="changeIcon(item.rank_change)" :is="changeIcon(item.rank_change)" class="size-3" />{{ Math.abs(item.rank_change) }}
                </span>
              </UiTableCell>
            </UiTableRow>
            <UiTableRow v-if="!items.length && !loading">
              <UiTableCell :colspan="6" class="h-24 text-center text-muted-foreground">暂无排名数据，请先运行分析 Pipeline</UiTableCell>
            </UiTableRow>
          </UiTableBody>
        </UiTable>
      </UiCardContent>
    </UiCard>

    <div v-if="total > pageSize" class="flex items-center justify-center gap-2">
      <Button variant="outline" size="sm" :disabled="page <= 1" @click="page--">上一页</Button>
      <span class="text-sm text-muted-foreground">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
      <Button variant="outline" size="sm" :disabled="page * pageSize >= total" @click="page++">下一页</Button>
    </div>
  </div>
</template>
