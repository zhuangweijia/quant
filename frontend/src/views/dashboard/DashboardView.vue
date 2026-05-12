<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "@/stores/auth";
import { formatCurrency, formatPercent } from "@/utils/format";

const authStore = useAuthStore();
</script>

<template>
  <div class="dashboard-view">
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6" v-for="stat in [
        { label: '总资产', value: '-', sub: '' },
        { label: '日盈亏', value: '-', sub: '' },
        { label: '总盈亏', value: '-', sub: '' },
        { label: '运行策略', value: '0', sub: '/ 10' },
      ]" :key="stat.label">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-label">{{ stat.label }}</div>
          <div class="stat-value">{{ stat.value }}<small>{{ stat.sub }}</small></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header><span>权益曲线</span></template>
          <div class="chart-placeholder">
            <el-empty description="暂无数据" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span>持仓分布</span></template>
          <div class="chart-placeholder">
            <el-empty description="暂无持仓" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>策略表现</span></template>
          <el-empty description="暂无策略数据" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>最近交易</span></template>
          <el-empty description="暂无交易记录" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped lang="scss">
.dashboard-view {
  .stat-row {
    margin-bottom: 20px;
  }

  .stat-card {
    text-align: center;
  }

  .stat-label {
    font-size: 14px;
    color: var(--qp-text-secondary);
    margin-bottom: 8px;
  }

  .stat-value {
    font-size: 24px;
    font-weight: 600;
    color: var(--qp-text-primary);

    small {
      font-size: 14px;
      font-weight: 400;
      color: var(--qp-text-secondary);
    }
  }

  .chart-placeholder {
    height: 300px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
</style>
