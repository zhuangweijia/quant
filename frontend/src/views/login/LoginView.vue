<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
import { toTypedSchema } from '@vee-validate/zod'
import { useForm } from 'vee-validate'
import { z } from 'zod'
import Button from '@/components/ui/button/Button.vue'
import { Card as UiCard, CardHeader as UiCardHeader, CardContent as UiCardContent, CardTitle as UiCardTitle, CardDescription as UiCardDescription } from '@/components/ui/card'
import Input from '@/components/ui/input/Input.vue'
import Label from '@/components/ui/label/Label.vue'
import Badge from '@/components/ui/badge/Badge.vue'
import { useAuthStore } from '@/stores/auth'
import { ArrowRight, LockKeyhole, TrendingUp, UserRound } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const isRegister = ref(false)
const loading = ref(false)

const loginSchema = z.object({
  username: z.string().min(3, '用户名至少 3 个字符').max(64, '用户名最多 64 个字符'),
  password: z.string().min(8, '密码至少 8 个字符').max(64, '密码最多 64 个字符'),
  confirm_password: z.string().optional(),
})

const registerSchema = loginSchema.extend({
  confirm_password: z.string().min(8, '密码至少 8 个字符'),
}).refine(data => data.password === data.confirm_password, {
  message: '两次密码不一致',
  path: ['confirm_password'],
})

const { handleSubmit, errors, setValues, setFieldError, defineField } = useForm({
  validationSchema: toTypedSchema(loginSchema),
  initialValues: { username: '', password: '', confirm_password: '' },
})

const [username, usernameAttrs] = defineField('username')
const [password, passwordAttrs] = defineField('password')
const [confirmPassword, confirmPasswordAttrs] = defineField('confirm_password')

const toggleMode = () => {
  isRegister.value = !isRegister.value
  setValues({ username: '', password: '', confirm_password: '' })
}

const onSubmit = handleSubmit(async (values) => {
  if (isRegister.value) {
    const result = registerSchema.safeParse(values)
    if (!result.success) {
      for (const issue of result.error.issues) {
        const field = issue.path[0] as 'username' | 'password' | 'confirm_password'
        setFieldError(field, issue.message)
      }
      return
    }
  }

  loading.value = true
  try {
    if (isRegister.value) {
      await authStore.register(values as any)
      toast.success('注册成功，请使用新账户登录')
      isRegister.value = false
      setValues({ username: '', password: '', confirm_password: '' })
    } else {
      await authStore.login({ username: values.username, password: values.password })
      const redirect = (route.query.redirect as string) || '/'
      router.push(redirect)
    }
  } catch (e: any) {
    toast.error(e.message || '操作失败，请稍后重试')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-6 bg-background">
    <div class="w-full max-w-5xl grid lg:grid-cols-2 gap-8 items-center">
      <div class="hidden lg:flex flex-col gap-6">
        <Badge variant="outline" class="w-fit">每日智能选股</Badge>
        <h1 class="text-5xl font-bold tracking-tight leading-tight">
          Quant Desk
        </h1>
        <p class="text-muted-foreground text-lg max-w-md">
          每日分析沪深 300，筛出值得关注的股票，并用简单清楚的理由解释每一次推荐。
        </p>
        <div class="grid grid-cols-3 gap-3 mt-4">
          <div class="rounded-lg border p-4">
            <p class="text-xs text-muted-foreground uppercase tracking-wider mb-2">股票池</p>
            <p class="text-sm font-semibold">沪深 300</p>
          </div>
          <div class="rounded-lg border p-4">
            <p class="text-xs text-muted-foreground uppercase tracking-wider mb-2">更新频率</p>
            <p class="text-sm font-semibold">每个交易日</p>
          </div>
          <div class="rounded-lg border p-4">
            <p class="text-xs text-muted-foreground uppercase tracking-wider mb-2">分析结果</p>
            <p class="text-sm font-semibold">强推 · 观望 · 回避</p>
          </div>
        </div>
      </div>

      <UiCard class="w-full max-w-md mx-auto lg:mx-0">
        <UiCardHeader class="space-y-1">
          <div class="flex items-center gap-2 mb-2 lg:hidden">
            <TrendingUp class="size-5 text-primary" />
            <span class="font-bold">Quant Desk</span>
          </div>
          <UiCardTitle class="text-2xl">
            {{ isRegister ? '创建 Quant Desk 账户' : '登录 Quant Desk' }}
          </UiCardTitle>
          <UiCardDescription>
            {{ isRegister ? '创建账户，开始查看每日选股分析。' : '查看下一交易日组合建议、仓位调整依据与主要风险' }}
          </UiCardDescription>
        </UiCardHeader>
        <UiCardContent>
          <form class="space-y-4" @submit.prevent="onSubmit">
            <div class="space-y-2">
              <Label for="username">用户名</Label>
              <div class="relative">
                <UserRound class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="username"
                  v-model="username"
                  v-bind="usernameAttrs"
                  placeholder="输入用户名"
                  class="pl-9"
                  :aria-invalid="!!errors.username"
                />
              </div>
              <p v-if="errors.username" class="text-xs text-destructive mt-1">{{ errors.username }}</p>
            </div>

            <div class="space-y-2">
              <Label for="password">密码</Label>
              <div class="relative">
                <LockKeyhole class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="password"
                  v-model="password"
                  v-bind="passwordAttrs"
                  type="password"
                  placeholder="输入密码"
                  class="pl-9"
                  :aria-invalid="!!errors.password"
                />
              </div>
              <p v-if="errors.password" class="text-xs text-destructive mt-1">{{ errors.password }}</p>
            </div>

            <div v-if="isRegister" class="space-y-2">
              <Label for="confirm_password">确认密码</Label>
              <div class="relative">
                <LockKeyhole class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="confirm_password"
                  v-model="confirmPassword"
                  v-bind="confirmPasswordAttrs"
                  type="password"
                  placeholder="再次输入密码"
                  class="pl-9"
                  :aria-invalid="!!errors.confirm_password"
                />
              </div>
              <p v-if="errors.confirm_password" class="text-xs text-destructive mt-1">{{ errors.confirm_password }}</p>
            </div>

            <Button type="submit" size="lg" :loading="loading" class="w-full">
              <span>{{ isRegister ? '创建账户' : '查看今日选股' }}</span>
              <ArrowRight class="ml-2 size-4" />
            </Button>
          </form>

          <div class="mt-4 text-center text-sm text-muted-foreground">
            <span>{{ isRegister ? '已有账户？' : '还没有账户？' }}</span>
            <button
              type="button"
              class="text-primary font-medium hover:underline ml-1"
              @click="toggleMode"
            >
              {{ isRegister ? '返回登录' : '立即注册' }}
            </button>
          </div>
        </UiCardContent>
      </UiCard>
    </div>
  </div>
</template>
