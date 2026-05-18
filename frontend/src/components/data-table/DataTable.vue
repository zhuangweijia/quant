<script setup lang="ts" generic="TData, TValue">
import type { ColumnDef, SortingState, VisibilityState, PaginationState } from '@tanstack/vue-table'
import { valueUpdater } from '@/lib/utils'
import {
  FlexRender,
  getCoreRowModel,
  useVueTable,
} from '@tanstack/vue-table'

const props = withDefaults(defineProps<{
  columns: ColumnDef<TData, TValue>[]
  data: TData[]
  total?: number
  loading?: boolean
  pageSize?: number
}>(), {
  total: 0,
  loading: false,
  pageSize: 20,
})

const emit = defineEmits<{
  (e: 'page-change', page: number): void
}>()

const sorting = ref<SortingState>([])
const columnVisibility = ref<VisibilityState>({})
const pagination = ref<PaginationState>({ pageIndex: 0, pageSize: props.pageSize })

const table = useVueTable({
  get columns() { return props.columns },
  get data() { return props.data },
  get pageCount() { return Math.ceil(props.total / props.pageSize) },
  state: {
    get sorting() { return sorting.value },
    get columnVisibility() { return columnVisibility.value },
    get pagination() { return pagination.value },
  },
  manualPagination: true,
  manualSorting: true,
  onPaginationChange: (updater) => {
    valueUpdater(updater, pagination)
    emit('page-change', pagination.value.pageIndex + 1)
  },
  getCoreRowModel: getCoreRowModel(),
})
</script>

<template>
  <div class="space-y-4">
    <div class="rounded-md border">
      <UiTable>
        <UiTableHeader>
          <UiTableRow v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
            <UiTableHead v-for="header in headerGroup.headers" :key="header.id">
              <FlexRender
                v-if="!header.isPlaceholder"
                :render="header.column.columnDef.header"
                :props="header.getContext()"
              />
            </UiTableHead>
          </UiTableRow>
        </UiTableHeader>
        <UiTableBody>
          <template v-if="loading">
            <UiTableRow v-for="i in 5" :key="`skeleton-${i}`">
              <UiTableCell v-for="header in table.getHeaderGroups()[0]?.headers" :key="header.id">
                <UiSkeleton class="h-5 w-full" />
              </UiTableCell>
            </UiTableRow>
          </template>
          <template v-else-if="table.getRowModel().rows?.length">
            <UiTableRow
              v-for="row in table.getRowModel().rows"
              :key="row.id"
              :data-state="row.getIsSelected() ? 'selected' : undefined"
            >
              <UiTableCell v-for="cell in row.getVisibleCells()" :key="cell.id">
                <FlexRender :render="cell.column.columnDef.cell" :props="cell.getContext()" />
              </UiTableCell>
            </UiTableRow>
          </template>
          <template v-else>
            <UiTableRow>
              <UiTableCell :colspan="columns.length" class="h-32">
                <div class="flex flex-col items-center justify-center gap-2 text-muted-foreground">
                  <svg xmlns="http://www.w3.org/2000/svg" class="size-10 opacity-40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3h18v18H3z"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
                  <p class="text-sm">暂无数据</p>
                </div>
              </UiTableCell>
            </UiTableRow>
          </template>
        </UiTableBody>
      </UiTable>
    </div>

    <div v-if="total > pageSize" class="flex items-center justify-between px-2">
      <div class="text-sm text-muted-foreground">
        共 {{ total }} 条
      </div>
      <div class="flex items-center gap-2">
        <UiButton
          variant="outline"
          size="sm"
          :disabled="pagination.pageIndex === 0"
          @click="table.previousPage()"
        >
          上一页
        </UiButton>
        <span class="text-sm text-muted-foreground">
          {{ pagination.pageIndex + 1 }} / {{ Math.ceil(total / pageSize) }}
        </span>
        <UiButton
          variant="outline"
          size="sm"
          :disabled="pagination.pageIndex >= Math.ceil(total / pageSize) - 1"
          @click="table.nextPage()"
        >
          下一页
        </UiButton>
      </div>
    </div>
  </div>
</template>
