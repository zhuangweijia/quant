<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useStrategyStore } from "@/stores/strategy";
import { ElMessage, ElMessageBox } from "element-plus";
import { STATUS_LABELS, MARKET_LABELS } from "@/utils/constants";

const router = useRouter();
const store = useStrategyStore();
const loading = ref(false);

onMounted(async () => {
  loading.value = true;
  try {
    await store.fetchStrategies();
  } finally {
    loading.value = false;
  }
});

async function handleStart(id: string) {
  try {
    await store.startStrategy(id);
    ElMessage.success("策略已启动");
  } catch (e: any) {
    ElMessage.error(e.message || "启动失败");
  }
}

async function handleStop(id: string) {
  try {
    await store.stopStrategy(id);
    ElMessage.success("策略已停止");
  } catch (e: any) {
    ElMessage.error(e.message || "停止失败");
  }
}

async function handleDelete(id: string, name: string) {
  try {
    await ElMessageBox.confirm(`确定删除策略「${name}」？`, "确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
    await store.deleteStrategy(id);
    ElMessage.success("策略已删除");
  } catch {
    // cancelled
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
            {{ new Date(row.updated_at).toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="router.push(`/strategy/${row.id}/edit`)">
              编辑
            </el-button>
            <el-button
              v-if="row.status !== 'running'"
              size="small"
              type="success"
              @click="handleStart(row.id)"
            >
              启动
            </el-button>
            <el-button
              v-if="row.status === 'running'"
              size="small"
              type="warning"
              @click="handleStop(row.id)"
            >
              停止
            </el-button>
            <el-button
              v-if="row.status !== 'running'"
              size="small"
              type="danger"
              @click="handleDelete(row.id, row.name)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
