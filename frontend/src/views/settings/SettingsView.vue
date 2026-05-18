<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toast } from 'vue-sonner'
import { useTheme } from '@/composables/useTheme'
import { settingsApi } from '@/api/settings'
import { BasicPage } from '@/components/global-layout'
import Button from '@/components/ui/button/Button.vue'
import Label from '@/components/ui/label/Label.vue'
import Input from '@/components/ui/input/Input.vue'
import UiSwitch from '@/components/ui/switch/Switch.vue'
import UiSkeleton from '@/components/ui/skeleton/Skeleton.vue'
import {
  Card as UiCard,
  CardHeader as UiCardHeader,
  CardContent as UiCardContent,
  CardTitle as UiCardTitle,
  CardDescription as UiCardDescription,
} from '@/components/ui/card'
import {
  Select as UiSelect,
  SelectContent as UiSelectContent,
  SelectItem as UiSelectItem,
  SelectTrigger as UiSelectTrigger,
  SelectValue as UiSelectValue,
} from '@/components/ui/select'
import {
  Tabs as UiTabs,
  TabsContent as UiTabsContent,
  TabsList as UiTabsList,
  TabsTrigger as UiTabsTrigger,
} from '@/components/ui/tabs'
import {
  Separator as UiSeparator,
} from '@/components/ui/separator'
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

const { isDark, toggleTheme, theme, setTheme } = useTheme()
const loading = ref(false)
const activeTab = ref('profile')

const profile = ref({ username: '', email: '' })
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' })
const passwordDialog = ref(false)

const brokerName = ref('default')
const broker = ref({ api_key: '', api_secret: '', testnet: false })
const tradingMode = ref('paper')

const notifications = ref({ email_enabled: false, webhook_enabled: false, email_address: '', webhook_url: '' })

const themeColors = [
  { value: 'zinc', label: 'Zinc' },
  { value: 'red', label: 'Red' },
  { value: 'rose', label: 'Rose' },
  { value: 'orange', label: 'Orange' },
  { value: 'green', label: 'Green' },
  { value: 'blue', label: 'Blue' },
  { value: 'yellow', label: 'Yellow' },
  { value: 'violet', label: 'Violet' },
]

async function loadSettings() {
  loading.value = true
  try {
    const [profileRes, brokerRes, modeRes, notifRes] = await Promise.allSettled([
      settingsApi.getProfile(),
      settingsApi.getBrokers(),
      settingsApi.getTradingMode(),
      settingsApi.getNotifications(),
    ])
    if (profileRes.status === 'fulfilled') {
      const d = (profileRes.value as any).data
      profile.value = { username: d?.username || '', email: d?.email || '' }
    }
    if (brokerRes.status === 'fulfilled') {
      const d = (brokerRes.value as any).data
      if (Array.isArray(d) && d.length) {
        brokerName.value = d[0].broker_name || 'default'
        broker.value = { api_key: d[0].api_key || '', api_secret: d[0].api_secret || '', testnet: d[0].testnet || false }
      }
    }
    if (modeRes.status === 'fulfilled') tradingMode.value = (modeRes.value as any).data?.mode || 'paper'
    if (notifRes.status === 'fulfilled') {
      const d = (notifRes.value as any).data
      notifications.value = {
        email_enabled: d?.email_enabled || false,
        webhook_enabled: d?.webhook_enabled || false,
        email_address: d?.email_address || '',
        webhook_url: d?.webhook_url || '',
      }
    }
  } finally { loading.value = false }
}

async function saveBroker() {
  try {
    await settingsApi.updateBroker(brokerName.value, broker.value)
    toast.success('券商配置已保存')
  } catch (e: any) { toast.error(e.message || '保存失败') }
}

async function testBrokerConnection() {
  try {
    await settingsApi.testBroker(brokerName.value)
    toast.success('连接测试成功')
  } catch (e: any) { toast.error(e.message || '连接测试失败') }
}

async function saveTradingMode() {
  try {
    await settingsApi.updateTradingMode({ mode: tradingMode.value })
    toast.success('交易模式已更新')
  } catch (e: any) { toast.error(e.message || '保存失败') }
}

async function saveNotifications() {
  try {
    await settingsApi.updateNotifications(notifications.value as any)
    toast.success('通知设置已保存')
  } catch (e: any) { toast.error(e.message || '保存失败') }
}

async function testEmail() {
  try {
    await settingsApi.testEmail()
    toast.success('测试邮件已发送')
  } catch (e: any) { toast.error(e.message || '发送失败') }
}

async function handleChangePassword() {
  if (!passwordForm.value.old_password || !passwordForm.value.new_password) {
    toast.error('请填写完整密码信息')
    return
  }
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    toast.error('两次密码不一致')
    return
  }
  try {
    await settingsApi.changePassword(passwordForm.value as any)
    toast.success('密码已修改')
    passwordDialog.value = false
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' }
  } catch (e: any) { toast.error(e.message || '修改失败') }
}

onMounted(loadSettings)
</script>

<template>
  <BasicPage title="设置" description="管理账户、券商、通知和外观配置">
    <UiTabs v-model="activeTab">
      <UiTabsList>
        <UiTabsTrigger value="profile">账户</UiTabsTrigger>
        <UiTabsTrigger value="broker">券商</UiTabsTrigger>
        <UiTabsTrigger value="notifications">通知</UiTabsTrigger>
        <UiTabsTrigger value="appearance">外观</UiTabsTrigger>
      </UiTabsList>

      <UiTabsContent value="profile" class="mt-6 space-y-6">
        <UiCard>
          <UiCardHeader>
            <UiCardTitle>个人资料</UiCardTitle>
            <UiCardDescription>管理你的账户信息</UiCardDescription>
          </UiCardHeader>
          <UiCardContent v-if="loading">
            <div class="space-y-4">
              <UiSkeleton class="h-10 w-full" />
              <UiSkeleton class="h-10 w-full" />
            </div>
          </UiCardContent>
          <UiCardContent v-else class="space-y-4">
            <div class="space-y-2">
              <Label>用户名</Label>
              <Input v-model="profile.username" disabled />
            </div>
            <div class="space-y-2">
              <Label>邮箱</Label>
              <Input v-model="profile.email" placeholder="your@email.com" />
            </div>
            <UiSeparator />
            <Button variant="outline" @click="passwordDialog = true">修改密码</Button>
          </UiCardContent>
        </UiCard>
      </UiTabsContent>

      <UiTabsContent value="broker" class="mt-6 space-y-6">
        <UiCard>
          <UiCardHeader>
            <UiCardTitle>券商配置</UiCardTitle>
            <UiCardDescription>配置交易所 API 连接</UiCardDescription>
          </UiCardHeader>
          <UiCardContent class="space-y-4">
            <div class="space-y-2">
              <Label>API Key</Label>
              <Input v-model="broker.api_key" type="password" placeholder="输入 API Key" />
            </div>
            <div class="space-y-2">
              <Label>API Secret</Label>
              <Input v-model="broker.api_secret" type="password" placeholder="输入 API Secret" />
            </div>
            <div class="flex items-center justify-between">
              <Label>使用测试网</Label>
              <UiSwitch v-model:checked="broker.testnet" />
            </div>
            <div class="flex gap-3">
              <Button @click="saveBroker">保存配置</Button>
              <Button variant="outline" @click="testBrokerConnection">测试连接</Button>
            </div>
          </UiCardContent>
        </UiCard>

        <UiCard>
          <UiCardHeader>
            <UiCardTitle>交易模式</UiCardTitle>
          </UiCardHeader>
          <UiCardContent class="space-y-4">
            <div class="space-y-2">
              <Label>当前模式</Label>
              <UiSelect v-model="tradingMode">
                <UiSelectTrigger class="w-48"><UiSelectValue /></UiSelectTrigger>
                <UiSelectContent>
                  <UiSelectItem value="paper">模拟盘</UiSelectItem>
                  <UiSelectItem value="live">实盘</UiSelectItem>
                </UiSelectContent>
              </UiSelect>
            </div>
            <Button @click="saveTradingMode">保存</Button>
          </UiCardContent>
        </UiCard>
      </UiTabsContent>

      <UiTabsContent value="notifications" class="mt-6 space-y-6">
        <UiCard>
          <UiCardHeader>
            <UiCardTitle>通知设置</UiCardTitle>
            <UiCardDescription>配置风控告警的通知方式</UiCardDescription>
          </UiCardHeader>
          <UiCardContent class="space-y-6">
            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <p class="font-medium">邮件通知</p>
                  <p class="text-sm text-muted-foreground">通过邮件接收风控告警</p>
                </div>
                <UiSwitch v-model:checked="notifications.email_enabled" />
              </div>
              <div v-if="notifications.email_enabled" class="space-y-2">
                <Label>邮箱地址</Label>
                <div class="flex gap-2">
                  <Input v-model="notifications.email_address" placeholder="your@email.com" class="flex-1" />
                  <Button variant="outline" @click="testEmail">测试</Button>
                </div>
              </div>
            </div>

            <UiSeparator />

            <div class="space-y-4">
              <div class="flex items-center justify-between">
                <div>
                  <p class="font-medium">Webhook 通知</p>
                  <p class="text-sm text-muted-foreground">通过 Webhook 推送告警</p>
                </div>
                <UiSwitch v-model:checked="notifications.webhook_enabled" />
              </div>
              <div v-if="notifications.webhook_enabled" class="space-y-2">
                <Label>Webhook URL</Label>
                <Input v-model="notifications.webhook_url" placeholder="https://..." />
              </div>
            </div>

            <Button @click="saveNotifications">保存设置</Button>
          </UiCardContent>
        </UiCard>
      </UiTabsContent>

      <UiTabsContent value="appearance" class="mt-6 space-y-6">
        <UiCard>
          <UiCardHeader>
            <UiCardTitle>外观</UiCardTitle>
            <UiCardDescription>自定义界面主题和配色</UiCardDescription>
          </UiCardHeader>
          <UiCardContent class="space-y-6">
            <div class="space-y-3">
              <Label>主题模式</Label>
              <div class="flex items-center gap-3">
                <Button
                  :variant="!isDark ? 'default' : 'outline'"
                  size="sm"
                  @click="toggleTheme"
                >
                  {{ isDark ? '切换到亮色' : '切换到暗色' }}
                </Button>
              </div>
            </div>

            <UiSeparator />

            <div class="space-y-3">
              <Label>主题色</Label>
              <div class="flex flex-wrap gap-2">
                <Button
                  v-for="color in themeColors"
                  :key="color.value"
                  :variant="theme === color.value ? 'default' : 'outline'"
                  size="sm"
                  @click="setTheme(color.value as any)"
                >
                  {{ color.label }}
                </Button>
              </div>
            </div>
          </UiCardContent>
        </UiCard>
      </UiTabsContent>
    </UiTabs>

    <UiAlertDialog v-model:open="passwordDialog">
      <UiAlertDialogContent>
        <UiAlertDialogHeader>
          <UiAlertDialogTitle>修改密码</UiAlertDialogTitle>
          <UiAlertDialogDescription>输入旧密码和新密码</UiAlertDialogDescription>
        </UiAlertDialogHeader>
        <div class="space-y-4 py-2">
          <div class="space-y-2">
            <Label>旧密码</Label>
            <Input v-model="passwordForm.old_password" type="password" />
          </div>
          <div class="space-y-2">
            <Label>新密码</Label>
            <Input v-model="passwordForm.new_password" type="password" />
          </div>
          <div class="space-y-2">
            <Label>确认新密码</Label>
            <Input v-model="passwordForm.confirm_password" type="password" />
          </div>
        </div>
        <UiAlertDialogFooter>
          <UiAlertDialogCancel @click="passwordForm = { old_password: '', new_password: '', confirm_password: '' }">取消</UiAlertDialogCancel>
          <UiAlertDialogAction @click="handleChangePassword">确认修改</UiAlertDialogAction>
        </UiAlertDialogFooter>
      </UiAlertDialogContent>
    </UiAlertDialog>
  </BasicPage>
</template>
