<script setup lang="ts">
import { ref, reactive, computed, h } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { useStrategyList, useStartStrategy, useStopStrategy, useDeleteStrategy } from '@/composables/useStrategyQuery'
import { strategyLogApi, strategyVersionApi } from '@/api/strategy'
import { STATUS_LABELS, MARKET_LABELS } from '@/utils/constants'
import { formatDate } from '@/utils/format'
import { BasicPage } from '@/components/global-layout'
import { DataTable } from '@/components/data-table'
import type { ColumnDef } from '@tanstack/vue-table'
import Button from '@/components/ui/button/Button.vue'
import Badge from '@/components/ui/badge/Badge.vue'
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
import {
  ScrollArea as UiScrollArea,
} from '@/components/ui/scroll-area'
import { Plus } from 'lucide-vue-next'

const router = useRouter()
const currentPage = ref(1)
const pageSize = 20

const listParams = computed(() => ({ page: currentPage.value, size: pageSize }))
const strategyListQuery = useStrategyList(listParams)
const startMutation = useStartStrategy()
const stopMutation = useStopStrategy()
const deleteMutation = useDeleteStrategy()

const tableData = computed(() => strategyListQuery.data.value?.items || [])
const tableTotal = computed(() => strategyListQuery.data.value?.total || 0)
const loading = computed(() => strategyListQuery.isLoading.value)

const logDialogOpen = ref(false)
const logLoading = ref(false)
const logStrategyName = ref('')
const logEntries = ref<any[]>([])

const deleteTarget = ref<{ id: string; name: string } | null>(null)

const versionDialogOpen = ref(false)
const versionLoading = ref(false)
const versionStrategyName = ref('')
const versionStrategyId = ref('')
const versions = ref<any[]>([])

const loadingActions = reactive(new Set<string>())

const columns: ColumnDef<any>[] = [
  { accessorKey: 'name', header: '名称', cell: ({ row }) => h('span', { class: 'font-medium' }, row.getValue('name')) },
  {
    accessorKey: 'description',
    header: '描述',
    cell: ({ row }) => h('span', { class: 'text-muted-foreground text-sm' }, row.original.description || '—'),
  },
  {
    accessorKey: 'market',
    header: '市场',
    cell: ({ row }) => MARKET_LABELS[row.getValue('market') as string] || row.getValue('market'),
  },
  {
    accessorKey: 'status',
    header: '状态',
    cell: ({ row }) => {
      const status = row.getValue('status') as string
      const info = STATUS_LABELS[status]
      return h(Badge, { variant: status === 'running' ? 'default' : status === 'error' ? 'destructive' : 'secondary' }, () => info?.label || status)
    },
  },
  {
    accessorKey: 'updated_at',
    header: '更新时间',
    cell: ({ row }) => formatDate(row.getValue('updated_at')),
  },
  {
    id: 'actions',
    header: '操作',
    cell: ({ row }) => {
      const s = row.original
      return h('div', { class: 'flex gap-1' }, [
        h(Button, { size: 'sm', variant: 'ghost', onClick: () => router.push(`/strategy/${s.id}/edit`) }, () => '编辑'),
        s.status === 'running'
          ? h(Button, { size: 'sm', variant: 'ghost', onClick: () => showLogs(s.id, s.name) }, () => '日志')
          : null,
        h(Button, { size: 'sm', variant: 'ghost', onClick: () => showVersions(s.id, s.name) }, () => '版本'),
        s.status !== 'running'
          ? h(Button, { size: 'sm', variant: 'ghost', onClick: () => handleStart(s.id), loading: loadingActions.has(s.id + ':start') }, () => '启动')
          : null,
        s.status === 'running'
          ? h(Button, { size: 'sm', variant: 'ghost', onClick: () => handleStop(s.id), loading: loadingActions.has(s.id + ':stop') }, () => '停止')
          : null,
        s.status !== 'running'
          ? h(Button, { size: 'sm', variant: 'ghost', class: 'text-destructive', onClick: () => { deleteTarget.value = { id: s.id, name: s.name } } }, () => '删除')
          : null,
      ].filter(Boolean))
    },
  },
]

function handlePageChange(page: number) {
  currentPage.value = page
}

async function handleStart(id: string) {
  loadingActions.add(id + ':start')
  try { await startMutation.mutateAsync(id); toast.success('策略已启动') }
  catch (e: any) { toast.error(e.message || '启动失败') }
  finally { loadingActions.delete(id + ':start') }
}

async function handleStop(id: string) {
  loadingActions.add(id + ':stop')
  try { await stopMutation.mutateAsync(id); toast.success('策略已停止') }
  catch (e: any) { toast.error(e.message || '停止失败') }
  finally { loadingActions.delete(id + ':stop') }
}

async function handleDelete() {
  if (!deleteTarget.value) return
  const { id } = deleteTarget.value
  loadingActions.add(id + ':delete')
  try {
    await deleteMutation.mutateAsync(id)
    toast.success('策略已删除')
  } catch (e: any) { toast.error(e.message || '删除失败') }
  finally {
    loadingActions.delete(id + ':delete')
    deleteTarget.value = null
  }
}

async function showLogs(id: string, name: string) {
  logStrategyName.value = name
  logDialogOpen.value = true
  logLoading.value = true
  logEntries.value = []
  try {
    const res: any = await strategyLogApi.list(id, { limit: 200 })
    logEntries.value = res.data?.items || []
  } catch { toast.error('加载日志失败') }
  finally { logLoading.value = false }
}

async function showVersions(id: string, name: string) {
  versionStrategyId.value = id
  versionStrategyName.value = name
  versionDialogOpen.value = true
  versionLoading.value = true
  versions.value = []
  try {
    const res: any = await strategyVersionApi.list(id)
    versions.value = res.data || []
  } catch { toast.error('加载版本失败') }
  finally { versionLoading.value = false }
}

async function handleRollback(id: string, version: number) {
  versionLoading.value = true
  try {
    await strategyVersionApi.rollback(id, version)
    toast.success(`已回滚到版本 ${version}`)
    showVersions(id, versionStrategyName.value)
  } catch (e: any) { toast.error(e.message || '回滚失败') }
  finally { versionLoading.value = false }
}
</script>

<template>
  <BasicPage title="策略" description="管理你的量化交易策略">
    <template #actions>
      <Button @click="router.push('/strategy/create')">
        <Plus class="mr-2 size-4" />
        创建策略
      </Button>
    </template>

    <DataTable
      :columns="columns"
      :data="tableData"
      :total="tableTotal"
      :page-size="pageSize"
      :loading="loading"
      @page-change="handlePageChange"
    />

    <UiDialog v-model:open="logDialogOpen">
      <UiDialogContent class="max-w-2xl">
        <UiDialogHeader>
          <UiDialogTitle>{{ logStrategyName }} - 运行日志</UiDialogTitle>
          <UiDialogDescription>最近 200 条日志记录</UiDialogDescription>
        </UiDialogHeader>
        <div v-if="logLoading" class="flex items-center justify-center py-12">
          <div class="size-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
        <UiScrollArea v-else class="h-[400px]">
          <div v-if="!logEntries.length" class="py-8 text-center text-sm text-muted-foreground">暂无日志</div>
          <div v-else class="space-y-0 font-mono text-xs">
            <div
              v-for="(entry, idx) in logEntries"
              :key="idx"
              class="flex items-start gap-2 py-2 border-b last:border-0"
            >
              <span class="text-muted-foreground whitespace-nowrap shrink-0">{{ formatDate(entry.created_at) }}</span>
              <Badge
                :variant="entry.level === 'error' ? 'destructive' : entry.level === 'warning' ? 'outline' : 'secondary'"
                class="text-[10px] px-1.5 py-0 shrink-0"
              >
                {{ entry.level }}
              </Badge>
              <span class="break-all">{{ entry.message }}</span>
            </div>
          </div>
        </UiScrollArea>
      </UiDialogContent>
    </UiDialog>

    <UiDialog v-model:open="versionDialogOpen">
      <UiDialogContent class="max-w-2xl">
        <UiDialogHeader>
          <UiDialogTitle>{{ versionStrategyName }} - 版本历史</UiDialogTitle>
          <UiDialogDescription>最近 50 个版本记录，可以将策略回滚到任一版本</UiDialogDescription>
        </UiDialogHeader>
        <div v-if="versionLoading" class="flex items-center justify-center py-12">
          <div class="size-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
        <UiScrollArea v-else class="h-[400px]">
          <div v-if="!versions.length" class="py-8 text-center text-sm text-muted-foreground">暂无版本记录</div>
          <div v-else class="space-y-2">
            <div
              v-for="(v, idx) in versions"
              :key="idx"
              class="flex items-center justify-between p-3 border rounded-md"
            >
              <div class="space-y-1 flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <Badge variant="secondary">v{{ v.version }}</Badge>
                  <span v-if="v.change_note" class="text-xs text-muted-foreground ml-2 truncate">{{ v.change_note }}</span>
                </div>
                <p class="text-xs text-muted-foreground">{{ formatDate(v.created_at) }}</p>
              </div>
              <Button
                size="sm"
                variant="outline"
                :loading="versionLoading"
                @click="handleRollback(versionStrategyId, v.version)"
              >
                回滚
              </Button>
            </div>
          </div>
        </UiScrollArea>
      </UiDialogContent>
    </UiDialog>

    <UiAlertDialog :open="!!deleteTarget" @update:open="!$event && (deleteTarget = null)">
      <UiAlertDialogContent>
        <UiAlertDialogHeader>
          <UiAlertDialogTitle>确认删除</UiAlertDialogTitle>
          <UiAlertDialogDescription>
            确定删除策略「{{ deleteTarget?.name }}」？此操作不可撤销。
          </UiAlertDialogDescription>
        </UiAlertDialogHeader>
        <UiAlertDialogFooter>
          <UiAlertDialogCancel>取消</UiAlertDialogCancel>
          <UiAlertDialogAction @click="handleDelete">删除</UiAlertDialogAction>
        </UiAlertDialogFooter>
      </UiAlertDialogContent>
    </UiAlertDialog>
  </BasicPage>
</template>
