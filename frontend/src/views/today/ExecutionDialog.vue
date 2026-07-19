<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { ApiError } from '@/api/client'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogScrollContent,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAdviceStore } from '@/stores/advice'
import type {
  AdviceItemResponse,
  ExecutionDisposition,
  ExecutionRecordResponse,
  ExecutionUpdateRequest,
} from '@/types/advice'

const props = defineProps<{
  open: boolean
  item: AdviceItemResponse
  existingExecution?: ExecutionRecordResponse | null
}>()
const emit = defineEmits<{
  'update:open': [value: boolean]
  submit: [payload: ExecutionUpdateRequest]
  success: []
}>()

const adviceStore = useAdviceStore()
const disposition = ref<ExecutionDisposition>('executed')
const quantity = ref('')
const price = ref('')
const fee = ref('0')
const executedAt = ref('')
const reason = ref('')
const submitting = ref(false)
const validationErrors = ref<string[]>([])
const submitError = ref('')
const acknowledgementReason = ref('')
const acknowledgementPayload = ref<ExecutionUpdateRequest | null>(null)

const advisedQuantity = computed(() => Math.abs(props.item.delta_quantity))
const maximumQuantity = computed(() => {
  if (props.item.action === 'reduce' || props.item.action === 'exit') {
    return Math.min(advisedQuantity.value, props.item.current_quantity)
  }
  return advisedQuantity.value
})
const traded = computed(() => disposition.value !== 'skipped')
const revision = computed(() => props.existingExecution?.revision ?? 0)

function localDateTime(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function resetForm() {
  const existing = props.existingExecution
  disposition.value = existing?.disposition ?? 'executed'
  quantity.value = String(existing?.quantity ?? maximumQuantity.value)
  // Actual price is deliberately never copied from advice or a prior execution.
  price.value = ''
  fee.value = existing?.fee ?? '0'
  executedAt.value = localDateTime(existing?.executed_at ?? null)
  reason.value = existing?.reason ?? ''
  submitting.value = false
  validationErrors.value = []
  submitError.value = ''
  acknowledgementReason.value = ''
  acknowledgementPayload.value = null
  if (disposition.value === 'skipped') clearTradeFields()
}

function clearTradeFields() {
  quantity.value = '0'
  price.value = ''
  fee.value = '0'
  executedAt.value = ''
}

watch(
  () => [props.open, props.item.id, props.existingExecution] as const,
  ([open]) => { if (open) resetForm() },
  { immediate: true },
)

watch(disposition, value => {
  validationErrors.value = []
  submitError.value = ''
  acknowledgementReason.value = ''
  acknowledgementPayload.value = null
  if (value === 'skipped') {
    clearTradeFields()
  } else if (quantity.value === '0') {
    quantity.value = String(maximumQuantity.value)
  }
})

function canonicalNonNegativeMoney(value: string): boolean {
  return /^(?:0|[1-9]\d*)(?:\.\d+)?$/.test(value)
}

function canonicalPositiveMoney(value: string): boolean {
  return canonicalNonNegativeMoney(value) && /[1-9]/.test(value)
}

function parsedQuantity(): number | null {
  if (!/^[1-9]\d*$/.test(quantity.value)) return null
  const parsed = Number(quantity.value)
  return Number.isSafeInteger(parsed) ? parsed : null
}

function validate(): string[] {
  if (disposition.value === 'skipped') {
    return reason.value.trim() ? [] : ['未执行原因必填']
  }
  const errors: string[] = []
  const parsed = parsedQuantity()
  if (parsed === null) errors.push('成交数量必须是正整数')
  else {
    if (parsed > maximumQuantity.value) errors.push(`成交数量不能超过 ${maximumQuantity.value}`)
    if (disposition.value === 'executed' && parsed !== advisedQuantity.value) {
      errors.push(`全部执行数量必须等于建议调整数量 ${advisedQuantity.value}`)
    }
    if (disposition.value === 'partial' && parsed >= advisedQuantity.value) {
      errors.push('部分执行数量必须小于建议调整数量')
    }
  }
  if (!canonicalPositiveMoney(price.value)) errors.push('请输入规范的正数成交价')
  if (!canonicalNonNegativeMoney(fee.value)) errors.push('请输入规范的非负手续费')
  if (!executedAt.value || Number.isNaN(new Date(executedAt.value).getTime())) {
    errors.push('请选择有效成交时间')
  }
  return errors
}

function payload(acknowledgeOutsideAdvice: boolean): ExecutionUpdateRequest {
  if (disposition.value === 'skipped') {
    return {
      disposition: 'skipped',
      quantity: 0,
      price: null,
      fee: '0',
      executed_at: null,
      reason: reason.value,
      expected_revision: revision.value,
      acknowledge_outside_advice: acknowledgeOutsideAdvice,
    }
  }
  return {
    disposition: disposition.value,
    quantity: Number(quantity.value),
    price: price.value,
    fee: fee.value,
    executed_at: new Date(executedAt.value).toISOString(),
    reason: reason.value,
    expected_revision: revision.value,
    acknowledge_outside_advice: acknowledgeOutsideAdvice,
  }
}

function conflictCode(error: ApiError): string {
  const detail = error.detail
  if (typeof detail !== 'object' || detail === null || !('code' in detail)) return ''
  return typeof detail.code === 'string' ? detail.code : ''
}

function conflictReason(error: ApiError): string {
  const detail = error.detail
  if (typeof detail === 'object' && detail !== null && 'message' in detail && typeof detail.message === 'string') {
    return detail.message
  }
  return error.message
}

async function submit(acknowledgeOutsideAdvice = false) {
  if (submitting.value) return
  let update: ExecutionUpdateRequest
  if (acknowledgeOutsideAdvice) {
    if (!acknowledgementPayload.value) return
    update = {
      ...acknowledgementPayload.value,
      acknowledge_outside_advice: true,
    }
    validationErrors.value = []
  } else {
    validationErrors.value = validate()
    if (validationErrors.value.length) return
    update = payload(false)
  }
  submitting.value = true
  submitError.value = ''
  acknowledgementReason.value = ''
  acknowledgementPayload.value = null
  try {
    emit('submit', update)
    await adviceStore.updateExecution(props.item.id, update)
    emit('success')
    emit('update:open', false)
  } catch (caught) {
    if (
      caught instanceof ApiError &&
      caught.status === 409 &&
      conflictCode(caught) === 'outside_advice_requires_acknowledgement'
    ) {
      acknowledgementReason.value = conflictReason(caught)
      acknowledgementPayload.value = { ...update }
      submitError.value = ''
    } else if (caught instanceof ApiError && caught.status === 409) {
      submitError.value = `${conflictReason(caught)}。请刷新今日建议并核对持仓后再更正。`
    } else {
      submitError.value = caught instanceof Error ? caught.message : '执行记录保存失败，请稍后重试'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogScrollContent class="max-w-2xl">
      <DialogHeader>
        <DialogTitle>记录实际执行 · {{ item.name }} {{ item.symbol }}</DialogTitle>
        <DialogDescription>
          建议调整 {{ item.delta_quantity }} 股，参考价 {{ item.reference_price }}，修订版本 {{ revision }}。
          实际成交价不会预填，请按真实成交回报录入。
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-5 py-2">
        <div class="space-y-2">
          <Label for="execution-disposition">处理结果</Label>
          <select id="execution-disposition" v-model="disposition" class="h-9 w-full rounded-md border bg-background px-3 text-sm">
            <option value="executed">全部执行</option>
            <option value="partial">部分执行</option>
            <option value="skipped">未执行</option>
          </select>
        </div>

        <div v-if="traded" class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-2">
            <Label for="execution-quantity">成交数量</Label>
            <Input id="execution-quantity" v-model="quantity" type="number" min="1" :max="maximumQuantity" step="1" />
            <p class="text-xs text-muted-foreground">最多 {{ maximumQuantity }} 股；全部执行须等于建议调整数量。</p>
          </div>
          <div class="space-y-2">
            <Label for="execution-price">实际成交价（CNY）</Label>
            <Input id="execution-price" v-model="price" inputmode="decimal" autocomplete="off" />
          </div>
          <div class="space-y-2">
            <Label for="execution-fee">手续费（CNY）</Label>
            <Input id="execution-fee" v-model="fee" inputmode="decimal" />
          </div>
          <div class="space-y-2">
            <Label for="execution-time">成交时间</Label>
            <Input id="execution-time" v-model="executedAt" type="datetime-local" />
          </div>
        </div>

        <div class="space-y-2">
          <Label for="execution-reason">{{ traded ? '备注（可选）' : '未执行原因' }}</Label>
          <textarea id="execution-reason" v-model="reason" maxlength="512" class="min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm" />
        </div>

        <div v-if="existingExecution" class="rounded-md border bg-muted/30 p-3 text-xs text-muted-foreground">
          这是执行记录更正。若该股票已有后续组合事件，服务端会要求先到持仓页核对持仓；系统不会自动覆盖后续事件。
        </div>

        <div v-if="validationErrors.length" role="alert" class="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
          <p v-for="error in validationErrors" :key="error">{{ error }}</p>
        </div>
        <div v-if="submitError" role="alert" class="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">{{ submitError }}</div>
        <div v-if="acknowledgementReason" role="alert" class="rounded-md border border-amber-500/40 bg-amber-500/5 p-3 text-sm">
          <p>{{ acknowledgementReason }}</p>
          <p class="mt-1 text-xs text-muted-foreground">请确认这是实际成交。确认只针对本次超价带或过期建议记录。</p>
        </div>
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" :disabled="submitting" @click="emit('update:open', false)">取消</Button>
        <Button
          v-if="acknowledgementReason"
          data-testid="execution-acknowledge"
          type="button"
          variant="destructive"
          :loading="submitting"
          :disabled="submitting"
          @click="submit(true)"
        >仍记录为实际成交</Button>
        <Button
          v-else
          data-testid="execution-submit"
          type="button"
          :loading="submitting"
          :disabled="submitting"
          @click="submit(false)"
        >保存执行记录</Button>
      </DialogFooter>
    </DialogScrollContent>
  </Dialog>
</template>
