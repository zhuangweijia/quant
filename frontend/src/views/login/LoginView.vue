<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { toast } from 'vue-sonner'
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
const form = ref({
  username: '',
  password: '',
  confirm_password: '',
})

async function handleSubmit() {
  if (!form.value.username || !form.value.password) {
    toast.error('请填写用户名和密码')
    return
  }

  loading.value = true
  try {
    if (isRegister.value) {
      if (form.value.password !== form.value.confirm_password) {
        toast.error('两次密码不一致')
        return
      }
      await authStore.register(form.value)
      toast.success('注册成功，请使用新账户登录')
      isRegister.value = false
      form.value.password = ''
      form.value.confirm_password = ''
    } else {
      await authStore.login(form.value)
      const redirect = (route.query.redirect as string) || '/'
      router.push(redirect)
    }
  } catch (e: any) {
    toast.error(e.message || '操作失败，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-6 bg-background">
    <div class="w-full max-w-5xl grid lg:grid-cols-2 gap-8 items-center">
      <div class="hidden lg:flex flex-col gap-6">
        <Badge variant="outline" class="w-fit">Trading workspace</Badge>
        <h1 class="text-5xl font-bold tracking-tight leading-tight">
          Quant Desk
        </h1>
        <p class="text-muted-foreground text-lg max-w-md">
          面向多市场量化交易的统一控制台。把策略、回测、执行和风控放进一套更干净的操作界面里。
        </p>
        <div class="grid grid-cols-3 gap-3 mt-4">
          <div class="rounded-lg border p-4">
            <p class="text-xs text-muted-foreground uppercase tracking-wider mb-2">Markets</p>
            <p class="text-sm font-semibold">A股 / US / Crypto</p>
          </div>
          <div class="rounded-lg border p-4">
            <p class="text-xs text-muted-foreground uppercase tracking-wider mb-2">Latency</p>
            <p class="text-sm font-semibold">&lt; 150 ms routing</p>
          </div>
          <div class="rounded-lg border p-4">
            <p class="text-xs text-muted-foreground uppercase tracking-wider mb-2">Risk</p>
            <p class="text-sm font-semibold">Rules + alerts</p>
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
            {{ isRegister ? '创建交易工作区账户' : '登录你的交易工作台' }}
          </UiCardTitle>
          <UiCardDescription>
            {{ isRegister ? '先完成身份创建，再进入量化控制台。' : '继续访问策略、行情、交易与风控模块。' }}
          </UiCardDescription>
        </UiCardHeader>
        <UiCardContent>
          <form class="space-y-4" @submit.prevent="handleSubmit">
            <div class="space-y-2">
              <Label for="username">用户名</Label>
              <div class="relative">
                <UserRound class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="username"
                  v-model="form.username"
                  placeholder="输入用户名"
                  class="pl-9"
                  minlength="3"
                  maxlength="64"
                />
              </div>
            </div>

            <div class="space-y-2">
              <Label for="password">密码</Label>
              <div class="relative">
                <LockKeyhole class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="password"
                  v-model="form.password"
                  type="password"
                  placeholder="输入密码"
                  class="pl-9"
                  minlength="8"
                  maxlength="64"
                />
              </div>
            </div>

            <div v-if="isRegister" class="space-y-2">
              <Label for="confirm_password">确认密码</Label>
              <div class="relative">
                <LockKeyhole class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
                <Input
                  id="confirm_password"
                  v-model="form.confirm_password"
                  type="password"
                  placeholder="再次输入密码"
                  class="pl-9"
                />
              </div>
            </div>

            <Button type="submit" size="lg" :loading="loading" class="w-full">
              <span>{{ isRegister ? '创建账户' : '进入控制台' }}</span>
              <ArrowRight class="ml-2 size-4" />
            </Button>
          </form>

          <div class="mt-4 text-center text-sm text-muted-foreground">
            <span>{{ isRegister ? '已有账户？' : '还没有账户？' }}</span>
            <button
              type="button"
              class="text-primary font-medium hover:underline ml-1"
              @click="isRegister = !isRegister"
            >
              {{ isRegister ? '返回登录' : '立即注册' }}
            </button>
          </div>
        </UiCardContent>
      </UiCard>
    </div>
  </div>
</template>
