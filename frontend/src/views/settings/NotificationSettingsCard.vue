<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { toast } from 'vue-sonner'

import {
  settingsApi,
  type NotificationLevel,
  type NotificationUpdate,
} from '@/api/settings'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

const loading = ref(true)
const saving = ref(false)
const testing = ref<'email' | 'webhook' | null>(null)
const loadError = ref('')
const form = reactive<NotificationUpdate>({
  email_enabled: false,
  email_smtp_host: '',
  email_smtp_port: 465,
  email_sender: '',
  email_password: '',
  email_use_ssl: true,
  email_recipient: '',
  webhook_enabled: false,
  webhook_url: '',
  webhook_secret: '',
  notify_levels: ['warning', 'error'],
})
const notificationLevels: Array<{ value: NotificationLevel; label: string }> = [
  { value: 'info', label: '信息' },
  { value: 'warning', label: '警告' },
  { value: 'error', label: '错误' },
]
const savedBaseline = ref('')
const hasEmailPassword = ref(false)
const hasWebhookSecret = ref(false)
const serialized = computed(() => JSON.stringify(form))
const dirty = computed(() => serialized.value !== savedBaseline.value)
const emailValid = computed(
  () =>
    !form.email_enabled ||
    (!!form.email_smtp_host &&
      !!form.email_sender &&
      !!form.email_recipient &&
      form.email_smtp_port >= 1 &&
      form.email_smtp_port <= 65535 &&
      (hasEmailPassword.value || !!form.email_password)),
)
const webhookValid = computed(
  () =>
    !form.webhook_enabled ||
    (/^https?:\/\//.test(form.webhook_url) &&
      (hasWebhookSecret.value || !!form.webhook_secret)),
)
const valid = computed(
  () => emailValid.value && webhookValid.value && form.notify_levels.length > 0,
)

function toggleLevel(level: NotificationLevel, checked: boolean) {
  form.notify_levels = checked
    ? [...new Set([...form.notify_levels, level])]
    : form.notify_levels.filter((item) => item !== level)
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const data = (await settingsApi.getNotifications()).data
    Object.assign(form, {
      email_enabled: data.email_enabled,
      email_smtp_host: data.email_smtp_host,
      email_smtp_port: data.email_smtp_port,
      email_sender: data.email_sender,
      email_password: '',
      email_use_ssl: data.email_use_ssl,
      email_recipient: data.email_recipient,
      webhook_enabled: data.webhook_enabled,
      webhook_url: data.webhook_url,
      webhook_secret: '',
      notify_levels: [...data.notify_levels],
    })
    hasEmailPassword.value = data.has_email_password
    hasWebhookSecret.value = data.has_webhook_secret
    savedBaseline.value = serialized.value
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '通知配置加载失败'
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!dirty.value || !valid.value) return
  saving.value = true
  try {
    await settingsApi.updateNotifications({ ...form })
    if (form.email_password) hasEmailPassword.value = true
    if (form.webhook_secret) hasWebhookSecret.value = true
    form.email_password = ''
    form.webhook_secret = ''
    savedBaseline.value = serialized.value
    toast.success('通知配置已保存')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '通知配置保存失败')
  } finally {
    saving.value = false
  }
}

async function sendTest(channel: 'email' | 'webhook') {
  if (dirty.value || !valid.value) return
  testing.value = channel
  try {
    const response =
      channel === 'email' ? await settingsApi.testEmail() : await settingsApi.testWebhook()
    response.data.sent ? toast.success('测试通知已发送') : toast.error('测试通知发送失败')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '测试通知发送失败')
  } finally {
    testing.value = null
  }
}

onMounted(load)
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>通知配置</CardTitle>
      <CardDescription>配置邮件、Webhook 与需要接收的告警等级。</CardDescription>
    </CardHeader>

    <CardContent v-if="loading" class="text-sm text-muted-foreground">
      正在加载通知配置…
    </CardContent>
    <CardContent v-else-if="loadError" class="space-y-3">
      <p class="text-sm text-destructive">{{ loadError }}</p>
      <Button type="button" variant="outline" @click="load">重试</Button>
    </CardContent>
    <CardContent v-else class="space-y-5">
      <section class="space-y-4 rounded-lg border p-4">
        <div class="flex items-center justify-between">
          <Label for="email-enabled">邮件通知</Label>
          <Switch id="email-enabled" v-model="form.email_enabled" />
        </div>
        <div class="grid gap-4 sm:grid-cols-2">
          <div class="space-y-2">
            <Label for="email-host">SMTP 主机</Label>
            <Input id="email-host" v-model="form.email_smtp_host" />
          </div>
          <div class="space-y-2">
            <Label for="email-port">端口</Label>
            <Input
              id="email-port"
              v-model.number="form.email_smtp_port"
              type="number"
              min="1"
              max="65535"
            />
          </div>
          <div class="space-y-2">
            <Label for="email-sender">发件人</Label>
            <Input id="email-sender" v-model="form.email_sender" type="email" />
          </div>
          <div class="space-y-2">
            <div class="flex items-center gap-2">
              <Label for="email-password">SMTP 密码</Label>
              <Badge
                v-if="hasEmailPassword"
                data-testid="email-password-configured"
                variant="secondary"
              >
                已配置
              </Badge>
            </div>
            <Input
              id="email-password"
              v-model="form.email_password"
              type="password"
              autocomplete="new-password"
              placeholder="留空则保留原密码"
            />
          </div>
          <div class="space-y-2">
            <Label for="email-recipient">收件人</Label>
            <Input id="email-recipient" v-model="form.email_recipient" type="email" />
          </div>
          <div class="flex items-center justify-between self-end rounded-md border px-3 py-2">
            <Label for="email-ssl">使用 SSL</Label>
            <Switch id="email-ssl" v-model="form.email_use_ssl" />
          </div>
        </div>
        <p v-if="form.email_enabled && !emailValid" class="text-sm text-destructive">
          请完整填写邮件服务器、发件人、收件人和凭据。
        </p>
        <Button
          type="button"
          data-testid="notification-test-email"
          variant="outline"
          :loading="testing === 'email'"
          :disabled="dirty || !valid || !form.email_enabled || testing !== null"
          @click="sendTest('email')"
        >
          测试邮件
        </Button>
      </section>

      <section class="space-y-4 rounded-lg border p-4">
        <div class="flex items-center justify-between">
          <Label for="webhook-enabled">Webhook</Label>
          <Switch id="webhook-enabled" v-model="form.webhook_enabled" />
        </div>
        <div class="space-y-2">
          <Label for="webhook-url">地址</Label>
          <Input id="webhook-url" v-model="form.webhook_url" type="url" />
        </div>
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <Label for="webhook-secret">签名密钥</Label>
            <Badge
              v-if="hasWebhookSecret"
              data-testid="webhook-secret-configured"
              variant="secondary"
            >
              已配置
            </Badge>
          </div>
          <Input
            id="webhook-secret"
            v-model="form.webhook_secret"
            type="password"
            autocomplete="new-password"
            placeholder="留空则保留原密钥"
          />
        </div>
        <p v-if="form.webhook_enabled && !webhookValid" class="text-sm text-destructive">
          请输入有效的 HTTP(S) 地址和签名密钥。
        </p>
        <Button
          type="button"
          data-testid="notification-test-webhook"
          variant="outline"
          :loading="testing === 'webhook'"
          :disabled="dirty || !valid || !form.webhook_enabled || testing !== null"
          @click="sendTest('webhook')"
        >
          测试 Webhook
        </Button>
      </section>

      <fieldset class="space-y-2">
        <legend class="text-sm font-medium">通知等级</legend>
        <label
          v-for="level in notificationLevels"
          :key="level.value"
          class="flex items-center gap-2 text-sm"
        >
          <Checkbox
            :model-value="form.notify_levels.includes(level.value)"
            @update:model-value="toggleLevel(level.value, $event === true)"
          />
          {{ level.label }}
        </label>
      </fieldset>
    </CardContent>

    <CardFooter v-if="!loading && !loadError" class="justify-end">
      <Button
        type="button"
        data-testid="notification-save"
        :loading="saving"
        :disabled="!dirty || !valid || saving"
        @click="save"
      >
        保存通知配置
      </Button>
    </CardFooter>
  </Card>
</template>
