<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { toast } from 'vue-sonner'

import { ApiError, type ValidationIssue } from '@/api/client'
import { settingsApi, type SystemParams } from '@/api/settings'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
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

type NumericParamKey = Exclude<keyof SystemParams, 'stock_universe' | 'analysis_time'>

const loading = ref(true)
const saving = ref(false)
const resetting = ref(false)
const loadError = ref('')
const form = reactive<SystemParams>({
  data_retention_days: 90,
  alert_retention_days: 90,
  model_train_window_days: 756,
  model_val_window_days: 126,
  forward_return_days: 5,
  forward_return_threshold: 0.02,
  model_ic_threshold: 0.02,
  stock_universe: 'csi300',
  analysis_time: '17:00',
})
const savedBaseline = ref('')
const dirty = computed(() => JSON.stringify(form) !== savedBaseline.value)
const serverErrors = reactive<Partial<Record<keyof SystemParams, string>>>({})

function inRange(value: number, min: number, max: number) {
  return Number.isFinite(value) && value >= min && value <= max
}

const clientErrors = computed(() => ({
  data_retention_days: inRange(form.data_retention_days, 7, 3650)
    ? ''
    : '请输入 7–3650 天',
  alert_retention_days: inRange(form.alert_retention_days, 7, 3650)
    ? ''
    : '请输入 7–3650 天',
  model_train_window_days: inRange(form.model_train_window_days, 252, 2520)
    ? ''
    : '请输入 252–2520 个交易日',
  model_val_window_days:
    form.model_val_window_days >= form.model_train_window_days
      ? '验证窗口必须短于训练窗口'
      : inRange(form.model_val_window_days, 21, 504)
        ? ''
        : '请输入 21–504 个交易日',
  forward_return_days: inRange(form.forward_return_days, 1, 30)
    ? ''
    : '请输入 1–30 个交易日',
  forward_return_threshold:
    Number.isFinite(form.forward_return_threshold) &&
    form.forward_return_threshold > 0 &&
    form.forward_return_threshold <= 1
      ? ''
      : '请输入大于 0 且不超过 1 的数值',
  model_ic_threshold: inRange(form.model_ic_threshold, 0, 1) ? '' : '请输入 0–1 的数值',
  analysis_time: /^([01]\d|2[0-3]):[0-5]\d$/.test(form.analysis_time)
    ? ''
    : '请输入 HH:mm 时间',
}))
const errors = computed(() => ({ ...clientErrors.value, ...serverErrors }))
const valid = computed(() => Object.values(errors.value).every((value) => !value))

watch(
  form,
  () => {
    for (const key of Object.keys(serverErrors) as Array<keyof SystemParams>) {
      delete serverErrors[key]
    }
  },
  { deep: true },
)

function setNumber(key: NumericParamKey, value: string | number) {
  form[key] = Number(value)
}

function applyServerValidation(error: unknown) {
  if (!(error instanceof ApiError) || !Array.isArray(error.detail)) return
  for (const issue of error.detail as ValidationIssue[]) {
    const field = issue.loc[issue.loc.length - 1]
    if (typeof field === 'string' && field in form) {
      serverErrors[field as keyof SystemParams] = issue.msg
    }
  }
}

function applyServerParams(params: SystemParams) {
  Object.assign(form, params)
  savedBaseline.value = JSON.stringify(form)
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    applyServerParams((await settingsApi.getParams()).data)
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '系统参数加载失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!dirty.value || !valid.value) return
  saving.value = true
  try {
    applyServerParams((await settingsApi.updateParams({ ...form })).data)
    toast.success('系统参数已保存，将在后续任务中生效')
  } catch (error) {
    applyServerValidation(error)
    toast.error(error instanceof Error ? error.message : '系统参数保存失败')
  } finally {
    saving.value = false
  }
}

async function reset() {
  resetting.value = true
  try {
    applyServerParams((await settingsApi.resetParams()).data)
    toast.success('系统参数已恢复默认值')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '恢复默认参数失败')
  } finally {
    resetting.value = false
  }
}

onMounted(load)
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>系统参数</CardTitle>
      <CardDescription>
        保存后应用于后续分析或清理任务，不改变正在运行的任务。
      </CardDescription>
    </CardHeader>

    <CardContent v-if="loading" class="text-sm text-muted-foreground">
      正在加载系统参数…
    </CardContent>
    <CardContent v-else-if="loadError" class="space-y-3">
      <p class="text-sm text-destructive">{{ loadError }}</p>
      <Button type="button" variant="outline" @click="load">重试</Button>
    </CardContent>
    <CardContent v-else class="grid gap-6 lg:grid-cols-2">
      <fieldset class="space-y-4 rounded-lg border p-4">
        <legend class="px-1 text-sm font-medium">数据保留</legend>
        <div class="space-y-2">
          <Label for="data-retention">行情与日志（天）</Label>
          <Input
            id="data-retention"
            :model-value="form.data_retention_days"
            type="number"
            min="7"
            max="3650"
            step="1"
            :aria-invalid="!!errors.data_retention_days"
            @update:model-value="setNumber('data_retention_days', $event)"
          />
          <p v-if="errors.data_retention_days" class="text-sm text-destructive">
            {{ errors.data_retention_days }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="alert-retention">告警（天）</Label>
          <Input
            id="alert-retention"
            :model-value="form.alert_retention_days"
            type="number"
            min="7"
            max="3650"
            step="1"
            :aria-invalid="!!errors.alert_retention_days"
            @update:model-value="setNumber('alert_retention_days', $event)"
          />
          <p v-if="errors.alert_retention_days" class="text-sm text-destructive">
            {{ errors.alert_retention_days }}
          </p>
        </div>
      </fieldset>

      <fieldset class="space-y-4 rounded-lg border p-4">
        <legend class="px-1 text-sm font-medium">模型窗口</legend>
        <div class="space-y-2">
          <Label for="model-train-window">训练窗口（交易日）</Label>
          <Input
            id="model-train-window"
            :model-value="form.model_train_window_days"
            type="number"
            min="252"
            max="2520"
            step="1"
            :aria-invalid="!!errors.model_train_window_days"
            @update:model-value="setNumber('model_train_window_days', $event)"
          />
          <p v-if="errors.model_train_window_days" class="text-sm text-destructive">
            {{ errors.model_train_window_days }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="model-val-window">验证窗口（交易日）</Label>
          <Input
            id="model-val-window"
            :model-value="form.model_val_window_days"
            type="number"
            min="21"
            max="504"
            step="1"
            :aria-invalid="!!errors.model_val_window_days"
            @update:model-value="setNumber('model_val_window_days', $event)"
          />
          <p v-if="errors.model_val_window_days" class="text-sm text-destructive">
            {{ errors.model_val_window_days }}
          </p>
        </div>
      </fieldset>

      <fieldset class="space-y-4 rounded-lg border p-4">
        <legend class="px-1 text-sm font-medium">预测阈值</legend>
        <div class="space-y-2">
          <Label for="forward-return-days">前瞻窗口（交易日）</Label>
          <Input
            id="forward-return-days"
            :model-value="form.forward_return_days"
            type="number"
            min="1"
            max="30"
            step="1"
            :aria-invalid="!!errors.forward_return_days"
            @update:model-value="setNumber('forward_return_days', $event)"
          />
          <p v-if="errors.forward_return_days" class="text-sm text-destructive">
            {{ errors.forward_return_days }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="forward-return-threshold">收益阈值</Label>
          <Input
            id="forward-return-threshold"
            :model-value="form.forward_return_threshold"
            type="number"
            min="0.0001"
            max="1"
            step="0.001"
            :aria-invalid="!!errors.forward_return_threshold"
            @update:model-value="setNumber('forward_return_threshold', $event)"
          />
          <p v-if="errors.forward_return_threshold" class="text-sm text-destructive">
            {{ errors.forward_return_threshold }}
          </p>
        </div>
        <div class="space-y-2">
          <Label for="model-ic-threshold">IC 阈值</Label>
          <Input
            id="model-ic-threshold"
            :model-value="form.model_ic_threshold"
            type="number"
            min="0"
            max="1"
            step="0.001"
            :aria-invalid="!!errors.model_ic_threshold"
            @update:model-value="setNumber('model_ic_threshold', $event)"
          />
          <p v-if="errors.model_ic_threshold" class="text-sm text-destructive">
            {{ errors.model_ic_threshold }}
          </p>
        </div>
      </fieldset>

      <fieldset class="space-y-4 rounded-lg border p-4">
        <legend class="px-1 text-sm font-medium">范围与计划</legend>
        <div class="space-y-2">
          <Label for="stock-universe">股票池</Label>
          <Input id="stock-universe" model-value="沪深 300" disabled />
        </div>
        <div class="space-y-2">
          <Label for="analysis-time">每日分析时间</Label>
          <Input
            id="analysis-time"
            v-model="form.analysis_time"
            type="time"
            :aria-invalid="!!errors.analysis_time"
          />
          <p v-if="errors.analysis_time" class="text-sm text-destructive">
            {{ errors.analysis_time }}
          </p>
        </div>
      </fieldset>
    </CardContent>

    <CardFooter v-if="!loading && !loadError" class="justify-end gap-2">
      <AlertDialog>
        <AlertDialogTrigger as-child>
          <Button type="button" data-testid="system-params-reset" variant="outline">
            恢复默认值
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>恢复默认系统参数？</AlertDialogTitle>
            <AlertDialogDescription>
              数据库中的参数覆盖将被移除，后续任务使用启动默认值。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              data-testid="system-params-reset-confirm"
              :disabled="resetting"
              @click="reset"
            >
              确认恢复
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <Button
        type="button"
        data-testid="system-params-save"
        :loading="saving"
        :disabled="!dirty || !valid || saving"
        @click="save"
      >
        保存系统参数
      </Button>
    </CardFooter>
  </Card>
</template>
