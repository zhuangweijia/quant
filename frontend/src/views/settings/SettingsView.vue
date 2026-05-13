<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { settingsApi } from "@/api/settings";
import { useAuthStore } from "@/stores/auth";
import { ElMessage } from "element-plus";
import type { BrokerConfig, ProfileInfo } from "@/types/settings";

const authStore = useAuthStore();
const activeTab = ref("broker");

const brokerLoading = ref(false);
const notifyLoading = ref(false);
const paramLoading = ref(false);
const profileLoading = ref(false);
const saving = ref(false);

const brokers = ref<BrokerConfig[]>([]);
const tradingMode = ref("paper");

const notifyForm = reactive({
  email_enabled: false,
  email_smtp_host: "",
  email_smtp_port: 465,
  email_sender: "",
  email_password: "",
  email_use_ssl: true,
  email_recipient: "",
  webhook_enabled: false,
  webhook_url: "",
  webhook_secret: "",
  notify_levels: ["warning", "error"] as string[],
});

const systemParams = ref<Record<string, string>>({});
const profile = ref<ProfileInfo | null>(null);

const passwordForm = reactive({
  old_password: "",
  new_password: "",
  confirm_password: "",
});

const PARAM_GROUPS = [
  {
    label: "策略限制",
    keys: ["max_strategies_per_user", "max_running_strategies", "max_concurrent_backtests"],
  },
  {
    label: "超时设置",
    keys: ["backtest_timeout", "order_timeout"],
  },
  {
    label: "资金与佣金",
    keys: ["paper_initial_capital", "default_commission_a_stock", "default_commission_us_stock", "default_commission_crypto"],
  },
  {
    label: "数据保留",
    keys: ["data_retention_days", "alert_retention_days"],
  },
];

const PARAM_LABELS: Record<string, string> = {
  max_strategies_per_user: "每用户最大策略数",
  max_running_strategies: "最大运行策略数",
  max_concurrent_backtests: "最大并发回测数",
  backtest_timeout: "回测超时(秒)",
  order_timeout: "下单超时(秒)",
  paper_initial_capital: "模拟盘初始资金",
  default_commission_a_stock: "A股默认佣金",
  default_commission_us_stock: "美股默认佣金",
  default_commission_crypto: "加密货币默认佣金",
  data_retention_days: "数据保留天数",
  alert_retention_days: "告警保留天数",
};

onMounted(async () => {
  profileLoading.value = true;
  try {
    const res: any = await settingsApi.getProfile();
    profile.value = res.data;
  } catch {
    // ignore
  } finally {
    profileLoading.value = false;
  }
});

async function loadBrokerTab() {
  brokerLoading.value = true;
  try {
    const [brokerRes, modeRes] = await Promise.allSettled([
      settingsApi.getBrokers(),
      settingsApi.getTradingMode(),
    ]);
    if (brokerRes.status === "fulfilled") brokers.value = (brokerRes.value as any).data || [];
    if (modeRes.status === "fulfilled") tradingMode.value = (modeRes.value as any).data?.mode || "paper";
  } finally {
    brokerLoading.value = false;
  }
}

async function loadNotifyTab() {
  notifyLoading.value = true;
  try {
    const res: any = await settingsApi.getNotifications();
    const data = res.data;
    if (data) {
      Object.keys(notifyForm).forEach((key) => {
        if (key in data) (notifyForm as any)[key] = data[key];
      });
    }
  } finally {
    notifyLoading.value = false;
  }
}

async function loadParamsTab() {
  paramLoading.value = true;
  try {
    const res: any = await settingsApi.getParams();
    systemParams.value = res.data || {};
  } finally {
    paramLoading.value = false;
  }
}

function onTabChange(tab: string | number) {
  if (tab === "broker" && !brokers.value.length) loadBrokerTab();
  if (tab === "notify") loadNotifyTab();
  if (tab === "params" && !Object.keys(systemParams.value).length) loadParamsTab();
}

async function saveBroker(broker: BrokerConfig) {
  saving.value = true;
  try {
    await settingsApi.updateBroker(broker.broker_name, {
      api_key: broker.api_key,
      api_secret: "",
      params: broker.params,
    });
    ElMessage.success(`${broker.broker_name} 配置已保存`);
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function testConnection(broker: BrokerConfig) {
  try {
    const res: any = await settingsApi.testBroker(broker.broker_name);
    const connected = res.data?.connected;
    ElMessage.success(connected ? `${broker.broker_name} 连接成功` : `${broker.broker_name} 连接失败`);
  } catch (e: any) {
    ElMessage.error(e.message || "测试失败");
  }
}

async function saveTradingMode() {
  saving.value = true;
  try {
    await settingsApi.updateTradingMode({ mode: tradingMode.value } as any);
    ElMessage.success("交易模式已更新");
  } catch (e: any) {
    ElMessage.error(e.message || "更新失败");
  } finally {
    saving.value = false;
  }
}

async function saveNotifications() {
  saving.value = true;
  try {
    await settingsApi.updateNotifications(notifyForm);
    ElMessage.success("通知配置已保存");
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function saveParams() {
  saving.value = true;
  try {
    await settingsApi.updateParams(systemParams.value);
    ElMessage.success("参数已保存");
  } catch (e: any) {
    ElMessage.error(e.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function resetParams() {
  try {
    await settingsApi.resetParams();
    await loadParamsTab();
    ElMessage.success("参数已重置");
  } catch (e: any) {
    ElMessage.error(e.message || "重置失败");
  }
}

async function changePassword() {
  if (!passwordForm.old_password || !passwordForm.new_password) {
    ElMessage.warning("请填写完整");
    return;
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.warning("两次密码不一致");
    return;
  }
  saving.value = true;
  try {
    await settingsApi.changePassword(passwordForm);
    ElMessage.success("密码已修改");
    passwordForm.old_password = "";
    passwordForm.new_password = "";
    passwordForm.confirm_password = "";
  } catch (e: any) {
    ElMessage.error(e.message || "修改失败");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="settings-view">
    <el-card shadow="hover">
      <el-tabs v-model="activeTab" @tab-change="onTabChange">
        <el-tab-pane label="券商配置" name="broker">
          <div v-loading="brokerLoading">
            <el-card v-for="broker in brokers" :key="broker.broker_name" shadow="hover" class="broker-card">
              <el-form label-width="100px" size="small">
                <el-row :gutter="16">
                  <el-col :span="8">
                    <el-form-item label="券商">
                      <el-input :model-value="broker.broker_name" disabled />
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="市场">
                      <el-tag>{{ broker.market }}</el-tag>
                    </el-form-item>
                  </el-col>
                  <el-col :span="8">
                    <el-form-item label="状态">
                      <el-tag :type="broker.connected ? 'success' : 'info'">
                        {{ broker.connected ? '已连接' : '未连接' }}
                      </el-tag>
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-row :gutter="16">
                  <el-col :span="12">
                    <el-form-item label="API Key">
                      <el-input v-model="broker.api_key" placeholder="API Key" show-password />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="操作">
                      <el-button size="small" @click="testConnection(broker)">测试连接</el-button>
                      <el-button size="small" type="primary" @click="saveBroker(broker)">保存</el-button>
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>
            </el-card>

            <el-divider />

            <h4 style="margin-bottom: 12px">交易模式</h4>
            <el-radio-group v-model="tradingMode" @change="saveTradingMode">
              <el-radio value="paper">模拟盘</el-radio>
              <el-radio value="live">实盘</el-radio>
            </el-radio-group>
          </div>
        </el-tab-pane>

        <el-tab-pane label="通知配置" name="notify">
          <div v-loading="notifyLoading">
            <el-form label-width="100px" style="max-width: 600px">
              <h4 class="section-title">邮件通知</h4>
              <el-form-item label="启用">
                <el-switch v-model="notifyForm.email_enabled" />
              </el-form-item>
              <el-form-item label="SMTP 主机">
                <el-input v-model="notifyForm.email_smtp_host" placeholder="smtp.example.com" />
              </el-form-item>
              <el-form-item label="SMTP 端口">
                <el-input-number v-model="notifyForm.email_smtp_port" :min="1" :max="65535" />
              </el-form-item>
              <el-form-item label="发件人">
                <el-input v-model="notifyForm.email_sender" />
              </el-form-item>
              <el-form-item label="邮箱密码">
                <el-input v-model="notifyForm.email_password" type="password" show-password />
              </el-form-item>
              <el-form-item label="收件人">
                <el-input v-model="notifyForm.email_recipient" placeholder="多个邮箱用逗号分隔" />
              </el-form-item>

              <el-divider />
              <h4 class="section-title">Webhook 通知</h4>
              <el-form-item label="启用">
                <el-switch v-model="notifyForm.webhook_enabled" />
              </el-form-item>
              <el-form-item label="URL">
                <el-input v-model="notifyForm.webhook_url" placeholder="https://..." />
              </el-form-item>
              <el-form-item label="Secret">
                <el-input v-model="notifyForm.webhook_secret" type="password" show-password />
              </el-form-item>

              <el-divider />
              <h4 class="section-title">通知等级</h4>
              <el-form-item label="通知等级">
                <el-checkbox-group v-model="notifyForm.notify_levels">
                  <el-checkbox value="info">信息</el-checkbox>
                  <el-checkbox value="warning">警告</el-checkbox>
                  <el-checkbox value="error">错误</el-checkbox>
                </el-checkbox-group>
              </el-form-item>

              <el-form-item>
                <el-button type="primary" :loading="saving" @click="saveNotifications">保存通知配置</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane label="系统参数" name="params">
          <div v-loading="paramLoading">
            <div v-for="group in PARAM_GROUPS" :key="group.label" class="param-group">
              <h4 class="param-group-title">{{ group.label }}</h4>
              <el-form label-width="140px" size="small">
                <el-form-item v-for="key in group.keys" :key="key" :label="PARAM_LABELS[key] || key">
                  <el-input v-model="systemParams[key]" />
                </el-form-item>
              </el-form>
            </div>

            <el-empty v-if="!Object.keys(systemParams).length" description="暂无可配置参数" />

            <div style="margin-top: 20px">
              <el-button type="primary" :loading="saving" @click="saveParams">保存参数</el-button>
              <el-button @click="resetParams">重置默认</el-button>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="个人设置" name="profile">
          <div v-loading="profileLoading">
            <el-descriptions :column="2" border v-if="profile" style="max-width: 600px; margin-bottom: 24px">
              <el-descriptions-item label="用户名">{{ profile.username }}</el-descriptions-item>
              <el-descriptions-item label="角色">{{ profile.role }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="profile.is_active ? 'success' : 'danger'">
                  {{ profile.is_active ? '正常' : '禁用' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="注册时间">{{ new Date(profile.created_at).toLocaleString() }}</el-descriptions-item>
            </el-descriptions>

            <el-divider />
            <h4 class="section-title">修改密码</h4>
            <el-form :model="passwordForm" label-width="100px" style="max-width: 400px">
              <el-form-item label="当前密码">
                <el-input v-model="passwordForm.old_password" type="password" show-password />
              </el-form-item>
              <el-form-item label="新密码">
                <el-input v-model="passwordForm.new_password" type="password" show-password />
              </el-form-item>
              <el-form-item label="确认密码">
                <el-input v-model="passwordForm.confirm_password" type="password" show-password />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="changePassword">修改密码</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.settings-view {
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h4 {
      margin: 0;
    }
  }

  .section-title {
    font-size: 14px;
    margin: 0 0 16px;
    padding-left: 8px;
    border-left: 3px solid var(--qp-primary);
  }

  .broker-card {
    margin-bottom: 12px;

    :deep(.el-card__body) {
      padding: 16px;
    }
  }

  .param-group {
    margin-bottom: 20px;
  }

  .param-group-title {
    font-size: 14px;
    color: var(--qp-text-secondary);
    margin: 0 0 12px;
    padding-left: 8px;
    border-left: 3px solid var(--qp-primary);
  }

  .param-desc {
    font-size: 12px;
    color: var(--qp-text-placeholder);
    margin-top: 4px;
  }
}
</style>
