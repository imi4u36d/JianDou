<template>
  <div class="page-shell login-view">
    <div class="login-view__intro">
      <p class="login-view__eyebrow">JianDou Admin</p>
      <h1>独立的后台管理入口</h1>
      <p>
        管理端只接受管理员账号登录。用户管理、账号启停、密码重置等操作都在这里完成。
      </p>
      <div class="login-view__badges">
        <span>Element Plus</span>
        <span>Admin Only</span>
        <span>Secure Session</span>
      </div>
    </div>

    <el-card class="surface-card login-view__card" shadow="never">
      <template #header>
        <div class="login-view__card-header">
          <div>
            <p class="login-view__eyebrow">Sign In</p>
            <h2>管理员登录</h2>
          </div>
          <el-tag type="warning" effect="plain">仅管理员</el-tag>
        </div>
      </template>

      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="用户名">
          <el-input v-model.trim="form.username" autocomplete="username" placeholder="请输入管理员用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" autocomplete="current-password" placeholder="请输入密码" show-password type="password" />
        </el-form-item>
        <el-button :loading="submitting" class="login-view__submit" native-type="submit" type="primary">
          进入管理系统
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { loginAndStoreSession, logoutAndClearSession } from "@/auth/session";

const route = useRoute();
const router = useRouter();

const form = reactive({
  username: "",
  password: ""
});
const submitting = ref(false);

function normalizeRedirectTarget(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return "/users";
  }
  return value;
}

async function handleSubmit() {
  submitting.value = true;
  try {
    const session = await loginAndStoreSession({
      username: form.username,
      password: form.password
    });
    if (session.user?.role !== "ADMIN") {
      await logoutAndClearSession();
      throw new Error("当前账号不是管理员，不能进入管理系统");
    }
    ElMessage.success("登录成功");
    await router.replace(normalizeRedirectTarget(route.query.redirect));
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "登录失败");
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.login-view {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(360px, 460px);
  align-items: center;
  gap: 40px;
  padding: 48px;
}

.login-view__intro {
  max-width: 620px;
}

.login-view__eyebrow {
  margin: 0 0 12px;
  color: var(--jd-text-soft);
  font-size: 0.78rem;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.login-view__intro h1,
.login-view__card-header h2 {
  margin: 0;
  font-family: inherit;
}

.login-view__intro h1 {
  font-size: clamp(2.5rem, 5vw, 4.3rem);
  line-height: 0.96;
}

.login-view__intro p {
  max-width: 540px;
  color: var(--jd-text-soft);
  font-size: 1.02rem;
}

.login-view__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 28px;
}

.login-view__badges span {
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.54);
  border: 1px solid rgba(23, 32, 42, 0.08);
  color: var(--jd-text-soft);
}

.login-view__card {
  border-radius: 28px;
}

.login-view__card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.login-view__alert {
  margin-bottom: 18px;
}

.login-view__submit {
  width: 100%;
  margin-top: 8px;
}

@media (max-width: 980px) {
  .login-view {
    grid-template-columns: 1fr;
    padding: 20px;
  }
}
</style>
