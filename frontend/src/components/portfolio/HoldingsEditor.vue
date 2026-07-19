<script setup lang="ts">
import { computed } from 'vue'
import { Plus, Trash2 } from 'lucide-vue-next'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { Money, PositionInput } from '@/types/portfolio'

const props = defineProps<{
  cash: Money
  positions: PositionInput[]
  totalCapital?: Money
}>()

const emit = defineEmits<{
  'update:cash': [value: Money]
  'update:positions': [value: PositionInput[]]
}>()

const symbolCounts = computed(() => {
  const counts = new Map<string, number>()
  for (const position of props.positions) {
    const symbol = position.symbol
    if (/^\d{6}$/.test(symbol)) {
      counts.set(symbol, (counts.get(symbol) ?? 0) + 1)
    }
  }
  return counts
})

function symbolError(position: PositionInput): string {
  const symbol = position.symbol
  if (!/^\d{6}$/.test(symbol)) return '股票代码必须是六位数字'
  if ((symbolCounts.value.get(symbol) ?? 0) > 1) return '持仓股票代码不能重复'
  return ''
}

function quantityError(quantity: number): string {
  return Number.isInteger(quantity) && quantity >= 0 ? '' : '持仓数量必须是非负整数'
}

function costError(cost: Money): string {
  return isPositiveDecimal(cost) ? '' : '平均成本必须是大于 0 的十进制数'
}

function cashError(value: Money): string {
  return /^\d+(?:\.\d+)?$/.test(value) ? '' : '可用现金必须是非负十进制数'
}

function isPositiveDecimal(value: string): boolean {
  if (!/^\d+(?:\.\d+)?$/.test(value)) return false
  return /[1-9]/.test(value)
}

function updatePosition<K extends keyof PositionInput>(
  index: number,
  key: K,
  value: PositionInput[K],
) {
  emit(
    'update:positions',
    props.positions.map((position, positionIndex) =>
      positionIndex === index ? { ...position, [key]: value } : { ...position },
    ),
  )
}

function updateSymbol(index: number, value: string | number) {
  updatePosition(index, 'symbol', String(value))
}

function updateQuantity(index: number, value: string | number) {
  const text = String(value)
  updatePosition(index, 'quantity', text === '' ? Number.NaN : Number(text))
}

function updateCost(index: number, value: string | number) {
  updatePosition(index, 'average_cost', String(value))
}

function addPosition() {
  emit('update:positions', [
    ...props.positions.map(position => ({ ...position })),
    { symbol: '', quantity: 0, average_cost: '' },
  ])
}

function removePosition(index: number) {
  emit(
    'update:positions',
    props.positions.filter((_, positionIndex) => positionIndex !== index).map(position => ({
      ...position,
    })),
  )
}

function multiplyDecimalByInteger(value: Money, quantity: number): string {
  if (!/^\d+(?:\.\d+)?$/.test(value) || !Number.isSafeInteger(quantity) || quantity < 0) {
    return '—'
  }

  const [whole, fraction = ''] = value.split('.')
  const scaled = BigInt(`${whole}${fraction}`) * BigInt(quantity)
  if (fraction.length === 0) return scaled.toString()

  const padded = scaled.toString().padStart(fraction.length + 1, '0')
  const wholeResult = padded.slice(0, -fraction.length)
  const fractionResult = padded.slice(-fraction.length).replace(/0+$/, '')
  return fractionResult ? `${wholeResult}.${fractionResult}` : wholeResult
}
</script>

<template>
  <div data-testid="holdings-editor" class="space-y-5">
    <div class="grid gap-2 md:max-w-sm">
      <Label for="portfolio-cash">可用现金（CNY）</Label>
      <Input
        id="portfolio-cash"
        :model-value="cash"
        inputmode="decimal"
        placeholder="例如 100000.00"
        :aria-invalid="!!cashError(cash)"
        @update:model-value="emit('update:cash', String($event))"
      />
      <p v-if="cashError(cash)" class="text-xs text-destructive">
        {{ cashError(cash) }}
      </p>
      <p class="text-xs text-muted-foreground">
        金额按输入的十进制字符串保存，不进行浮点换算。
        <span v-if="totalCapital">总资金：{{ totalCapital }}</span>
      </p>
    </div>

    <div class="flex items-center justify-between gap-4">
      <div>
        <h3 class="text-sm font-medium">当前持仓</h3>
        <p class="mt-1 text-xs text-muted-foreground">没有持仓时可仅填写现金。</p>
      </div>
      <Button data-testid="holding-add" type="button" variant="outline" size="sm" @click="addPosition">
        <Plus class="size-4" />
        添加持仓
      </Button>
    </div>

    <p v-if="positions.length === 0" class="rounded-lg border border-dashed p-4 text-sm text-muted-foreground">
      暂无持仓，将以现金组合完成初始化。
    </p>

    <div v-else class="space-y-3">
      <div
        v-for="(position, index) in positions"
        :key="index"
        class="grid gap-4 rounded-lg border p-4 md:grid-cols-[1fr_1fr_1fr_auto]"
      >
        <div class="space-y-2">
          <Label :for="`holding-symbol-${index}`">股票代码</Label>
          <Input
            :id="`holding-symbol-${index}`"
            :model-value="position.symbol"
            inputmode="numeric"
            maxlength="6"
            placeholder="六位数字"
            :aria-invalid="!!symbolError(position)"
            @update:model-value="updateSymbol(index, $event)"
          />
          <p
            v-if="symbolError(position)"
            data-testid="holding-symbol-error"
            class="text-xs text-destructive"
          >
            {{ symbolError(position) }}
          </p>
        </div>

        <div class="space-y-2">
          <Label :for="`holding-quantity-${index}`">数量（股）</Label>
          <Input
            :id="`holding-quantity-${index}`"
            :model-value="position.quantity"
            type="number"
            min="0"
            step="1"
            :aria-invalid="!!quantityError(position.quantity)"
            @update:model-value="updateQuantity(index, $event)"
          />
          <p v-if="quantityError(position.quantity)" class="text-xs text-destructive">
            {{ quantityError(position.quantity) }}
          </p>
        </div>

        <div class="space-y-2">
          <Label :for="`holding-cost-${index}`">平均成本（CNY）</Label>
          <Input
            :id="`holding-cost-${index}`"
            :model-value="position.average_cost"
            inputmode="decimal"
            placeholder="例如 10.25"
            :aria-invalid="!!costError(position.average_cost)"
            @update:model-value="updateCost(index, $event)"
          />
          <p v-if="costError(position.average_cost)" class="text-xs text-destructive">
            {{ costError(position.average_cost) }}
          </p>
        </div>

        <div class="flex items-start justify-between gap-3 md:flex-col md:items-end">
          <div class="text-right text-xs text-muted-foreground">
            <span class="block">成本金额</span>
            <strong
              :data-testid="`holding-value-${index}`"
              class="mt-1 block font-mono text-sm text-foreground"
            >
              {{ multiplyDecimalByInteger(position.average_cost, position.quantity) }}
            </strong>
          </div>
          <Button
            :data-testid="`holding-remove-${index}`"
            type="button"
            variant="ghost"
            size="icon"
            :aria-label="`删除持仓 ${index + 1}`"
            @click="removePosition(index)"
          >
            <Trash2 class="size-4" />
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>
