<script setup lang="ts">
import dayjs from 'dayjs'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import {
  settingsApi,
  type PasswordChange,
  type ProfileSettings,
} from '@/api/settings'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const profile = ref<ProfileSettings | null>(null)
const loading = ref(true)
const loadError = ref('')
const submitting = ref(false)
const form = reactive<PasswordChange>({
  old_password: '',
  new_password: '',
  confirm_password: '',
})
const passwordError = computed(() => {
  if (!form.old_password && !form.new_password && !form.confirm_password) return ''
  if (form.old_password.length < 8) return '当前密码至少 8 位'
  if (form.new_password.length < 8 || form.new_password.length > 64) {
    return '新密码需为 8–64 位'
  }
  if (!/[A-Za-z]/.test(form.new_password) || !/\d/.test(form.new_password)) {
    return '新密码需包含字母和数字'
  }
  if (form.new_password !== form.confirm_password) return '两次密码不一致'
  return ''
})
const canSubmit = computed(
  () =>
    !!form.old_password &&
    !!form.new_password &&
    !!form.confirm_password &&
    !passwordError.value,
)

async function loadProfile() {
  loading.value = true
  loadError.value = ''
  try {
    profile.value = (await settingsApi.getProfile()).data
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : '个人资料加载失败'
  } finally {
    loading.value = false
  }
}

async function submitPassword() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    await settingsApi.changePassword({ ...form })
    toast.success('密码已修改，请重新登录')
    authStore.logout()
    await router.push('/login')
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '密码修改失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadProfile)
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle>账户安全</CardTitle>
      <CardDescription>查看账户信息并修改登录密码。</CardDescription>
    </CardHeader>
    <CardContent class="grid gap-8 lg:grid-cols-2">
      <section>
        <h3 class="mb-4 text-sm font-medium">个人资料</h3>
        <p v-if="loading" class="text-sm text-muted-foreground">正在加载个人资料…</p>
        <div v-else-if="loadError" class="space-y-3">
          <p class="text-sm text-destructive">{{ loadError }}</p>
          <Button
            type="button"
            data-testid="profile-retry"
            variant="outline"
            @click="loadProfile"
          >
            重试
          </Button>
        </div>
        <dl
          v-else-if="profile"
          class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-3 text-sm"
        >
          <dt class="text-muted-foreground">用户名</dt>
          <dd>{{ profile.username }}</dd>
          <dt class="text-muted-foreground">角色</dt>
          <dd>{{ profile.role === 'admin' ? '管理员' : '用户' }}</dd>
          <dt class="text-muted-foreground">状态</dt>
          <dd>{{ profile.is_active ? '正常' : '停用' }}</dd>
          <dt class="text-muted-foreground">创建时间</dt>
          <dd>
            {{ profile.created_at ? dayjs(profile.created_at).format('YYYY-MM-DD HH:mm') : '—' }}
          </dd>
        </dl>
      </section>

      <form class="space-y-4" @submit.prevent="submitPassword">
        <h3 class="text-sm font-medium">修改密码</h3>
        <div class="space-y-2">
          <Label for="old-password">当前密码</Label>
          <Input
            id="old-password"
            v-model="form.old_password"
            type="password"
            autocomplete="current-password"
          />
        </div>
        <div class="space-y-2">
          <Label for="new-password">新密码</Label>
          <Input
            id="new-password"
            v-model="form.new_password"
            type="password"
            autocomplete="new-password"
          />
        </div>
        <div class="space-y-2">
          <Label for="confirm-password">确认新密码</Label>
          <Input
            id="confirm-password"
            v-model="form.confirm_password"
            type="password"
            autocomplete="new-password"
          />
        </div>
        <p v-if="passwordError" class="text-sm text-destructive">{{ passwordError }}</p>
        <Button
          data-testid="password-submit"
          type="submit"
          :loading="submitting"
          :disabled="!canSubmit || submitting"
        >
          修改密码
        </Button>
      </form>
    </CardContent>
  </Card>
</template>
