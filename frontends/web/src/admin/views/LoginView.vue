<template>
  <section class="auth-screen admin-login-screen">
    <AuthCarouselBackground />
    <div class="auth-screen__panel">
      <div class="auth-screen__brand">
        <img alt="煎豆 Logo" class="auth-screen__logo" src="/brand/jiandou-mark.svg" />
        <div>
          <h1>管理端登录</h1>
          <p>企业级配置与账号管理</p>
        </div>
      </div>
      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="用户名" class="auth-form-item">
          <el-input v-model.trim="form.username" autocomplete="username" placeholder="用户名" />
        </el-form-item>
        <el-form-item label="密码" class="auth-form-item">
          <el-input
            v-model="form.password"
            autocomplete="current-password"
            placeholder="密码"
            show-password
            type="password"
          />
        </el-form-item>
        <el-button :loading="submitting" class="auth-screen__submit" native-type="submit" type="primary">
          登录
        </el-button>
      </el-form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import AuthCarouselBackground from "@/components/auth/AuthCarouselBackground.vue";
import { loginAndStoreSession, logoutAndClearSession } from "@/auth/session";
import { normalizeAuthRedirectTarget } from "@/auth/redirect";

const route = useRoute();
const router = useRouter();

const form = reactive({
  username: "",
  password: ""
});
const submitting = ref(false);

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
    await router.replace(normalizeAuthRedirectTarget(route.query.redirect, "/admin"));
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "登录失败");
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.admin-login-screen {
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  overflow: hidden;
  isolation: isolate;
  background: var(--bg-base);
}

.auth-screen__panel {
  position: relative;
  z-index: 1;
  width: min(430px, 100%);
  display: grid;
  gap: 18px;
  padding: 22px;
  border-radius: 24px;
  border: 1px solid rgba(255, 255, 255, 0.68);
  background: var(--glass-panel-bg);
  box-shadow:
    var(--glass-panel-shadow),
    var(--glass-sheen);
  backdrop-filter: var(--glass-panel-blur);
  -webkit-backdrop-filter: var(--glass-panel-blur);
  max-width: calc(100% - 28px);
}

.auth-screen__brand {
  display: grid;
  gap: 10px;
  text-align: left;
}

.auth-screen__logo {
  width: 44px;
  height: 44px;
}

.auth-screen__brand h1 {
  margin: 0;
  line-height: 1.15;
  color: var(--text-strong);
  font-size: clamp(1.45rem, 4vw, 1.9rem);
}

.auth-screen__brand p {
  margin: 6px 0 0;
  color: var(--text-body);
}

:deep(.el-form-item__label) {
  color: var(--text-body);
  font-weight: 800;
  padding-bottom: 6px;
}

:deep(.el-form-item) {
  margin-bottom: 12px;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

:deep(.el-input__wrapper) {
  min-height: 48px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.56);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.78));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.86),
    inset 0 -1px 0 rgba(15, 23, 42, 0.03);
  transition: box-shadow 180ms ease, border-color 180ms ease, background 180ms ease;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: rgba(99, 102, 241, 0.64);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.95),
    0 0 0 1px rgba(99, 102, 241, 0.36),
    0 0 0 4px rgba(99, 102, 241, 0.18);
}

:deep(.el-input__inner) {
  min-height: 30px;
}

.auth-screen__submit {
  --el-button-bg-color: transparent;
  --el-button-text-color: var(--accent-blue);
  --el-button-hover-text-color: var(--accent-blue);
  width: 100%;
  margin-top: 4px;
  height: 48px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.58);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.08) 52%, rgba(255, 255, 255, 0.24)),
    linear-gradient(180deg, rgba(99, 102, 241, 0.22), rgba(99, 102, 241, 0.1));
  backdrop-filter: blur(24px) saturate(1.8) brightness(1.06);
  -webkit-backdrop-filter: blur(24px) saturate(1.8) brightness(1.06);
  font-weight: 800;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.92),
    inset 0 -1px 0 rgba(15, 23, 42, 0.08),
    0 12px 28px rgba(99, 102, 241, 0.14),
    0 2px 6px rgba(15, 23, 42, 0.08);
  transition:
    background 180ms ease,
    box-shadow 180ms ease,
    transform 180ms ease,
    opacity 180ms ease;
}

.auth-screen__submit:hover:not(:disabled),
.auth-screen__submit:focus-visible {
  transform: translateY(-1px);
  background:
    linear-gradient(145deg, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.12) 52%, rgba(255, 255, 255, 0.28)),
    linear-gradient(180deg, rgba(99, 102, 241, 0.3), rgba(99, 102, 241, 0.14));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.96),
    inset 0 -1px 0 rgba(15, 23, 42, 0.08),
    0 16px 34px rgba(99, 102, 241, 0.18),
    0 4px 12px rgba(15, 23, 42, 0.1);
}

.auth-screen__submit.is-loading,
.auth-screen__submit.is-disabled,
.auth-screen__submit:disabled {
  opacity: 0.75;
}

@media (max-width: 860px) {
  .admin-login-screen {
    padding: 16px;
  }

  .auth-screen__panel {
    gap: 14px;
    padding: 18px;
    border-radius: 22px;
    max-width: 100%;
  }
}
</style>
