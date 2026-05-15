<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRiskStore } from "@/stores/risk";
import { useStrategyStore } from "@/stores/strategy";
import { ElMessage, ElMessageBox } from "element-plus";
import { formatDate } from "@/utils/format";

const riskStore = useRiskStore();
const strategyStore = useStrategyStore();

const ruleDialog = ref(false);
const editingRule = ref<any>(null);
const ruleForm = ref({
  name: "",
  rule_type: "max_position_value",
  strategy_id: null as string | null,
  params: {} as Record<string, any>,
});

const alertFilter = ref("");
const alertPage = ref(1);
const ruleSaving = ref(false);
const ruleDeleting = ref<string | null>(null);

const RULE_TYPES: Record<string, { label: string; params: Record<string, { label: string; type: string; default: any }> }> = {
  max_position_value: { label: "单标的持仓限额", params: { max_value: { label: "最大金额", type: "number", default: 100000 } } },
  max_position_ratio: { label: "总仓位比例", params: { max_ratio: { label: "最大比例", type: "number", default: 0.8 } } },
  daily_loss_limit: { label: "日亏损限制", params: { max_daily_loss: { label: "最大日亏损", type: "number", default: 10000 } } },
  daily_trade_limit: { label: "日交易次数限制", params: { max_trades: { label: "最大次数", type: "number", default: 20 } } },
  blacklist: { label: "交易黑名单", params: { symbols: { label: "标的列表", type: "array", default: [] } } },
  max_order_amount: { label: "单笔金额限制", params: { max_amount: { label: "最大金额", type: "number", default: 50000 } } },
  stop_loss: { label: "止损规则", params: { stop_type: { label: "类型", type: "select", default: "fixed" }, value: { label: "止损值", type: "number", default: 0 } } },
  take_profit: { label: "止盈规则", params: { take_type: { label: "类型", type: "select", default: "fixed" }, value: { label: "止盈值", type: "number", default: 0 } } },
};

function initRuleForm(ruleType: string) {
  const config = RULE_TYPES[ruleType];
  if (config) {
    ruleForm.value.params = {};
    for (const [key, p] of Object.entries(config.params)) {
      ruleForm.value.params[key] = p.default;
    }
  }
}

function openCreateRule() {
  editingRule.value = null;
  ruleForm.value = { name: "", rule_type: "max_position_value", strategy_id: null, params: {} };
  initRuleForm("max_position_value");
  ruleDialog.value = true;
}

function openEditRule(rule: any) {
  editingRule.value = rule;
  ruleForm.value = {
    name: rule.name || "",
    rule_type: rule.rule_type,
    strategy_id: rule.strategy_id,
    params: { ...rule.params },
  };
  ruleDialog.value = true;
}

async function saveRule() {
  ruleSaving.value = true;
  try {
    if (editingRule.value) {
      await riskStore.updateRule(editingRule.value.id, { name: ruleForm.value.name, params: ruleForm.value.params });
    } else {
      await riskStore.createRule({
        name: ruleForm.value.name || RULE_TYPES[ruleForm.value.rule_type]?.label || ruleForm.value.rule_type,
        rule_type: ruleForm.value.rule_type,
        scope: ruleForm.value.strategy_id ? "strategy" : "global",
        strategy_id: ruleForm.value.strategy_id || undefined,
        params: ruleForm.value.params,
      });
    }
    ruleDialog.value = false;
    ElMessage.success("保存成功");
  } catch (e: any) {
    ElMessage.error(e.message);
  } finally {
    ruleSaving.value = false;
  }
}

async function deleteRule(id: string) {
  await ElMessageBox.confirm("确认删除该规则?", "提示", { type: "warning" });
  ruleDeleting.value = id;
  try {
    await riskStore.deleteRule(id);
    ElMessage.success("已删除");
  } finally {
    ruleDeleting.value = null;
  }
}

async function loadAlerts() {
  await riskStore.fetchAlerts({
    page: alertPage.value,
    page_size: 20,
    level: alertFilter.value || undefined,
  });
}

onMounted(() => {
  riskStore.fetchRules();
  loadAlerts();
  strategyStore.fetchStrategies();
});
</script>

<template>
  <div class="risk-page">
    <el-row :gutter="16">
      <el-col :xs="24" :md="16">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>风控规则</span>
              <el-button type="primary" size="small" @click="openCreateRule">新增规则</el-button>
            </div>
          </template>

          <h4 style="margin-bottom: 12px; color: var(--qp-text-secondary)">全局规则</h4>
          <div class="rule-grid">
            <el-card v-for="rule in riskStore.rules.filter((r: any) => !r.strategy_id)" :key="rule.id" shadow="hover" class="rule-card">
              <div class="rule-header">
                <el-tag size="small">{{ RULE_TYPES[rule.rule_type]?.label || rule.rule_type }}</el-tag>
                <el-switch v-model="rule.is_enabled" size="small" @change="riskStore.toggleRule(rule.id)" />
              </div>
              <div class="rule-params">
                <span v-for="(val, key) in rule.params" :key="key" class="param-item">
                  {{ key }}: {{ Array.isArray(val) ? val.join(", ") : val }}
                </span>
              </div>
              <div class="rule-actions">
                <el-button link type="primary" size="small" @click="openEditRule(rule)">编辑</el-button>
                <el-button link type="danger" size="small" :loading="ruleDeleting === rule.id" @click="deleteRule(rule.id)">删除</el-button>
              </div>
            </el-card>
            <el-empty v-if="!riskStore.rules.filter((r: any) => !r.strategy_id).length" description="暂无全局规则" :image-size="40" />
          </div>

          <el-divider />

          <h4 style="margin-bottom: 12px; color: var(--qp-text-secondary)">策略规则</h4>
          <div class="rule-grid">
            <el-card v-for="rule in riskStore.rules.filter((r: any) => r.strategy_id)" :key="rule.id" shadow="hover" class="rule-card">
              <div class="rule-header">
                <el-tag size="small">{{ RULE_TYPES[rule.rule_type]?.label || rule.rule_type }}</el-tag>
                <el-switch v-model="rule.is_enabled" size="small" @change="riskStore.toggleRule(rule.id)" />
              </div>
              <div class="rule-params">
                <span v-for="(val, key) in rule.params" :key="key" class="param-item">
                  {{ key }}: {{ Array.isArray(val) ? val.join(", ") : val }}
                </span>
              </div>
              <div class="rule-actions">
                <el-button link type="primary" size="small" @click="openEditRule(rule)">编辑</el-button>
                <el-button link type="danger" size="small" :loading="ruleDeleting === rule.id" @click="deleteRule(rule.id)">删除</el-button>
              </div>
            </el-card>
            <el-empty v-if="!riskStore.rules.filter((r: any) => r.strategy_id).length" description="暂无策略规则" :image-size="40" />
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="8">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>告警</span>
              <div>
                <el-select v-model="alertFilter" placeholder="筛选级别" size="small" clearable style="width: 100px; margin-right: 8px" @change="loadAlerts">
                  <el-option label="低" value="low" />
                  <el-option label="中" value="medium" />
                  <el-option label="高" value="high" />
                </el-select>
                <el-button size="small" @click="riskStore.markAllAlertsRead(); loadAlerts()">全部已读</el-button>
              </div>
            </div>
          </template>
          <div class="alert-list">
            <div v-for="alert in riskStore.alerts" :key="alert.id" class="alert-item" :class="{ unread: !alert.is_read }">
              <div class="alert-header">
                <el-tag size="small" :type="({ low: 'info', medium: 'warning', high: 'danger' }[alert.level as string] ?? 'info') as any">
                  {{ alert.level }}
                </el-tag>
                <span class="alert-time">{{ formatDate(alert.created_at) }}</span>
              </div>
              <div class="alert-title">{{ alert.rule_name || '告警' }}</div>
              <div class="alert-message">{{ alert.message }}</div>
              <el-button v-if="!alert.is_read" link type="primary" size="small" @click="riskStore.markAlertRead(alert.id)">标记已读</el-button>
            </div>
            <el-empty v-if="!riskStore.alerts.length" description="暂无告警" :image-size="60" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="ruleDialog" :title="editingRule ? '编辑规则' : '新增规则'" width="500px" destroy-on-close>
      <el-form :model="ruleForm" label-width="80px">
        <el-form-item label="规则名称">
          <el-input v-model="ruleForm.name" :placeholder="RULE_TYPES[ruleForm.rule_type]?.label || '规则名称'" />
        </el-form-item>
        <el-form-item v-if="!editingRule" label="规则类型">
          <el-select v-model="ruleForm.rule_type" style="width: 100%" @change="initRuleForm(ruleForm.rule_type)">
            <el-option v-for="(config, key) in RULE_TYPES" :key="key" :label="config.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!editingRule" label="策略">
          <el-select v-model="ruleForm.strategy_id" clearable placeholder="全局规则" style="width: 100%">
            <el-option v-for="s in strategyStore.strategies" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-for="(config, key) in RULE_TYPES[ruleForm.rule_type]?.params" :key="key" :label="config.label">
          <el-input-number v-if="config.type === 'number'" v-model="ruleForm.params[key]" style="width: 100%" />
          <el-select v-else-if="config.type === 'select'" v-model="ruleForm.params[key]" style="width: 100%">
            <el-option label="固定值" value="fixed" />
            <el-option label="百分比" value="percent" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialog = false">取消</el-button>
        <el-button type="primary" :loading="ruleSaving" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.risk-page {
  max-width: 1400px;
}

.rule-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.rule-card {
  .rule-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .rule-params {
    font-size: 12px;
    color: var(--qp-text-secondary);
    margin-bottom: 8px;

    .param-item {
      display: inline-block;
      margin-right: 12px;
    }
  }

  .rule-actions {
    border-top: 1px solid #f0f0f0;
    padding-top: 8px;
  }
}

.alert-list {
  max-height: 600px;
  overflow-y: auto;
}

.alert-item {
  padding: 10px 0;
  border-bottom: 1px solid #f5f5f5;

  &.unread {
    background: #f0f7ff;
    margin: 0 -12px;
    padding: 10px 12px;
    border-radius: 4px;
  }

  .alert-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .alert-time {
    font-size: 11px;
    color: var(--qp-text-secondary);
  }

  .alert-title {
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 2px;
  }

  .alert-message {
    font-size: 12px;
    color: var(--qp-text-secondary);
    margin-bottom: 4px;
  }
}
</style>
