<script setup lang="ts">
import { ref, computed, h } from 'vue'
import { toast } from 'vue-sonner'
import { useRiskStore } from '@/stores/risk'
import {
  useRiskRules,
  useRiskAlerts,
  useUnreadAlertCount,
  useCreateRule,
  useUpdateRule,
  useToggleRule,
  useDeleteRule,
} from '@/composables/useRiskQuery'
import { formatDate } from '@/utils/format'
import { BasicPage } from '@/components/global-layout'
import { DataTable } from '@/components/data-table'
import type { ColumnDef } from '@tanstack/vue-table'
import Button from '@/components/ui/button/Button.vue'
import Badge from '@/components/ui/badge/Badge.vue'
import Label from '@/components/ui/label/Label.vue'
import Input from '@/components/ui/input/Input.vue'
import {
  Card as UiCard,
  CardHeader as UiCardHeader,
  CardContent as UiCardContent,
  CardTitle as UiCardTitle,
} from '@/components/ui/card'
import {
  Tabs as UiTabs,
  TabsContent as UiTabsContent,
  TabsList as UiTabsList,
  TabsTrigger as UiTabsTrigger,
} from '@/components/ui/tabs'
import {
  Select as UiSelect,
  SelectContent as UiSelectContent,
  SelectItem as UiSelectItem,
  SelectTrigger as UiSelectTrigger,
  SelectValue as UiSelectValue,
} from '@/components/ui/select'
import UiSwitch from '@/components/ui/switch/Switch.vue'
import {
  Dialog as UiDialog,
  DialogContent as UiDialogContent,
  DialogHeader as UiDialogHeader,
  DialogTitle as UiDialogTitle,
  DialogDescription as UiDialogDescription,
} from '@/components/ui/dialog'
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
import { Plus } from 'lucide-vue-next'

const store = useRiskStore()
const activeTab = ref('rules')

const { data: rules, isLoading: rulesLoading } = useRiskRules()
const { data: unreadCount } = useUnreadAlertCount()

const alertParams = computed(() => ({ page: 1, page_size: 50 }))
const { data: alertsData, isLoading: alertsLoading } = useRiskAlerts(alertParams)

const createRuleMut = useCreateRule()
const updateRuleMut = useUpdateRule()
const toggleRuleMut = useToggleRule()
const deleteRuleMut = useDeleteRule()

const dialogOpen = ref(false)
const editingRule = ref<any>(null)
const ruleForm = ref({
  name: '',
  metric: '',
  condition: 'gt',
  threshold: '',
  level: 'medium',
  cooldown_minutes: 60,
})

const deleteTarget = ref<string | null>(null)

const ruleColumns: ColumnDef<any>[] = [
  { accessorKey: 'name', header: '规则名称', cell: ({ row }) => h('span', { class: 'font-medium' }, row.getValue('name')) },
  {
    accessorKey: 'metric',
    header: '指标',
    cell: ({ row }) => h(Badge, { variant: 'outline' }, () => row.getValue('metric')),
  },
  {
    accessorKey: 'condition',
    header: '条件',
    cell: ({ row }) => `${row.getValue('condition')} ${row.original.threshold}`,
  },
  {
    accessorKey: 'level',
    header: '级别',
    cell: ({ row }) => {
      const level = row.getValue('level') as string
      const variant = level === 'high' ? 'destructive' : level === 'medium' ? 'default' : 'secondary'
      return h(Badge, { variant }, () => level)
    },
  },
  {
    accessorKey: 'enabled',
    header: '状态',
    cell: ({ row }) => h(UiSwitch, {
      checked: row.getValue('enabled'),
      'onUpdate:checked': () => handleToggle(row.original),
    }),
  },
  {
    id: 'actions',
    header: '',
    cell: ({ row }) => h('div', { class: 'flex gap-1' }, [
      h(Button, { size: 'sm', variant: 'ghost', onClick: () => openEdit(row.original) }, () => '编辑'),
      h(Button, { size: 'sm', variant: 'ghost', class: 'text-destructive', onClick: () => { deleteTarget.value = row.original.id } }, () => '删除'),
    ]),
  },
]

const alertColumns: ColumnDef<any>[] = [
  { accessorKey: 'rule_name', header: '规则', cell: ({ row }) => h('span', { class: 'font-medium' }, row.original.rule_name || '—') },
  {
    accessorKey: 'level',
    header: '级别',
    cell: ({ row }) => {
      const level = row.getValue('level') as string
      const variant = level === 'high' ? 'destructive' : level === 'medium' ? 'default' : 'secondary'
      return h(Badge, { variant }, () => level)
    },
  },
  { accessorKey: 'message', header: '消息' },
  {
    accessorKey: 'is_read',
    header: '状态',
    cell: ({ row }) => row.original.is_read
      ? h(Badge, { variant: 'secondary' }, () => '已读')
      : h(Badge, { variant: 'default' }, () => '未读'),
  },
  { accessorKey: 'created_at', header: '时间', cell: ({ row }) => formatDate(row.getValue('created_at')) },
]

function openCreate() {
  editingRule.value = null
  ruleForm.value = { name: '', metric: '', condition: 'gt', threshold: '', level: 'medium', cooldown_minutes: 60 }
  dialogOpen.value = true
}

function openEdit(rule: any) {
  editingRule.value = rule
  ruleForm.value = {
    name: rule.name,
    metric: rule.metric,
    condition: rule.condition,
    threshold: String(rule.threshold),
    level: rule.level,
    cooldown_minutes: rule.cooldown_minutes,
  }
  dialogOpen.value = true
}

async function handleSaveRule() {
  if (!ruleForm.value.name || !ruleForm.value.metric || !ruleForm.value.threshold) {
    toast.error('请填写完整的规则信息')
    return
  }
  try {
    const data = { ...ruleForm.value, threshold: Number(ruleForm.value.threshold) }
    if (editingRule.value) {
      await updateRuleMut.mutateAsync({ id: editingRule.value.id, data: data as any })
      toast.success('规则已更新')
    } else {
      await createRuleMut.mutateAsync(data as any)
      toast.success('规则已创建')
    }
    dialogOpen.value = false
  } catch (e: any) { toast.error(e.message || '保存失败') }
}

async function handleToggle(rule: any) {
  try {
    await toggleRuleMut.mutateAsync(rule.id)
  } catch (e: any) { toast.error(e.message || '操作失败') }
}

async function handleDelete() {
  if (!deleteTarget.value) return
  try {
    await deleteRuleMut.mutateAsync(deleteTarget.value)
    toast.success('规则已删除')
  } catch (e: any) { toast.error(e.message || '删除失败') }
  finally { deleteTarget.value = null }
}
</script>

<template>
  <BasicPage title="风控" description="管理风控规则和告警通知">
    <template #actions>
      <Button @click="openCreate">
        <Plus class="mr-2 size-4" />
        新增规则
      </Button>
    </template>

    <UiTabs v-model="activeTab">
      <UiTabsList>
        <UiTabsTrigger value="rules">风控规则</UiTabsTrigger>
        <UiTabsTrigger value="alerts">
          告警记录
          <span v-if="(unreadCount ?? 0) > 0" class="ml-1.5 flex size-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground text-[10px]">
            {{ (unreadCount ?? 0) > 99 ? '99+' : unreadCount }}
          </span>
        </UiTabsTrigger>
      </UiTabsList>

      <UiTabsContent value="rules" class="mt-4">
        <DataTable :columns="ruleColumns" :data="rules ?? []" :total="(rules ?? []).length" :page-size="50" :loading="rulesLoading" />
      </UiTabsContent>

      <UiTabsContent value="alerts" class="mt-4">
        <DataTable :columns="alertColumns" :data="alertsData?.items ?? []" :total="alertsData?.total ?? 0" :page-size="50" :loading="alertsLoading" />
      </UiTabsContent>
    </UiTabs>

    <UiDialog v-model:open="dialogOpen">
      <UiDialogContent>
        <UiDialogHeader>
          <UiDialogTitle>{{ editingRule ? '编辑规则' : '新增规则' }}</UiDialogTitle>
          <UiDialogDescription>配置风控规则的触发条件</UiDialogDescription>
        </UiDialogHeader>
        <div class="space-y-4">
          <div class="space-y-2">
            <Label>规则名称</Label>
            <Input v-model="ruleForm.name" placeholder="如：最大回撤限制" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>监控指标</Label>
              <Input v-model="ruleForm.metric" placeholder="如：drawdown" />
            </div>
            <div class="space-y-2">
              <Label>条件</Label>
              <UiSelect v-model="ruleForm.condition">
                <UiSelectTrigger><UiSelectValue /></UiSelectTrigger>
                <UiSelectContent>
                  <UiSelectItem value="gt">大于</UiSelectItem>
                  <UiSelectItem value="lt">小于</UiSelectItem>
                  <UiSelectItem value="gte">大于等于</UiSelectItem>
                  <UiSelectItem value="lte">小于等于</UiSelectItem>
                </UiSelectContent>
              </UiSelect>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label>阈值</Label>
              <Input v-model="ruleForm.threshold" type="number" placeholder="0" />
            </div>
            <div class="space-y-2">
              <Label>级别</Label>
              <UiSelect v-model="ruleForm.level">
                <UiSelectTrigger><UiSelectValue /></UiSelectTrigger>
                <UiSelectContent>
                  <UiSelectItem value="high">高</UiSelectItem>
                  <UiSelectItem value="medium">中</UiSelectItem>
                  <UiSelectItem value="low">低</UiSelectItem>
                </UiSelectContent>
              </UiSelect>
            </div>
          </div>
          <div class="flex justify-end gap-3 pt-2">
            <Button variant="outline" @click="dialogOpen = false">取消</Button>
            <Button @click="handleSaveRule">保存</Button>
          </div>
        </div>
      </UiDialogContent>
    </UiDialog>

    <UiAlertDialog :open="!!deleteTarget" @update:open="!$event && (deleteTarget = null)">
      <UiAlertDialogContent>
        <UiAlertDialogHeader>
          <UiAlertDialogTitle>确认删除</UiAlertDialogTitle>
          <UiAlertDialogDescription>确定删除该风控规则？此操作不可撤销。</UiAlertDialogDescription>
        </UiAlertDialogHeader>
        <UiAlertDialogFooter>
          <UiAlertDialogCancel>取消</UiAlertDialogCancel>
          <UiAlertDialogAction @click="handleDelete">删除</UiAlertDialogAction>
        </UiAlertDialogFooter>
      </UiAlertDialogContent>
    </UiAlertDialog>
  </BasicPage>
</template>
