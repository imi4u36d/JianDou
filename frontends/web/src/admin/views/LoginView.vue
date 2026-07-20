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
      <el-form aria-label="管理员登录" label-position="top" @submit.prevent="handleSubmit">
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
  background: #eef0f4;
}

.admin-login-screen :deep(.auth-carousel-bg) {
  opacity: 0.16;
  filter: saturate(0.45);
}

.auth-screen__panel {
  position: relative;
  z-index: 1;
  width: min(430px, 100%);
  display: grid;
  gap: 22px;
  padding: 30px;
  border: 1px solid var(--jd-border);
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 18px 54px rgba(23, 26, 33, 0.12);
  max-width: calc(100% - 28px);
}

.auth-screen__brand {
  display: flex;
  align-items: center;
  gap: 14px;
  text-align: left;
}

.auth-screen__logo {
  width: 40px;
  height: 40px;
}

.auth-screen__brand h1 {
  margin: 0;
  line-height: 1.15;
  color: var(--jd-text);
  font-size: clamp(1.35rem, 4vw, 1.7rem);
  font-weight: 740;
}

.auth-screen__brand p {
  margin: 6px 0 0;
  color: var(--jd-text-soft);
  font-size: 0.82rem;
}

:deep(.el-form-item__label) {
  padding-bottom: 5px;
  color: var(--jd-text-soft);
  font-size: 0.78rem;
  font-weight: 650;
}

:deep(.el-form-item) {
  margin-bottom: 12px;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

:deep(.el-input__wrapper) {
  min-height: 44px;
  border: 1px solid var(--jd-border);
  border-radius: 9px;
  background: #fff;
  box-shadow: none !important;
  transition: box-shadow 180ms ease, border-color 180ms ease, background 180ms ease;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: var(--jd-accent);
  box-shadow: var(--jd-shadow-focus) !important;
}

:deep(.el-input__inner) {
  min-height: 30px;
}

.auth-screen__submit {
  width: 100%;
  margin-top: 4px;
  height: 44px;
  border-radius: 9px;
  font-weight: 700;
  box-shadow: none;
  transition: background-color 160ms ease, opacity 160ms ease;
}

.auth-screen__submit:hover:not(:disabled),
.auth-screen__submit:focus-visible {
  background: #4d4ed1;
  box-shadow: none;
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
    padding: 22px;
    border-radius: 12px;
    max-width: 100%;
  }
}
</style>
