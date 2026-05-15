<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import { ElMessage } from "element-plus";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const isRegister = ref(false);
const loading = ref(false);
const form = ref({
  username: "",
  password: "",
  confirm_password: "",
});

async function handleSubmit() {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning("请填写用户名和密码");
    return;
  }

  loading.value = true;
  try {
    if (isRegister.value) {
      if (form.value.password !== form.value.confirm_password) {
        ElMessage.error("两次密码不一致");
        return;
      }
      await authStore.register(form.value);
      ElMessage.success("注册成功，请登录");
      isRegister.value = false;
      form.value.password = "";
      form.value.confirm_password = "";
    } else {
      await authStore.login(form.value);
      const redirect = (route.query.redirect as string) || "/";
      router.push(redirect);
    }
  } catch (e: any) {
    ElMessage.error(e.message || "操作失败");
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">QuantPlatform</h1>
      <p class="login-subtitle">{{ isRegister ? "创建账户" : "多市场量化交易平台" }}</p>

      <el-form @submit.prevent="handleSubmit" class="login-form">
        <el-form-item>
          <el-input
            v-model="form.username"
            placeholder="用户名"
            prefix-icon="User"
            size="large"
            :minlength="3"
            :maxlength="64"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
            :minlength="8"
            :maxlength="64"
          />
        </el-form-item>
        <el-form-item v-if="isRegister">
          <el-input
            v-model="form.confirm_password"
            type="password"
            placeholder="确认密码"
            prefix-icon="Lock"
            size="large"
            show-password
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          @click="handleSubmit"
          class="login-btn"
        >
          {{ isRegister ? "注册" : "登录" }}
        </el-button>
      </el-form>

      <div class="login-footer">
        <span v-if="!isRegister">
          还没有账户？
          <el-link type="primary" @click="isRegister = true">立即注册</el-link>
        </span>
        <span v-else>
          已有账户？
          <el-link type="primary" @click="isRegister = false">返回登录</el-link>
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 90%;
  max-width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.login-title {
  text-align: center;
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 8px;
}

.login-subtitle {
  text-align: center;
  color: #909399;
  margin-bottom: 32px;
  font-size: 14px;
}

.login-form {
  .el-form-item {
    margin-bottom: 20px;
  }
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 16px;
}

.login-footer {
  text-align: center;
  margin-top: 20px;
  color: #909399;
  font-size: 14px;
}
</style>
