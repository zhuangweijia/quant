<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, Coins, RefreshCw, Settings2, WalletCards } from 'lucide-vue-next'

import { ApiError } from '@/api/client'
import { BasicPage } from '@/components/global-layout'
import HoldingsEditor from '@/components/portfolio/HoldingsEditor.vue'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { usePortfolioStore } from '@/stores/portfolio'
import type {
  CashMovementKind,
  InvestmentProfileInput,
  InvestmentProfileResponse,
  Money,
  PositionInput,
} from '@/types/portfolio'

const store = usePortfolioStore()

const initialLoading = ref(true)
const loadError = ref('')
const portfolioMissing = ref(false)

const profileOpen = ref(false)
const profileSaving = ref(false)
const profileError = ref('')
const profileDetail = ref('')
const profileDraft = ref({
  investmentHorizonDays: '',
  riskLevel: 'balanced' as InvestmentProfileInput['risk_level'],
  maxDrawdown: '',
  maxStockWeight: '',
  maxIndustryWeight: '',
  minCashRatio: '',
  maxDailyTurnover: '',
})

const reconcileOpen = ref(false)
const reconcileSaving = ref(false)
const reconcileCash = ref<Money>('')
const reconcilePositions = ref<PositionInput[]>([])
const reconcileExpectedUpdatedAt = ref('')
const reconcileLatestUpdatedAt = ref('')
const reconcileError = ref('')
const reconcileDetail = ref('')
const reconcileConflict = ref(false)
const reconcileRefreshing = ref(false)
const reconcileRefreshError = ref('')

const cashOpen = ref(false)
const cashSaving = ref(false)
const cashKind = ref<CashMovementKind>('deposit')
const cashAmount = ref<Money>('')
const cashOccurredAt = ref('')
const cashNote = ref('')
const cashError = ref('')
const cashDetail = ref('')

const portfolio = computed(() => store.portfolio)

const summaryItems = computed(() => {
  if (!portfolio.value) return []
  const summary = portfolio.value.summary
  return [
    { label: '总资产', value: `${summary.total_asset} ${summary.currency}` },
    { label: '可用现金', value: `${summary.cash} ${summary.currency}` },
    { label: '持仓市值', value: `${summary.market_value} ${summary.currency}` },
    { label: '总仓位', value: formatPercent(summary.exposure) },
    { label: '估值日期', value: summary.valuation_date ?? '暂无估值日期' },
    { label: '最近确认', value: summary.last_confirmed_at },
  ]
})

const profileValidationError = computed(() => {
  const draft = profileDraft.value
  const horizon = Number(draft.investmentHorizonDays)
  if (!/^\d+$/.test(draft.investmentHorizonDays) || horizon < 20 || horizon > 2520) {
    return '投资期限必须是 20 至 2520 的整数'
  }
  const values = [
    percentage(draft.maxDrawdown, 3, 50),
    percentage(draft.maxStockWeight, 1, 20),
    percentage(draft.maxIndustryWeight, 5, 50),
    percentage(draft.minCashRatio, 0, 50),
    percentage(draft.maxDailyTurnover, 5, 100),
  ]
  if (values.some(value => value === null)) return '请按允许范围填写全部组合约束'
  if ((values[1] as number) > (values[2] as number)) return '单股上限不能超过行业上限'
  return ''
})

const reconcileValidationError = computed(() => {
  if (!isNonNegativeMoney(reconcileCash.value)) return '可用现金必须是非负十进制字符串'
  const symbols = new Set<string>()
  for (const position of reconcilePositions.value) {
    if (!/^\d{6}$/.test(position.symbol)) return '股票代码必须是六位数字'
    if (symbols.has(position.symbol)) return '持仓股票代码不能重复'
    symbols.add(position.symbol)
    if (!Number.isInteger(position.quantity) || position.quantity < 0) {
      return '持仓数量必须是非负整数'
    }
    if (!isPositiveMoney(position.average_cost)) return '平均成本必须是正数十进制字符串'
  }
  return ''
})

const cashValidationError = computed(() => {
  if (!isPositiveMoney(cashAmount.value)) return '请输入规范的正数金额'
  if (!cashOccurredAt.value || Number.isNaN(new Date(cashOccurredAt.value).getTime())) {
    return '请选择有效的发生时间'
  }
  if (cashNote.value.length > 256) return '备注不能超过 256 个字符'
  return ''
})

onMounted(loadPortfolio)

async function loadPortfolio() {
  initialLoading.value = true
  loadError.value = ''
  portfolioMissing.value = false
  try {
    await store.loadPortfolio()
  } catch (caught) {
    if (caught instanceof ApiError && caught.status === 404) {
      portfolioMissing.value = true
      store.error = null
    } else {
      loadError.value = errorMessage(caught)
    }
  } finally {
    initialLoading.value = false
  }
}

function formatPercent(value: number): string {
  return new Intl.NumberFormat('zh-CN', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

function riskLabel(value: InvestmentProfileInput['risk_level']): string {
  return { conservative: '稳健', balanced: '均衡', aggressive: '进取' }[value]
}

function decimalPattern(value: string): boolean {
  return /^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value)
}

function isNonNegativeMoney(value: Money): boolean {
  return decimalPattern(value)
}

function isPositiveMoney(value: Money): boolean {
  return decimalPattern(value) && /[1-9]/.test(value)
}

function percentage(value: string, minimum: number, maximum: number): number | null {
  if (!/^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value)) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= minimum && parsed <= maximum
    ? parsed / 100
    : null
}

function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String(error.message)
  }
  return String(error)
}

function detailMessage(error: unknown): string {
  if (!(error instanceof ApiError) || error.detail === undefined) return ''
  if (typeof error.detail === 'string') return error.detail
  try {
    return JSON.stringify(error.detail)
  } catch {
    return String(error.detail)
  }
}

function openProfileEditor() {
  const current = portfolio.value?.profile
  if (!current) return
  profileDraft.value = {
    investmentHorizonDays: String(current.investment_horizon_days),
    riskLevel: current.risk_level,
    maxDrawdown: String(current.max_drawdown * 100),
    maxStockWeight: String(current.max_stock_weight * 100),
    maxIndustryWeight: String(current.max_industry_weight * 100),
    minCashRatio: String(current.min_cash_ratio * 100),
    maxDailyTurnover: String(current.max_daily_turnover * 100),
  }
  profileError.value = ''
  profileDetail.value = ''
  profileOpen.value = true
}

async function submitProfile() {
  if (profileValidationError.value || !portfolio.value) return
  const draft = profileDraft.value
  const payload: InvestmentProfileInput = {
    investment_horizon_days: Number(draft.investmentHorizonDays),
    risk_level: draft.riskLevel,
    max_drawdown: percentage(draft.maxDrawdown, 3, 50) as number,
    max_stock_weight: percentage(draft.maxStockWeight, 1, 20) as number,
    max_industry_weight: percentage(draft.maxIndustryWeight, 5, 50) as number,
    min_cash_ratio: percentage(draft.minCashRatio, 0, 50) as number,
    max_daily_turnover: percentage(draft.maxDailyTurnover, 5, 100) as number,
  }
  profileSaving.value = true
  profileError.value = ''
  profileDetail.value = ''
  try {
    const updated = await store.updateProfile(payload)
    replaceDisplayedProfile(updated)
    profileOpen.value = false
  } catch (caught) {
    profileError.value = errorMessage(caught)
    profileDetail.value = detailMessage(caught)
  } finally {
    profileSaving.value = false
  }
}

function replaceDisplayedProfile(updated: InvestmentProfileResponse) {
  if (!store.portfolio) return
  store.portfolio = { ...store.portfolio, profile: updated }
}

function openReconcileEditor() {
  const current = portfolio.value
  if (!current) return
  reconcileCash.value = current.summary.cash
  reconcilePositions.value = current.positions.map(position => ({
    symbol: position.symbol,
    quantity: position.quantity,
    average_cost: position.average_cost,
  }))
  reconcileExpectedUpdatedAt.value = current.updated_at
  reconcileLatestUpdatedAt.value = ''
  reconcileError.value = ''
  reconcileDetail.value = ''
  reconcileConflict.value = false
  reconcileRefreshing.value = false
  reconcileRefreshError.value = ''
  reconcileOpen.value = true
}

async function submitReconcile() {
  if (reconcileValidationError.value) return
  reconcileSaving.value = true
  reconcileError.value = ''
  reconcileDetail.value = ''
  reconcileConflict.value = false
  reconcileLatestUpdatedAt.value = ''
  reconcileRefreshError.value = ''
  try {
    await store.reconcileHoldings({
      expected_updated_at: reconcileExpectedUpdatedAt.value,
      cash: reconcileCash.value,
      positions: reconcilePositions.value.map(position => ({ ...position })),
    })
    reconcileOpen.value = false
  } catch (caught) {
    reconcileError.value = errorMessage(caught)
    reconcileDetail.value = detailMessage(caught)
    if (caught instanceof ApiError && caught.status === 409) {
      reconcileConflict.value = true
      await refreshConflictLatest()
    }
  } finally {
    reconcileSaving.value = false
  }
}

async function refreshConflictLatest() {
  if (!reconcileConflict.value || reconcileRefreshing.value) return
  reconcileRefreshing.value = true
  reconcileRefreshError.value = ''
  reconcileLatestUpdatedAt.value = ''
  try {
    const latest = await store.loadPortfolio()
    reconcileLatestUpdatedAt.value = latest.updated_at
  } catch (caught) {
    reconcileRefreshError.value = `最新组合刷新失败：${errorMessage(caught)}`
  } finally {
    reconcileRefreshing.value = false
  }
}

function adoptLatestReconcileVersion() {
  if (!reconcileConflict.value || !reconcileLatestUpdatedAt.value) return
  reconcileExpectedUpdatedAt.value = reconcileLatestUpdatedAt.value
  reconcileConflict.value = false
  reconcileError.value = ''
  reconcileDetail.value = ''
  reconcileRefreshError.value = ''
}

function localDateTimeValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0')
  return [
    date.getFullYear(), '-', pad(date.getMonth() + 1), '-', pad(date.getDate()),
    'T', pad(date.getHours()), ':', pad(date.getMinutes()),
  ].join('')
}

function openCashMovement() {
  cashKind.value = 'deposit'
  cashAmount.value = ''
  cashOccurredAt.value = localDateTimeValue(new Date())
  cashNote.value = ''
  cashError.value = ''
  cashDetail.value = ''
  cashOpen.value = true
}

async function submitCashMovement() {
  if (cashValidationError.value) return
  cashSaving.value = true
  cashError.value = ''
  cashDetail.value = ''
  try {
    await store.recordCashMovement({
      kind: cashKind.value,
      amount: cashAmount.value,
      occurred_at: new Date(cashOccurredAt.value).toISOString(),
      note: cashNote.value,
    })
    cashOpen.value = false
  } catch (caught) {
    cashError.value = errorMessage(caught)
    cashDetail.value = detailMessage(caught)
  } finally {
    cashSaving.value = false
  }
}
</script>

<template>
  <BasicPage title="持仓" description="核对真实资金与持仓，并维护后续建议使用的投资画像。">
    <template #actions>
      <Button
        v-if="portfolio"
        data-testid="portfolio-profile-edit"
        type="button"
        variant="outline"
        @click="openProfileEditor"
      >
        <Settings2 class="size-4" />
        编辑画像
      </Button>
      <Button
        v-if="portfolio"
        data-testid="portfolio-reconcile"
        type="button"
        variant="outline"
        @click="openReconcileEditor"
      >
        <RefreshCw class="size-4" />
        对账
      </Button>
      <Button
        v-if="portfolio"
        data-testid="portfolio-cash-movement"
        type="button"
        @click="openCashMovement"
      >
        <Coins class="size-4" />
        记录现金流水
      </Button>
    </template>

    <div
      v-if="initialLoading"
      role="status"
      class="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground"
    >
      正在加载持仓…
    </div>

    <div
      v-else-if="loadError"
      role="alert"
      class="rounded-lg border border-destructive/40 bg-destructive/5 p-6"
    >
      <p class="font-medium text-destructive">加载持仓失败</p>
      <p class="mt-2 text-sm text-destructive">{{ loadError }}</p>
      <Button
        data-testid="portfolio-retry"
        class="mt-4"
        type="button"
        variant="outline"
        @click="loadPortfolio"
      >
        重试
      </Button>
    </div>

    <div
      v-else-if="portfolioMissing || !portfolio"
      class="rounded-lg border border-dashed p-10 text-center"
    >
      <WalletCards class="mx-auto size-9 text-muted-foreground" />
      <p class="mt-4 font-medium">尚未建立投资组合</p>
      <p class="mt-2 text-sm text-muted-foreground">请先完成组合初始化，再在这里维护持仓。</p>
      <Button
        data-testid="portfolio-retry"
        class="mt-4"
        type="button"
        variant="outline"
        @click="loadPortfolio"
      >
        重试
      </Button>
    </div>

    <template v-else>
      <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Card v-for="item in summaryItems" :key="item.label">
          <CardHeader class="pb-2">
            <CardDescription>{{ item.label }}</CardDescription>
          </CardHeader>
          <CardContent class="font-mono text-lg font-semibold">{{ item.value }}</CardContent>
        </Card>
      </section>

      <div
        v-if="portfolio.valuation_warnings.length"
        class="space-y-2 rounded-lg border border-amber-500/40 bg-amber-500/5 p-4 text-sm"
      >
        <p class="flex items-center gap-2 font-medium text-amber-700 dark:text-amber-300">
          <AlertTriangle class="size-4" />估值提醒
        </p>
        <p v-for="warning in portfolio.valuation_warnings" :key="warning">{{ warning }}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>投资画像</CardTitle>
          <CardDescription>画像版本 {{ portfolio.profile.version }}；修改后仅影响后续建议。</CardDescription>
        </CardHeader>
        <CardContent>
          <dl class="grid gap-x-8 gap-y-4 text-sm md:grid-cols-2 xl:grid-cols-4">
            <div><dt class="text-muted-foreground">风险等级</dt><dd class="mt-1 font-medium">{{ riskLabel(portfolio.profile.risk_level) }}</dd></div>
            <div><dt class="text-muted-foreground">投资期限</dt><dd class="mt-1 font-medium">{{ portfolio.profile.investment_horizon_days }} 个交易日</dd></div>
            <div><dt class="text-muted-foreground">最大回撤约束</dt><dd class="mt-1 font-medium">{{ formatPercent(portfolio.profile.max_drawdown) }}</dd></div>
            <div><dt class="text-muted-foreground">单股最大权重</dt><dd class="mt-1 font-medium">{{ formatPercent(portfolio.profile.max_stock_weight) }}</dd></div>
            <div><dt class="text-muted-foreground">单一行业最大比例</dt><dd class="mt-1 font-medium">{{ formatPercent(portfolio.profile.max_industry_weight) }}</dd></div>
            <div><dt class="text-muted-foreground">最低现金比例</dt><dd class="mt-1 font-medium">{{ formatPercent(portfolio.profile.min_cash_ratio) }}</dd></div>
            <div><dt class="text-muted-foreground">单日最大调仓比例</dt><dd class="mt-1 font-medium">{{ formatPercent(portfolio.profile.max_daily_turnover) }}</dd></div>
            <div><dt class="text-muted-foreground">生效状态</dt><dd class="mt-1 font-medium">{{ portfolio.profile.is_active ? '当前生效' : '历史版本' }}</dd></div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>持仓明细</CardTitle>
          <CardDescription>金额保留服务端返回的精确十进制字符串。</CardDescription>
        </CardHeader>
        <CardContent>
          <div v-if="portfolio.positions.length === 0" class="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
            暂无持仓；当前是有效的现金组合。
          </div>
          <div v-else class="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>股票</TableHead><TableHead>行业</TableHead><TableHead>数量</TableHead>
                  <TableHead>平均成本</TableHead><TableHead>最新收盘</TableHead><TableHead>市值</TableHead>
                  <TableHead>未实现盈亏</TableHead><TableHead>当前权重</TableHead><TableHead>目标权重</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <template v-for="position in portfolio.positions" :key="position.id">
                  <TableRow>
                    <TableCell><p class="font-medium">{{ position.name }}</p><p class="font-mono text-xs text-muted-foreground">{{ position.symbol }}</p></TableCell>
                    <TableCell>{{ position.industry ?? '—' }}</TableCell>
                    <TableCell>{{ position.quantity }}</TableCell>
                    <TableCell class="font-mono">{{ position.average_cost }}</TableCell>
                    <TableCell class="font-mono">{{ position.latest_close }}</TableCell>
                    <TableCell class="font-mono">{{ position.market_value }}</TableCell>
                    <TableCell class="font-mono">{{ position.unrealized_pnl }}</TableCell>
                    <TableCell>{{ formatPercent(position.current_weight) }}</TableCell>
                    <TableCell :data-testid="`position-target-${position.symbol}`">{{ position.target_weight === null ? '—' : formatPercent(position.target_weight) }}</TableCell>
                  </TableRow>
                  <TableRow v-if="position.valuation_warning" class="bg-amber-500/5">
                    <TableCell colspan="9" class="text-xs text-amber-700 dark:text-amber-300">
                      <span class="inline-flex items-center gap-2"><AlertTriangle class="size-3.5" />{{ position.valuation_warning }}</span>
                    </TableCell>
                  </TableRow>
                </template>
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </template>

    <Dialog :open="profileOpen" @update:open="profileOpen = $event">
      <DialogContent class="max-w-2xl">
        <DialogHeader><DialogTitle>编辑投资画像</DialogTitle><DialogDescription>保存会创建新的画像版本，比例按百分数填写。</DialogDescription></DialogHeader>
        <div class="grid gap-4 py-2 md:grid-cols-2">
          <div class="space-y-2"><Label for="profile-risk-level">风险等级</Label><select id="profile-risk-level" v-model="profileDraft.riskLevel" class="h-9 w-full rounded-md border bg-background px-3 text-sm"><option value="conservative">稳健</option><option value="balanced">均衡</option><option value="aggressive">进取</option></select></div>
          <div class="space-y-2"><Label for="profile-horizon-days">投资期限（交易日）</Label><Input id="profile-horizon-days" v-model="profileDraft.investmentHorizonDays" inputmode="numeric" /></div>
          <div class="space-y-2"><Label for="profile-max-drawdown">最大回撤（%）</Label><Input id="profile-max-drawdown" v-model="profileDraft.maxDrawdown" inputmode="decimal" /></div>
          <div class="space-y-2"><Label for="profile-max-stock-weight">单股最大权重（%）</Label><Input id="profile-max-stock-weight" v-model="profileDraft.maxStockWeight" inputmode="decimal" /></div>
          <div class="space-y-2"><Label for="profile-max-industry-weight">行业最大比例（%）</Label><Input id="profile-max-industry-weight" v-model="profileDraft.maxIndustryWeight" inputmode="decimal" /></div>
          <div class="space-y-2"><Label for="profile-min-cash-ratio">最低现金比例（%）</Label><Input id="profile-min-cash-ratio" v-model="profileDraft.minCashRatio" inputmode="decimal" /></div>
          <div class="space-y-2"><Label for="profile-max-daily-turnover">单日最大调仓（%）</Label><Input id="profile-max-daily-turnover" v-model="profileDraft.maxDailyTurnover" inputmode="decimal" /></div>
        </div>
        <p v-if="profileValidationError" class="text-sm text-destructive">{{ profileValidationError }}</p>
        <div v-if="profileError" role="alert" class="rounded-md border border-destructive/40 p-3 text-sm text-destructive"><p>{{ profileError }}</p><p v-if="profileDetail && profileDetail !== profileError" class="mt-1">{{ profileDetail }}</p><p class="mt-1 text-xs">编辑内容已保留。</p></div>
        <DialogFooter><Button type="button" variant="outline" @click="profileOpen = false">取消</Button><Button data-testid="profile-submit" type="button" :loading="profileSaving" :disabled="!!profileValidationError" @click="submitProfile">创建新版本</Button></DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog :open="reconcileOpen" @update:open="reconcileOpen = $event">
      <DialogScrollContent class="max-w-4xl">
        <DialogHeader><DialogTitle>核对现金与持仓</DialogTitle><DialogDescription>基准更新时间：{{ reconcileExpectedUpdatedAt }}。保存时会按此版本检查并发修改。</DialogDescription></DialogHeader>
        <HoldingsEditor v-model:cash="reconcileCash" v-model:positions="reconcilePositions" />
        <p v-if="reconcileValidationError" class="text-sm text-destructive">{{ reconcileValidationError }}</p>
        <div v-if="reconcileError" role="alert" class="rounded-md border border-destructive/40 p-3 text-sm text-destructive">
          <p>{{ reconcileError }}</p>
          <p v-if="reconcileDetail && reconcileDetail !== reconcileError" class="mt-1">{{ reconcileDetail }}</p>
          <template v-if="reconcileConflict">
            <p v-if="reconcileRefreshing" class="mt-2 font-medium">正在刷新最新组合版本…</p>
            <template v-else-if="reconcileLatestUpdatedAt">
              <p class="mt-2 font-medium">已获取最新组合版本：{{ reconcileLatestUpdatedAt }}</p>
              <p class="mt-1">请核对差异后重试；本次编辑不会自动重提。</p>
              <Button data-testid="reconcile-adopt-latest" class="mt-3" type="button" size="sm" variant="outline" @click="adoptLatestReconcileVersion">采用最新版本，保留当前编辑</Button>
            </template>
            <template v-else>
              <p class="mt-2 font-medium">最新组合尚未刷新，不能使用旧版本再次保存。</p>
              <p v-if="reconcileRefreshError" class="mt-1">{{ reconcileRefreshError }}</p>
              <Button data-testid="reconcile-refresh-latest" class="mt-3" type="button" size="sm" variant="outline" :loading="reconcileRefreshing" @click="refreshConflictLatest">重新刷新最新组合</Button>
            </template>
          </template>
          <p v-else class="mt-1 text-xs">现金与持仓编辑均已保留。</p>
        </div>
        <DialogFooter><Button type="button" variant="outline" @click="reconcileOpen = false">取消</Button><Button data-testid="reconcile-submit" type="button" :loading="reconcileSaving" :disabled="!!reconcileValidationError || reconcileConflict" @click="submitReconcile">保存对账</Button></DialogFooter>
      </DialogScrollContent>
    </Dialog>

    <Dialog :open="cashOpen" @update:open="cashOpen = $event">
      <DialogContent class="max-w-lg">
        <DialogHeader><DialogTitle>记录现金流水</DialogTitle><DialogDescription>资金进出与费用会独立记录，不直接计入投资收益。</DialogDescription></DialogHeader>
        <div class="space-y-4 py-2">
          <div class="space-y-2"><Label for="cash-kind">类型</Label><select id="cash-kind" v-model="cashKind" class="h-9 w-full rounded-md border bg-background px-3 text-sm"><option value="deposit">追加资金</option><option value="withdrawal">取出资金</option><option value="fee">手续费</option></select></div>
          <div class="space-y-2"><Label for="cash-amount">金额（CNY）</Label><Input id="cash-amount" v-model="cashAmount" inputmode="decimal" placeholder="例如 1000.00" /><p class="text-xs text-muted-foreground">金额按原始十进制字符串提交，不会去除空白或使用浮点换算。</p></div>
          <div class="space-y-2"><Label for="cash-occurred-at">发生时间</Label><Input id="cash-occurred-at" v-model="cashOccurredAt" type="datetime-local" /></div>
          <div class="space-y-2"><Label for="cash-note">备注</Label><textarea id="cash-note" v-model="cashNote" maxlength="256" class="min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm" /></div>
        </div>
        <p v-if="cashValidationError" class="text-sm text-destructive">{{ cashValidationError }}</p>
        <div v-if="cashError" role="alert" class="rounded-md border border-destructive/40 p-3 text-sm text-destructive"><p>{{ cashError }}</p><p v-if="cashDetail && cashDetail !== cashError" class="mt-1">{{ cashDetail }}</p><p class="mt-1 text-xs">编辑内容已保留。</p></div>
        <DialogFooter><Button type="button" variant="outline" @click="cashOpen = false">取消</Button><Button data-testid="cash-movement-submit" type="button" :loading="cashSaving" :disabled="!!cashValidationError" @click="submitCashMovement">保存流水</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  </BasicPage>
</template>
