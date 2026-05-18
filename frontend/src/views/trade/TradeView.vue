<script setup lang="ts">
import { ref, onMounted, h } from 'vue'
import { toast } from 'vue-sonner'
import { useTradeStore } from '@/stores/trade'
import { formatCurrency, formatNumber, formatDate } from '@/utils/format'
import { BasicPage } from '@/components/global-layout'
import { DataTable } from '@/components/data-table'
import type { ColumnDef } from '@tanstack/vue-table'
import Button from '@/components/ui/button/Button.vue'
import Label from '@/components/ui/label/Label.vue'
import Input from '@/components/ui/input/Input.vue'
import Badge from '@/components/ui/badge/Badge.vue'
import {
  Card as UiCard,
  CardHeader as UiCardHeader,
  CardContent as UiCardContent,
  CardTitle as UiCardTitle,
  CardDescription as UiCardDescription,
} from '@/components/ui/card'
import {
  Select as UiSelect,
  SelectContent as UiSelectContent,
  SelectItem as UiSelectItem,
  SelectTrigger as UiSelectTrigger,
  SelectValue as UiSelectValue,
} from '@/components/ui/select'
import {
  Tabs as UiTabs,
  TabsContent as UiTabsContent,
  TabsList as UiTabsList,
  TabsTrigger as UiTabsTrigger,
} from '@/components/ui/tabs'
import {
  AlertDialog as UiAlertDialog,
  AlertDialogAction as UiAlertDialogAction,
  AlertDialogCancel as UiAlertDialogCancel,
  AlertDialogContent as UiAlertDialogContent,
  AlertDialogDescription as UiAlertDialogDescription,
  AlertDialogFooter as UiAlertDialogFooter,
  AlertDialogHeader as UiAlertDialogHeader,
  AlertDialogTitle as UiAlertDialogTitle,
} from '@/components/ui/alert-dialog'

const store = useTradeStore()
const loading = ref(false)
const activeTab = ref('positions')

const orderForm = ref({
  symbol: '',
  side: 'buy',
  type: 'market',
  qty: '',
  price: '',
})

const confirmAction = ref<{ type: string; id: string; title: string } | null>(null)

const positionColumns: ColumnDef<any>[] = [
  { accessorKey: 'symbol', header: '标的', cell: ({ row }) => h('span', { class: 'font-medium' }, row.getValue('symbol')) },
  { accessorKey: 'side', header: '方向', cell: ({ row }) => h('span', { class: row.getValue('side') === 'long' ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400' }, row.getValue('side') === 'long' ? '多' : '空') },
  { accessorKey: 'qty', header: '数量', cell: ({ row }) => Number(row.getValue('qty')).toFixed(4) },
  { accessorKey: 'avg_price', header: '均价', cell: ({ row }) => formatNumber(row.getValue('avg_price'), 2) },
  {
    accessorKey: 'unrealized_pnl',
    header: '浮动盈亏',
    cell: ({ row }) => {
      const v = Number(row.getValue('unrealized_pnl'))
      return h('span', { class: v > 0 ? 'text-green-600 dark:text-green-400' : v < 0 ? 'text-red-600 dark:text-red-400' : '' }, formatCurrency(v))
    },
  },
  {
    id: 'actions',
    header: '',
    cell: ({ row }) => h(Button, {
      size: 'sm', variant: 'ghost', class: 'text-destructive',
      onClick: () => { confirmAction.value = { type: 'close', id: row.original.id, title: row.original.symbol } },
    }, () => '平仓'),
  },
]

const orderColumns: ColumnDef<any>[] = [
  { accessorKey: 'symbol', header: '标的', cell: ({ row }) => h('span', { class: 'font-medium' }, row.getValue('symbol')) },
  {
    accessorKey: 'side',
    header: '方向',
    cell: ({ row }) => h('span', { class: row.getValue('side') === 'buy' ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400' }, row.getValue('side') === 'buy' ? '买入' : '卖出'),
  },
  { accessorKey: 'qty', header: '数量', cell: ({ row }) => Number(row.original.qty).toFixed(4) },
  { accessorKey: 'price', header: '价格', cell: ({ row }) => formatNumber(row.getValue('price'), 2) },
  {
    accessorKey: 'status',
    header: '状态',
    cell: ({ row }) => {
      const s = row.getValue('status') as string
      const map: Record<string, string> = { filled: '已成交', pending: '待成交', submitted: '已提交', cancelled: '已撤单', rejected: '已拒绝' }
      const variant = s === 'filled' ? 'default' : s === 'cancelled' || s === 'rejected' ? 'destructive' : 'secondary'
      return h(Badge, { variant }, () => map[s] || s)
    },
  },
  { accessorKey: 'created_at', header: '时间', cell: ({ row }) => formatDate(row.getValue('created_at')) },
  {
    id: 'actions',
    header: '',
    cell: ({ row }) => row.original.status === 'pending' || row.original.status === 'submitted'
      ? h(Button, {
          size: 'sm', variant: 'ghost', class: 'text-destructive',
          onClick: () => { confirmAction.value = { type: 'cancel', id: row.original.id, title: row.original.symbol } },
        }, () => '撤单')
      : null,
  },
]

async function loadData() {
  loading.value = true
  try {
    await Promise.all([
      store.fetchPositions(),
      store.fetchOrders({ page: 1, page_size: 50 }),
      store.fetchAccount(),
    ])
  } finally { loading.value = false }
}

async function handleSubmitOrder() {
  if (!orderForm.value.symbol || !orderForm.value.qty) {
    toast.error('请填写标的和数量')
    return
  }
  try {
    await store.submitOrder({
      symbol: orderForm.value.symbol,
      side: orderForm.value.side,
      type: orderForm.value.type,
      qty: Number(orderForm.value.qty),
      price: orderForm.value.price ? Number(orderForm.value.price) : undefined,
    } as any)
    toast.success('下单成功')
    orderForm.value = { symbol: '', side: 'buy', type: 'market', qty: '', price: '' }
    await loadData()
  } catch (e: any) { toast.error(e.message || '下单失败') }
}

async function handleConfirm() {
  if (!confirmAction.value) return
  try {
    if (confirmAction.value.type === 'close') {
      await store.closePosition(confirmAction.value.id)
      toast.success('平仓成功')
    } else if (confirmAction.value.type === 'cancel') {
      await store.cancelOrder(confirmAction.value.id)
      toast.success('撤单成功')
    }
    await loadData()
  } catch (e: any) { toast.error(e.message || '操作失败') }
  finally { confirmAction.value = null }
}

onMounted(loadData)
</script>

<template>
  <BasicPage title="交易" description="下单、持仓和委托管理">
    <div class="space-y-6">
      <div class="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div>
          <UiTabs v-model="activeTab">
            <UiTabsList>
              <UiTabsTrigger value="positions">持仓</UiTabsTrigger>
              <UiTabsTrigger value="orders">委托</UiTabsTrigger>
            </UiTabsList>
            <UiTabsContent value="positions" class="mt-4">
              <DataTable :columns="positionColumns" :data="store.positions" :total="store.positions.length" :page-size="50" :loading="loading" />
            </UiTabsContent>
            <UiTabsContent value="orders" class="mt-4">
              <DataTable :columns="orderColumns" :data="store.orders" :total="store.ordersTotal" :page-size="50" :loading="loading" />
            </UiTabsContent>
          </UiTabs>
        </div>

        <div class="space-y-6">
          <UiCard v-if="store.account">
            <UiCardHeader class="pb-3">
              <UiCardTitle class="text-base">账户信息</UiCardTitle>
            </UiCardHeader>
            <UiCardContent class="space-y-3">
              <div class="flex justify-between text-sm">
                <span class="text-muted-foreground">总资产</span>
                <span class="font-medium">{{ formatCurrency(store.account.total_equity) }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-muted-foreground">可用余额</span>
                <span class="font-medium">{{ formatCurrency(store.account.cash) }}</span>
              </div>
              <div class="flex justify-between text-sm">
                <span class="text-muted-foreground">持仓保证金</span>
                <span class="font-medium">{{ formatCurrency(store.account.position_value) }}</span>
              </div>
            </UiCardContent>
          </UiCard>

          <UiCard>
            <UiCardHeader class="pb-3">
              <UiCardTitle class="text-base">下单</UiCardTitle>
              <UiCardDescription>快速下单面板</UiCardDescription>
            </UiCardHeader>
            <UiCardContent class="space-y-4">
              <div class="space-y-2">
                <Label>标的</Label>
                <Input v-model="orderForm.symbol" placeholder="如 BTCUSDT" />
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="space-y-2">
                  <Label>方向</Label>
                  <UiSelect v-model="orderForm.side">
                    <UiSelectTrigger><UiSelectValue /></UiSelectTrigger>
                    <UiSelectContent>
                      <UiSelectItem value="buy">买入</UiSelectItem>
                      <UiSelectItem value="sell">卖出</UiSelectItem>
                    </UiSelectContent>
                  </UiSelect>
                </div>
                <div class="space-y-2">
                  <Label>类型</Label>
                  <UiSelect v-model="orderForm.type">
                    <UiSelectTrigger><UiSelectValue /></UiSelectTrigger>
                    <UiSelectContent>
                      <UiSelectItem value="market">市价</UiSelectItem>
                      <UiSelectItem value="limit">限价</UiSelectItem>
                    </UiSelectContent>
                  </UiSelect>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="space-y-2">
                  <Label>数量</Label>
                  <Input v-model="orderForm.qty" type="number" placeholder="0" />
                </div>
                <div v-if="orderForm.type === 'limit'" class="space-y-2">
                  <Label>价格</Label>
                  <Input v-model="orderForm.price" type="number" placeholder="0" />
                </div>
              </div>
              <Button class="w-full" @click="handleSubmitOrder">
                {{ orderForm.side === 'buy' ? '买入' : '卖出' }}
              </Button>
            </UiCardContent>
          </UiCard>
        </div>
      </div>
    </div>

    <UiAlertDialog :open="!!confirmAction" @update:open="!$event && (confirmAction = null)">
      <UiAlertDialogContent>
        <UiAlertDialogHeader>
          <UiAlertDialogTitle>确认操作</UiAlertDialogTitle>
          <UiAlertDialogDescription>
            {{ confirmAction?.type === 'close' ? `确定平仓「${confirmAction?.title}」？` : `确定撤销「${confirmAction?.title}」的委托？` }}
          </UiAlertDialogDescription>
        </UiAlertDialogHeader>
        <UiAlertDialogFooter>
          <UiAlertDialogCancel>取消</UiAlertDialogCancel>
          <UiAlertDialogAction @click="handleConfirm">确认</UiAlertDialogAction>
        </UiAlertDialogFooter>
      </UiAlertDialogContent>
    </UiAlertDialog>
  </BasicPage>
</template>
