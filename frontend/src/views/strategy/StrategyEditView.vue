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
`,
  params: '{"short_period": 5, "long_period": 20}',
  market: 'crypto',
})

const codeLines = computed(() => form.value.code.split('\n').length)

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

    const data = {
      name: form.value.name,
      description: form.value.description || undefined,
      code: form.value.code,
      params,
      market: form.value.market,
    }

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
          <div class="flex rounded-md border overflow-hidden bg-muted/50 font-mono text-sm">
            <div class="shrink-0 w-12 bg-muted border-r py-3 select-none text-right text-muted-foreground text-xs leading-relaxed">
              <div v-for="n in codeLines" :key="n" class="px-2 leading-relaxed">{{ n }}</div>
            </div>
            <textarea
              v-model="form.code"
              class="flex-1 min-h-[400px] p-3 bg-transparent border-0 outline-none resize-y font-mono text-sm leading-relaxed tab-size-4"
              spellcheck="false"
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
