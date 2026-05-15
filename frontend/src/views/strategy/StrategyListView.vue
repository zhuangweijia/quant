<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useStrategyStore } from "@/stores/strategy";
import { strategyLogApi } from "@/api/strategy";
import { ElMessage, ElMessageBox } from "element-plus";
import { STATUS_LABELS, MARKET_LABELS } from "@/utils/constants";
import { formatDate } from "@/utils/format";

const router = useRouter();
const store = useStrategyStore();
const loading = ref(false);
const loadingActions = reactive(new Set<string>());

const logDialogVisible = ref(false);
const logLoading = ref(false);
const logStrategyName = ref("");
const logEntries = ref<any[]>([]);

const currentPage = ref(1);
const pageSize = ref(20);

onMounted(async () => {
  loading.value = true;
  try {
    await store.fetchStrategies({ page: currentPage.value, size: pageSize.value });
  } finally {
    loading.value = false;
  }
});

async function handlePageChange(page: number) {
  currentPage.value = page;
  loading.value = true;
  try {
    await store.fetchStrategies({ page: currentPage.value, size: pageSize.value });
  } finally {
    loading.value = false;
  }
}

async function handleStart(id: string) {
  loadingActions.add(id + ":start");
  try {
    await store.startStrategy(id);
    ElMessage.success("策略已启动");
  } catch (e: any) {
    ElMessage.error(e.message || "启动失败");
  } finally {
    loadingActions.delete(id + ":start");
  }
}

async function handleStop(id: string) {
  loadingActions.add(id + ":stop");
  try {
    await store.stopStrategy(id);
    ElMessage.success("策略已停止");
  } catch (e: any) {
    ElMessage.error(e.message || "停止失败");
  } finally {
    loadingActions.delete(id + ":stop");
  }
}

async function handleDelete(id: string, name: string) {
  try {
    await ElMessageBox.confirm(`确定删除策略「${name}」？`, "确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
    loadingActions.add(id + ":delete");
    try {
      await store.deleteStrategy(id);
      ElMessage.success("策略已删除");
    } finally {
      loadingActions.delete(id + ":delete");
    }
  } catch {
    // cancelled
  }
}

async function showLogs(id: string, name: string) {
  logStrategyName.value = name;
  logDialogVisible.value = true;
  logLoading.value = true;
  logEntries.value = [];
  try {
    const res: any = await strategyLogApi.list(id, { limit: 200 });
    logEntries.value = res.data?.items || [];
  } catch {
    ElMessage.error("加载日志失败");
  } finally {
    logLoading.value = false;
  }
}
</script>

<template>
  <div>
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>策略列表</span>
          <el-button type="primary" @click="router.push('/strategy/create')">
            创建策略
          </el-button>
        </div>
      </template>

      <el-table :data="store.strategies" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="{ row }">
            <span class="text-secondary">{{ row.description || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="market" label="市场" width="120">
          <template #default="{ row }">
            {{ MARKET_LABELS[row.market] || row.market }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag
              :type="(STATUS_LABELS[row.status]?.type as any) || 'info'"
              size="small"
            >
              {{ STATUS_LABELS[row.status]?.label || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="router.push(`/strategy/${row.id}/edit`)">
              编辑
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              size="small"
              type="info"
              @click="showLogs(row.id, row.name)"
            >
              日志
            </el-button>
            <el-button
              v-if="row.status !== 'running'"
              size="small"
              type="success"
              :loading="loadingActions.has(row.id + ':start')"
              @click="handleStart(row.id)"
            >
              启动
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              size="small"
              type="warning"
              :loading="loadingActions.has(row.id + ':stop')"
              @click="handleStop(row.id)"
            >
              停止
            </el-button>
            <el-button
              v-if="row.status !== 'running'"
              size="small"
              type="danger"
              :loading="loadingActions.has(row.id + ':delete')"
              @click="handleDelete(row.id, row.name)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; display: flex; justify-content: flex-end">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="store.total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <el-dialog v-model="logDialogVisible" :title="`${logStrategyName} - 运行日志`" width="720px" top="6vh">
      <div v-loading="logLoading" class="log-container">
        <el-empty v-if="!logLoading && !logEntries.length" description="暂无日志" />
        <div v-else class="log-entries">
          <div v-for="(entry, idx) in logEntries" :key="idx" class="log-entry">
            <span class="log-time">{{ formatDate(entry.created_at) }}</span>
            <el-tag :type="entry.level === 'error' ? 'danger' : entry.level === 'warning' ? 'warning' : 'info'" size="small">
              {{ entry.level }}
            </el-tag>
            <span class="log-msg">{{ entry.message }}</span>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.text-secondary {
  color: var(--qp-text-secondary);
  font-size: 13px;
}

.log-container {
  max-height: 480px;
  overflow-y: auto;
}

.log-entries {
  font-family: 'Courier New', Courier, monospace;
  font-size: 12px;
}

.log-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--qp-border-color, #eee);

  &:last-child {
    border-bottom: none;
  }
}

.log-time {
  color: var(--qp-text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
}

.log-msg {
  word-break: break-all;
}
</style>
