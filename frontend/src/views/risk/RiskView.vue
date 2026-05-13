<script setup lang="ts">
import { ref, computed, onMounted, reactive } from "vue";
import { useRiskStore } from "@/stores/risk";
import { strategyApi } from "@/api/strategy";
import { ElMessage, ElMessageBox } from "element-plus";
import type { StrategyListItem } from "@/types/strategy";
import type { RiskRuleCreateRequest } from "@/types/risk";

const store = useRiskStore();
const loading = ref(false);
const dialogVisible = ref(false);
const editDialogVisible = ref(false);
const editingRule = ref<any>(null);
const strategies = ref<StrategyListItem[]>([]);
const alertFilter = ref("");
const alertLoading = ref(false);

const ruleForm = reactive<RiskRuleCreateRequest>({
  name: "",
  rule_type: "max_drawdown",
  scope: "global",
  strategy_id: undefined,
  params: {},
});
const ruleParamsJson = ref("{}");

const editForm = reactive({
  name: "",
  params: {} as Record<string, any>,
});
const editParamsJson = ref("{}");

const ruleTypes = [
  { label: "最大回撤", value: "max_drawdown" },
  { label: "最大持仓", value: "max_position" },
  { label: "日亏损限制", value: "daily_loss" },
  { label: "单笔止损", value: "stop_loss" },
  { label: "价格波动", value: "price_alert" },
];

const levelOptions = [
  { label: "低", value: "low" },
  { label: "中", value: "medium" },
  { label: "高", value: "high" },
];

const globalRules = computed(() => store.rules.filter((r) => r.scope === "global"));
const strategyRules = computed(() => store.rules.filter((r) => r.scope === "strategy"));
const filteredAlerts = computed(() => {
  if (!alertFilter.value) return store.alerts;
  return store.alerts.filter((a) => a.level === alertFilter.value);
});

onMounted(async () => {
  loading.value = true;
  try {
    await Promise.all([store.fetchRules(), store.fetchAlerts({ page: 1, page_size: 50 })]);
    const res: any = await strategyApi.list();
    strategies.value = res.data.items || [];
  } finally {
    loading.value = false;
  }
});

async function handleToggle(rule: any) {
  try {
    await store.toggleRule(rule.id);
    ElMessage.success(rule.is_enabled ? "已禁用" : "已启用");
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  }
}

async function handleDelete(id: string) {
  try {
    await ElMessageBox.confirm("确定删除该规则？", "确认", { type: "warning" });
    await store.deleteRule(id);
    ElMessage.success("已删除");
  } catch {
    // cancelled
  }
}

function openCreateDialog() {
  ruleForm.name = "";
  ruleForm.rule_type = "max_drawdown";
  ruleForm.scope = "global";
  ruleForm.strategy_id = undefined;
  ruleForm.params = {};
  ruleParamsJson.value = "{}";
  dialogVisible.value = true;
}

async function handleCreate() {
  if (!ruleForm.name) {
    ElMessage.warning("请输入规则名称");
    return;
  }
  try {
    ruleForm.params = JSON.parse(ruleParamsJson.value || "{}");
    await store.createRule({ ...ruleForm });
    ElMessage.success("规则已创建");
    dialogVisible.value = false;
  } catch (e: any) {
    ElMessage.error(e.message || "创建失败");
  }
}

function openEditDialog(rule: any) {
  editingRule.value = rule;
  editForm.name = rule.name;
  editForm.params = { ...rule.params };
  editParamsJson.value = JSON.stringify(rule.params, null, 2);
  editDialogVisible.value = true;
}

async function handleUpdate() {
  if (!editingRule.value) return;
  try {
    editForm.params = JSON.parse(editParamsJson.value || "{}");
    await store.updateRule(editingRule.value.id, {
      name: editForm.name,
      params: editForm.params,
    });
    ElMessage.success("规则已更新");
    editDialogVisible.value = false;
  } catch (e: any) {
    ElMessage.error(e.message || "更新失败");
  }
}

async function handleMarkRead(id: string) {
  try {
    await store.markAlertRead(id);
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  }
}

async function handleMarkAllRead() {
  try {
    await store.markAllAlertsRead();
    ElMessage.success("已全部标记已读");
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  }
}

function getRuleTypeLabel(type: string) {
  return ruleTypes.find((t) => t.value === type)?.label || type;
}

function formatParams(params: Record<string, any>) {
  return Object.entries(params)
    .map(([k, v]) => `${k}: ${v}`)
    .join(", ");
}
</script>

<template>
  <div class="risk-view" v-loading="loading">
    <el-card shadow="hover" style="margin-bottom: 20px">
      <template #header>
        <div class="card-header">
          <span>风控规则</span>
          <el-button type="primary" size="small" @click="openCreateDialog">添加规则</el-button>
        </div>
      </template>

      <div v-if="globalRules.length">
        <h4 class="rule-group-title">全局规则</h4>
        <el-row :gutter="16">
          <el-col :span="8" v-for="rule in globalRules" :key="rule.id">
            <el-card shadow="hover" class="rule-card">
              <div class="rule-header">
                <span class="rule-name">{{ rule.name }}</span>
                <el-switch
                  :model-value="rule.is_enabled"
                  size="small"
                  @change="handleToggle(rule)"
                />
              </div>
              <div class="rule-type">
                <el-tag size="small">{{ getRuleTypeLabel(rule.rule_type) }}</el-tag>
              </div>
              <div class="rule-params" v-if="Object.keys(rule.params).length">
                {{ formatParams(rule.params) }}
              </div>
              <div class="rule-actions">
                <el-button text size="small" @click="openEditDialog(rule)">编辑</el-button>
                <el-button text size="small" type="danger" @click="handleDelete(rule.id)">删除</el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <div v-if="strategyRules.length" style="margin-top: 16px">
        <h4 class="rule-group-title">策略规则</h4>
        <el-row :gutter="16">
          <el-col :span="8" v-for="rule in strategyRules" :key="rule.id">
            <el-card shadow="hover" class="rule-card">
              <div class="rule-header">
                <span class="rule-name">{{ rule.name }}</span>
                <el-switch
                  :model-value="rule.is_enabled"
                  size="small"
                  @change="handleToggle(rule)"
                />
              </div>
              <div class="rule-type">
                <el-tag size="small">{{ getRuleTypeLabel(rule.rule_type) }}</el-tag>
                <el-tag size="small" type="info" style="margin-left: 4px">
                  {{ strategies.find((s) => s.id === rule.strategy_id)?.name || rule.strategy_id || "-" }}
                </el-tag>
              </div>
              <div class="rule-params" v-if="Object.keys(rule.params).length">
                {{ formatParams(rule.params) }}
              </div>
              <div class="rule-actions">
                <el-button text size="small" @click="openEditDialog(rule)">编辑</el-button>
                <el-button text size="small" type="danger" @click="handleDelete(rule.id)">删除</el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <el-empty v-if="!store.rules.length" description="暂无风控规则" />
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>风控告警</span>
          <div>
            <el-select v-model="alertFilter" placeholder="筛选等级" clearable size="small" style="width: 120px; margin-right: 8px">
              <el-option v-for="l in levelOptions" :key="l.value" :label="l.label" :value="l.value" />
            </el-select>
            <el-button size="small" @click="handleMarkAllRead" :disabled="!store.alerts.length">
              全部已读
            </el-button>
          </div>
        </div>
      </template>

      <el-table :data="filteredAlerts" stripe size="small">
        <el-table-column prop="rule_name" label="规则" width="140" />
        <el-table-column prop="message" label="告警信息" min-width="200" />
        <el-table-column label="等级" width="80">
          <template #default="{ row }">
            <el-tag
              :type="row.level === 'high' ? 'danger' : row.level === 'medium' ? 'warning' : 'info'"
              size="small"
            >
              {{ row.level === "high" ? "高" : row.level === "medium" ? "中" : "低" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_read ? 'info' : 'warning'" size="small">
              {{ row.is_read ? "已读" : "未读" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ new Date(row.created_at).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="操作" width="70" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.is_read" text size="small" type="primary" @click="handleMarkRead(row.id)">
              已读
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!store.alerts.length" description="暂无告警" :image-size="60" />
    </el-card>

    <el-dialog v-model="dialogVisible" title="添加风控规则" width="500px" destroy-on-close>
      <el-form :model="ruleForm" label-width="90px">
        <el-form-item label="规则名称">
          <el-input v-model="ruleForm.name" placeholder="输入规则名称" />
        </el-form-item>
        <el-form-item label="规则类型">
          <el-select v-model="ruleForm.rule_type" style="width: 100%">
            <el-option v-for="t in ruleTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="作用范围">
          <el-radio-group v-model="ruleForm.scope">
            <el-radio value="global">全局</el-radio>
            <el-radio value="strategy">策略</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="ruleForm.scope === 'strategy'" label="策略">
          <el-select v-model="ruleForm.strategy_id" placeholder="选择策略" style="width: 100%">
            <el-option v-for="s in strategies" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数 (JSON)">
          <el-input
            v-model="ruleParamsJson"
            type="textarea"
            :rows="3"
            placeholder='{"threshold": 0.1}'
            style="font-family: 'Courier New', monospace"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑风控规则" width="500px" destroy-on-close>
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="规则名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="参数 (JSON)">
          <el-input
            v-model="editParamsJson"
            type="textarea"
            :rows="3"
            style="font-family: 'Courier New', monospace"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUpdate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rule-group-title {
  font-size: 14px;
  color: var(--qp-text-secondary);
  margin: 0 0 12px;
  padding-left: 4px;
  border-left: 3px solid var(--qp-primary);
}

.rule-card {
  margin-bottom: 12px;

  :deep(.el-card__body) {
    padding: 12px;
  }

  .rule-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .rule-name {
    font-weight: 600;
    font-size: 14px;
  }

  .rule-type {
    margin-bottom: 6px;
  }

  .rule-params {
    font-size: 12px;
    color: var(--qp-text-secondary);
    margin-bottom: 8px;
    word-break: break-all;
  }

  .rule-actions {
    display: flex;
    gap: 4px;
  }
}
</style>
