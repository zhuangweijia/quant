<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Check, ChevronLeft, ChevronRight } from 'lucide-vue-next'

import { ApiError, type ValidationIssue } from '@/api/client'
import { BasicPage } from '@/components/global-layout'
import HoldingsEditor from '@/components/portfolio/HoldingsEditor.vue'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { usePortfolioStore } from '@/stores/portfolio'
import type {
  InvestmentProfileInput,
  Money,
  PortfolioSetupRequest,
  PositionInput,
  RiskLevel,
} from '@/types/portfolio'

const DRAFT_KEY = 'quant-desk:portfolio-setup:v1'
const DRAFT_VERSION = 1

const steps = ['风险与期限', '组合约束', '资金与持仓', '确认'] as const

interface ProfileForm {
  investmentHorizonDays: string
  riskLevel: RiskLevel
  maxDrawdown: string
  maxStockWeight: string
  maxIndustryWeight: string
  minCashRatio: string
  maxDailyTurnover: string
}

interface SetupDraft {
  version: 1
  currentStep: number
  profile: ProfileForm
  totalCapital: Money
  cash: Money
  positions: PositionInput[]
}

const riskDefaults: Record<
  RiskLevel,
  Pick<
    ProfileForm,
    | 'maxDrawdown'
    | 'maxStockWeight'
    | 'maxIndustryWeight'
    | 'minCashRatio'
    | 'maxDailyTurnover'
  >
> = {
  conservative: {
    maxDrawdown: '10',
    maxStockWeight: '5',
    maxIndustryWeight: '20',
    minCashRatio: '20',
    maxDailyTurnover: '20',
  },
  balanced: {
    maxDrawdown: '15',
    maxStockWeight: '8',
    maxIndustryWeight: '25',
    minCashRatio: '10',
    maxDailyTurnover: '30',
  },
  aggressive: {
    maxDrawdown: '25',
    maxStockWeight: '12',
    maxIndustryWeight: '35',
    minCashRatio: '5',
    maxDailyTurnover: '50',
  },
}

function defaultDraft(): SetupDraft {
  return {
    version: DRAFT_VERSION,
    currentStep: 0,
    profile: {
      investmentHorizonDays: '120',
      riskLevel: 'balanced',
      ...riskDefaults.balanced,
    },
    totalCapital: '',
    cash: '',
    positions: [],
  }
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isRiskLevel(value: unknown): value is RiskLevel {
  return value === 'conservative' || value === 'balanced' || value === 'aggressive'
}

function parseDraft(value: unknown): SetupDraft | null {
  if (!isPlainObject(value) || value.version !== DRAFT_VERSION) return null
  if (!Number.isInteger(value.currentStep) || Number(value.currentStep) < 0 || Number(value.currentStep) > 3) {
    return null
  }
  if (!isPlainObject(value.profile)) return null

  const profile = value.profile
  const investmentHorizonDays = profile.investmentHorizonDays
  const maxDrawdown = profile.maxDrawdown
  const maxStockWeight = profile.maxStockWeight
  const maxIndustryWeight = profile.maxIndustryWeight
  const minCashRatio = profile.minCashRatio
  const maxDailyTurnover = profile.maxDailyTurnover
  if (
    typeof investmentHorizonDays !== 'string' ||
    typeof maxDrawdown !== 'string' ||
    typeof maxStockWeight !== 'string' ||
    typeof maxIndustryWeight !== 'string' ||
    typeof minCashRatio !== 'string' ||
    typeof maxDailyTurnover !== 'string'
  ) {
    return null
  }
  if (!isRiskLevel(profile.riskLevel)) return null
  if (typeof value.totalCapital !== 'string' || typeof value.cash !== 'string') return null
  if (!Array.isArray(value.positions) || value.positions.length > 300) return null

  const positions: PositionInput[] = []
  for (const position of value.positions) {
    if (
      !isPlainObject(position) ||
      typeof position.symbol !== 'string' ||
      !Number.isInteger(position.quantity) ||
      Number(position.quantity) < 0 ||
      typeof position.average_cost !== 'string'
    ) {
      return null
    }
    positions.push({
      symbol: position.symbol,
      quantity: Number(position.quantity),
      average_cost: position.average_cost,
    })
  }

  return {
    version: DRAFT_VERSION,
    currentStep: Number(value.currentStep),
    profile: {
      investmentHorizonDays,
      riskLevel: profile.riskLevel,
      maxDrawdown,
      maxStockWeight,
      maxIndustryWeight,
      minCashRatio,
      maxDailyTurnover,
    },
    totalCapital: value.totalCapital,
    cash: value.cash,
    positions,
  }
}

function loadDraft(): SetupDraft {
  try {
    const saved = localStorage.getItem(DRAFT_KEY)
    if (!saved) return defaultDraft()
    const parsed = parseDraft(JSON.parse(saved))
    if (parsed) return parsed
    localStorage.removeItem(DRAFT_KEY)
  } catch {
    try {
      localStorage.removeItem(DRAFT_KEY)
    } catch {
      // Storage can be unavailable in privacy-restricted contexts.
    }
  }
  return defaultDraft()
}

const initialDraft = loadDraft()
const currentStep = ref(initialDraft.currentStep)
const profile = reactive<ProfileForm>({ ...initialDraft.profile })
const totalCapital = ref<Money>(initialDraft.totalCapital)
const cash = ref<Money>(initialDraft.cash)
const positions = ref<PositionInput[]>(initialDraft.positions.map(position => ({ ...position })))
const submitting = ref(false)
const submitError = ref('')
const submitDetail = ref('')

const router = useRouter()
const portfolioStore = usePortfolioStore()

function saveDraft() {
  const draft: SetupDraft = {
    version: DRAFT_VERSION,
    currentStep: currentStep.value,
    profile: { ...profile },
    totalCapital: totalCapital.value,
    cash: cash.value,
    positions: positions.value.map(position => ({ ...position })),
  }
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft))
  } catch {
    // The setup remains usable when storage is full or unavailable.
  }
}

watch(
  () => ({
    currentStep: currentStep.value,
    profile: { ...profile },
    totalCapital: totalCapital.value,
    cash: cash.value,
    positions: positions.value,
  }),
  saveDraft,
  { deep: true },
)

function applyRiskDefaults() {
  Object.assign(profile, riskDefaults[profile.riskLevel])
}

function integerInRange(value: string, minimum: number, maximum: number): boolean {
  if (!/^\d+$/.test(value)) return false
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed >= minimum && parsed <= maximum
}

function percentageInRange(value: string, minimum: number, maximum: number): boolean {
  if (!/^\d+(?:\.\d+)?$/.test(value)) return false
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= minimum && parsed <= maximum
}

function nonNegativeMoney(value: Money): boolean {
  return /^\d+(?:\.\d+)?$/.test(value.trim())
}

function positiveMoney(value: Money): boolean {
  const trimmed = value.trim()
  return nonNegativeMoney(trimmed) && /[1-9]/.test(trimmed)
}

const profileErrors = computed(() => ({
  investmentHorizonDays: integerInRange(profile.investmentHorizonDays, 20, 2520)
    ? ''
    : '投资期限需为 20–2520 个交易日',
  maxDrawdown: percentageInRange(profile.maxDrawdown, 3, 50)
    ? ''
    : '最大回撤需为 3%–50%',
  maxStockWeight: percentageInRange(profile.maxStockWeight, 1, 20)
    ? Number(profile.maxStockWeight) <= Number(profile.maxIndustryWeight)
      ? ''
      : '单只股票权重不能超过行业权重'
    : '单只股票最大权重需为 1%–20%',
  maxIndustryWeight: percentageInRange(profile.maxIndustryWeight, 5, 50)
    ? ''
    : '单一行业最大比例需为 5%–50%',
  minCashRatio: percentageInRange(profile.minCashRatio, 0, 50)
    ? ''
    : '最低现金比例需为 0%–50%',
  maxDailyTurnover: percentageInRange(profile.maxDailyTurnover, 5, 100)
    ? ''
    : '单日最大调仓比例需为 5%–100%',
}))

const positionErrors = computed(() => {
  const symbolCounts = new Map<string, number>()
  for (const position of positions.value) {
    const symbol = position.symbol.trim()
    if (/^\d{6}$/.test(symbol)) {
      symbolCounts.set(symbol, (symbolCounts.get(symbol) ?? 0) + 1)
    }
  }
  return positions.value.map(position => {
    const symbol = position.symbol.trim()
    return {
      symbol:
        !/^\d{6}$/.test(symbol) || (symbolCounts.get(symbol) ?? 0) > 1,
      quantity: !Number.isInteger(position.quantity) || position.quantity < 0,
      averageCost: !positiveMoney(position.average_cost),
    }
  })
})

const riskStepValid = computed(
  () => !profileErrors.value.investmentHorizonDays && !profileErrors.value.maxDrawdown,
)
const constraintStepValid = computed(
  () =>
    !profileErrors.value.maxStockWeight &&
    !profileErrors.value.maxIndustryWeight &&
    !profileErrors.value.minCashRatio &&
    !profileErrors.value.maxDailyTurnover,
)
const holdingsStepValid = computed(
  () =>
    positiveMoney(totalCapital.value) &&
    nonNegativeMoney(cash.value) &&
    positionErrors.value.every(errors => !Object.values(errors).some(Boolean)),
)
const stepValidity = computed(() => [
  riskStepValid.value,
  constraintStepValid.value,
  holdingsStepValid.value,
  riskStepValid.value && constraintStepValid.value && holdingsStepValid.value,
])
const canGoNext = computed(
  () => currentStep.value < steps.length - 1 && stepValidity.value[currentStep.value],
)
const canSubmit = computed(
  () => currentStep.value === steps.length - 1 && stepValidity.value.every(Boolean),
)

function nextStep() {
  if (!canGoNext.value) return
  submitError.value = ''
  submitDetail.value = ''
  currentStep.value += 1
}

function previousStep() {
  if (currentStep.value === 0) return
  submitError.value = ''
  submitDetail.value = ''
  currentStep.value -= 1
}

function toRatio(value: string): number {
  return Number(value) / 100
}

function setupPayload(): PortfolioSetupRequest {
  const profilePayload: InvestmentProfileInput = {
    investment_horizon_days: Number(profile.investmentHorizonDays),
    risk_level: profile.riskLevel,
    max_drawdown: toRatio(profile.maxDrawdown),
    max_stock_weight: toRatio(profile.maxStockWeight),
    max_industry_weight: toRatio(profile.maxIndustryWeight),
    min_cash_ratio: toRatio(profile.minCashRatio),
    max_daily_turnover: toRatio(profile.maxDailyTurnover),
  }
  return {
    profile: profilePayload,
    total_capital: totalCapital.value.trim(),
    cash: cash.value.trim(),
    positions: positions.value.map(position => ({
      symbol: position.symbol.trim(),
      quantity: position.quantity,
      average_cost: position.average_cost.trim(),
    })),
  }
}

function detailMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return ''
  const detail = error.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return (detail as ValidationIssue[])
      .map(issue => (isPlainObject(issue) && typeof issue.msg === 'string' ? issue.msg : ''))
      .filter(Boolean)
      .join('；')
  }
  if (!isPlainObject(detail)) return ''

  const labels: Record<string, string> = {
    server_valuation: '服务端估值',
    declared_total_capital: '填写的总资金',
    tolerance: '允许误差',
    valuation_warning: '估值提示',
  }
  return Object.entries(detail)
    .filter(([, value]) => typeof value === 'string' || typeof value === 'number')
    .map(([key, value]) => `${labels[key] ?? key}：${String(value)}`)
    .join('；')
}

async function submit() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  submitError.value = ''
  submitDetail.value = ''
  try {
    await portfolioStore.completeSetup(setupPayload())
    localStorage.removeItem(DRAFT_KEY)
    await router.push('/today')
  } catch (error) {
    submitError.value = error instanceof Error ? error.message : '组合初始化失败，请稍后重试'
    submitDetail.value = detailMessage(error)
    saveDraft()
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <BasicPage
    title="初始化投资组合"
    description="填写风险画像、组合约束与当前资金。进度会保存在此浏览器中。"
    class="mx-auto max-w-5xl"
  >
    <Card>
      <CardHeader class="space-y-5">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle>{{ steps[currentStep] }}</CardTitle>
            <CardDescription class="mt-2">
              第 {{ currentStep + 1 }} 步，共 {{ steps.length }} 步
            </CardDescription>
          </div>
          <span class="rounded-full bg-muted px-3 py-1 text-xs text-muted-foreground">
            草稿自动保存
          </span>
        </div>
        <Progress :model-value="((currentStep + 1) / steps.length) * 100" />
        <ol class="grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
          <li
            v-for="(step, index) in steps"
            :key="step"
            :class="[
              'rounded-md border px-3 py-2',
              index === currentStep
                ? 'border-primary bg-primary text-primary-foreground'
                : index < currentStep
                  ? 'bg-muted text-foreground'
                  : 'text-muted-foreground',
            ]"
          >
            {{ index + 1 }}. {{ step }}
          </li>
        </ol>
      </CardHeader>

      <CardContent>
        <section v-if="currentStep === 0" class="grid gap-6 md:grid-cols-2">
          <div class="space-y-2 md:col-span-2">
            <Label for="risk-level">风险等级</Label>
            <select
              id="risk-level"
              v-model="profile.riskLevel"
              class="border-input h-9 w-full rounded-md border bg-transparent px-3 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:max-w-sm"
              @change="applyRiskDefaults"
            >
              <option value="conservative">稳健</option>
              <option value="balanced">均衡</option>
              <option value="aggressive">积极</option>
            </select>
            <p class="text-xs text-muted-foreground">
              切换风险等级会填入默认约束，之后仍可逐项修改。
            </p>
          </div>

          <div class="space-y-2">
            <Label for="horizon-days">投资期限（交易日）</Label>
            <Input
              id="horizon-days"
              v-model="profile.investmentHorizonDays"
              type="number"
              min="20"
              max="2520"
              step="1"
              :aria-invalid="!!profileErrors.investmentHorizonDays"
            />
            <p v-if="profileErrors.investmentHorizonDays" class="text-sm text-destructive">
              {{ profileErrors.investmentHorizonDays }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="max-drawdown">可接受最大回撤（%）</Label>
            <Input
              id="max-drawdown"
              v-model="profile.maxDrawdown"
              type="number"
              min="3"
              max="50"
              step="0.1"
              :aria-invalid="!!profileErrors.maxDrawdown"
            />
            <p v-if="profileErrors.maxDrawdown" class="text-sm text-destructive">
              {{ profileErrors.maxDrawdown }}
            </p>
            <p class="text-xs text-muted-foreground">该值用于风险约束，不代表收益或回撤保证。</p>
          </div>
        </section>

        <section v-else-if="currentStep === 1" class="grid gap-6 md:grid-cols-2">
          <div class="space-y-2">
            <Label for="max-stock-weight">单只股票最大权重（%）</Label>
            <Input
              id="max-stock-weight"
              v-model="profile.maxStockWeight"
              type="number"
              min="1"
              max="20"
              step="0.1"
              :aria-invalid="!!profileErrors.maxStockWeight"
            />
            <p v-if="profileErrors.maxStockWeight" class="text-sm text-destructive">
              {{ profileErrors.maxStockWeight }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="max-industry-weight">单一行业最大比例（%）</Label>
            <Input
              id="max-industry-weight"
              v-model="profile.maxIndustryWeight"
              type="number"
              min="5"
              max="50"
              step="0.1"
              :aria-invalid="!!profileErrors.maxIndustryWeight"
            />
            <p v-if="profileErrors.maxIndustryWeight" class="text-sm text-destructive">
              {{ profileErrors.maxIndustryWeight }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="min-cash-ratio">最低现金比例（%）</Label>
            <Input
              id="min-cash-ratio"
              v-model="profile.minCashRatio"
              type="number"
              min="0"
              max="50"
              step="0.1"
              :aria-invalid="!!profileErrors.minCashRatio"
            />
            <p v-if="profileErrors.minCashRatio" class="text-sm text-destructive">
              {{ profileErrors.minCashRatio }}
            </p>
          </div>

          <div class="space-y-2">
            <Label for="max-daily-turnover">单日最大调仓比例（%）</Label>
            <Input
              id="max-daily-turnover"
              v-model="profile.maxDailyTurnover"
              type="number"
              min="5"
              max="100"
              step="0.1"
              :aria-invalid="!!profileErrors.maxDailyTurnover"
            />
            <p v-if="profileErrors.maxDailyTurnover" class="text-sm text-destructive">
              {{ profileErrors.maxDailyTurnover }}
            </p>
          </div>
        </section>

        <section v-else-if="currentStep === 2" class="space-y-7">
          <div class="grid gap-2 md:max-w-sm">
            <Label for="total-capital">总资金（CNY）</Label>
            <Input
              id="total-capital"
              v-model="totalCapital"
              inputmode="decimal"
              placeholder="例如 100000.00"
              :aria-invalid="!!totalCapital && !positiveMoney(totalCapital)"
            />
            <p v-if="totalCapital && !positiveMoney(totalCapital)" class="text-sm text-destructive">
              总资金必须是大于 0 的十进制数
            </p>
          </div>

          <HoldingsEditor
            :cash="cash"
            :positions="positions"
            :total-capital="totalCapital"
            @update:cash="cash = $event"
            @update:positions="positions = $event"
          />
        </section>

        <section v-else class="space-y-6">
          <div class="rounded-lg border bg-muted/30 p-4 text-sm">
            <p class="font-medium">提交前确认</p>
            <p class="mt-2 text-muted-foreground">
              系统只在本地检查格式。股票范围及总资金与最新行情估值的一致性，将由服务端校验。
            </p>
          </div>
          <dl class="grid gap-x-8 gap-y-4 text-sm md:grid-cols-2">
            <div>
              <dt class="text-muted-foreground">风险等级 / 投资期限</dt>
              <dd class="mt-1 font-medium">{{ profile.riskLevel }} / {{ profile.investmentHorizonDays }} 个交易日</dd>
            </div>
            <div>
              <dt class="text-muted-foreground">最大回撤</dt>
              <dd class="mt-1 font-medium">{{ profile.maxDrawdown }}%</dd>
            </div>
            <div>
              <dt class="text-muted-foreground">总资金 / 可用现金</dt>
              <dd class="mt-1 font-mono">{{ totalCapital }} / {{ cash }} CNY</dd>
            </div>
            <div>
              <dt class="text-muted-foreground">持仓数量</dt>
              <dd class="mt-1 font-medium">{{ positions.length }} 只</dd>
            </div>
            <div class="md:col-span-2">
              <dt class="text-muted-foreground">组合约束</dt>
              <dd class="mt-1">
                单股 {{ profile.maxStockWeight }}% · 行业 {{ profile.maxIndustryWeight }}% ·
                最低现金 {{ profile.minCashRatio }}% · 单日调仓 {{ profile.maxDailyTurnover }}%
              </dd>
            </div>
          </dl>

          <div
            v-if="submitError"
            role="alert"
            class="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
          >
            <p class="font-medium">{{ submitError }}</p>
            <p v-if="submitDetail && submitDetail !== submitError" class="mt-2">{{ submitDetail }}</p>
            <p class="mt-2 text-xs">输入与草稿均已保留，请核对后重试。</p>
          </div>
        </section>
      </CardContent>

      <CardFooter class="flex items-center justify-between gap-3 border-t pt-6">
        <Button
          data-testid="setup-back"
          type="button"
          variant="outline"
          :disabled="currentStep === 0 || submitting"
          @click="previousStep"
        >
          <ChevronLeft class="size-4" />
          返回
        </Button>

        <Button
          v-show="currentStep < steps.length - 1"
          data-testid="setup-next"
          type="button"
          :disabled="!canGoNext || submitting"
          @click="nextStep"
        >
          下一步
          <ChevronRight class="size-4" />
        </Button>

        <Button
          v-show="currentStep === steps.length - 1"
          data-testid="setup-submit"
          type="button"
          :loading="submitting"
          :disabled="!canSubmit || submitting"
          @click="submit"
        >
          <Check class="size-4" />
          保存并进入今日
        </Button>
      </CardFooter>
    </Card>
  </BasicPage>
</template>
