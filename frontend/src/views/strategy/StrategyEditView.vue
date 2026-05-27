<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { strategyApi } from '@/api/strategy'
import { MARKET_LABELS } from '@/utils/constants'
import { BasicPage } from '@/components/global-layout'
import Button from '@/components/ui/button/Button.vue'
import Label from '@/components/ui/label/Label.vue'
import Input from '@/components/ui/input/Input.vue'
import {
  Select as UiSelect,
  SelectContent as UiSelectContent,
  SelectItem as UiSelectItem,
  SelectTrigger as UiSelectTrigger,
  SelectValue as UiSelectValue,
} from '@/components/ui/select'
import {
  Card as UiCard,
  CardContent as UiCardContent,
} from '@/components/ui/card'
import { ArrowLeft } from 'lucide-vue-next'
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'

const route = useRoute()
const router = useRouter()
const isEdit = computed(() => !!route.params.id)
const loading = ref(false)

const form = ref({
  name: '',
  description: '',
  code: `from app.core.types import BaseStrategy, BarData

class MyStrategy(BaseStrategy):
    def on_init(self, context):
        self.short_period = self.params.get("short_period", 5)
        self.long_period = self.params.get("long_period", 20)

    def on_bar(self, bar: BarData):
        bars = self.get_bars(bar.symbol, self.long_period + 1)
        if len(bars) < self.long_period:
            return
        short_avg = sum(b.close for b in bars[-self.short_period:]) / self.short_period
        long_avg = sum(b.close for b in bars[-self.long_period:]) / self.long_period

        if short_avg > long_avg and self.get_position(bar.symbol) <= 0:
            self.buy(bar.symbol, qty=1.0)
        elif short_avg < long_avg and self.get_position(bar.symbol) > 0:
            self.sell(bar.symbol, qty=self.get_position(bar.symbol))
`,
  params: '{"short_period": 5, "long_period": 20}',
  market: 'crypto',
  symbol: '',
  timeframe: '1d',
})

const cmExtensions = [python(), oneDark]

onMounted(async () => {
  if (isEdit.value) {
    loading.value = true
    try {
      const res: any = await strategyApi.get(route.params.id as string)
      const s = res.data
      form.value = {
        name: s.name,
        description: s.description || '',
        code: s.code,
        params: s.params ? JSON.stringify(s.params, null, 2) : '{}',
        market: s.market,
        symbol: s.symbol || '',
        timeframe: s.timeframe || '1d',
      }
    } catch {
      toast.error('策略加载失败')
      router.push('/strategy')
    } finally { loading.value = false }
  }
})

async function handleSave() {
  if (!form.value.name) { toast.error('请输入策略名称'); return }
  if (!form.value.code?.trim()) { toast.error('请输入策略代码'); return }

  loading.value = true
  try {
    let params = {}
    try { params = JSON.parse(form.value.params || '{}') }
    catch { toast.error('策略参数 JSON 格式错误'); loading.value = false; return }

    const data: any = {
      name: form.value.name,
      description: form.value.description || undefined,
      code: form.value.code,
      params,
      market: form.value.market,
    }
    if (form.value.symbol) data.symbol = form.value.symbol
    if (form.value.timeframe) data.timeframe = form.value.timeframe

    if (isEdit.value) {
      await strategyApi.update(route.params.id as string, data)
      toast.success('策略已更新')
    } else {
      await strategyApi.create(data)
      toast.success('策略已创建')
    }
    router.push('/strategy')
  } catch (e: any) { toast.error(e.message || '保存失败') }
  finally { loading.value = false }
}
</script>

<template>
  <BasicPage :title="isEdit ? '编辑策略' : '创建策略'">
    <template #actions>
      <Button variant="ghost" @click="router.push('/strategy')">
        <ArrowLeft class="mr-2 size-4" />
        返回列表
      </Button>
    </template>

    <UiCard>
      <UiCardContent class="pt-6 space-y-6 max-w-4xl">
        <div class="grid gap-6 sm:grid-cols-2">
          <div class="space-y-2">
            <Label for="name">策略名称</Label>
            <Input id="name" v-model="form.name" placeholder="输入策略名称" />
          </div>
          <div class="space-y-2">
            <Label>目标市场</Label>
            <UiSelect v-model="form.market" :disabled="isEdit">
              <UiSelectTrigger>
                <UiSelectValue placeholder="选择市场" />
              </UiSelectTrigger>
              <UiSelectContent>
                <UiSelectItem v-for="(label, value) in MARKET_LABELS" :key="value" :value="value as string">
                  {{ label }}
                </UiSelectItem>
              </UiSelectContent>
            </UiSelect>
          </div>
        </div>

        <div class="grid gap-6 sm:grid-cols-2">
          <div class="space-y-2">
            <Label for="symbol">交易标的 (Symbol)</Label>
            <Input id="symbol" v-model="form.symbol" placeholder="如 BTCUSDT / AAPL / 000001" />
          </div>
          <div class="space-y-2">
            <Label>时间周期</Label>
            <UiSelect v-model="form.timeframe">
              <UiSelectTrigger>
                <UiSelectValue placeholder="选择周期" />
              </UiSelectTrigger>
              <UiSelectContent>
                <UiSelectItem value="1m">1 分钟</UiSelectItem>
                <UiSelectItem value="5m">5 分钟</UiSelectItem>
                <UiSelectItem value="15m">15 分钟</UiSelectItem>
                <UiSelectItem value="30m">30 分钟</UiSelectItem>
                <UiSelectItem value="1h">1 小时</UiSelectItem>
                <UiSelectItem value="4h">4 小时</UiSelectItem>
                <UiSelectItem value="1d">1 天</UiSelectItem>
                <UiSelectItem value="1w">1 周</UiSelectItem>
              </UiSelectContent>
            </UiSelect>
          </div>
        </div>

        <div class="space-y-2">
          <Label for="description">描述</Label>
          <textarea
            id="description"
            v-model="form.description"
            class="flex min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            placeholder="策略描述（可选）"
            rows="2"
          />
        </div>

        <div class="space-y-2">
          <Label>策略代码</Label>
          <div class="border rounded-md overflow-hidden">
            <Codemirror
              v-model="form.code"
              :extensions="cmExtensions"
              :style="{ height: '400px' }"
            />
          </div>
        </div>

        <div class="space-y-2">
          <Label for="params">策略参数 (JSON)</Label>
          <textarea
            id="params"
            v-model="form.params"
            class="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            rows="6"
            placeholder="JSON 格式"
          />
        </div>

        <div class="flex gap-3">
          <Button :loading="loading" @click="handleSave">
            {{ isEdit ? '更新策略' : '创建策略' }}
          </Button>
          <Button variant="outline" @click="router.push('/strategy')">取消</Button>
        </div>
      </UiCardContent>
    </UiCard>
  </BasicPage>
</template>