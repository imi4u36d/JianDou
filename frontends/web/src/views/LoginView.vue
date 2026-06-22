<template>
  <section class="auth-screen">
    <div class="auth-screen__panel">
      <div class="auth-screen__hero">
        <h1>进入工作台</h1>
      </div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label class="auth-form__field">
          <span class="auth-form__field-label">用户名</span>
          <input v-model="username" autocomplete="username" placeholder="用户名" type="text" />
        </label>
        <label class="auth-form__field">
          <span class="auth-form__field-label">密码</span>
          <div class="auth-form__password-wrap">
            <input
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              placeholder="密码"
            />
            <button
              :aria-label="showPassword ? '隐藏密码' : '显示密码'"
              :title="showPassword ? '隐藏密码' : '显示密码'"
              class="auth-form__password-toggle"
              type="button"
              @click="showPassword = !showPassword"
            >
              <IconEyeOff v-if="showPassword" size="sm" />
              <IconEye v-else size="sm" />
            </button>
          </div>
        </label>

        <button :disabled="submitting" class="auth-form__submit" type="submit">
          <IconLoading v-if="submitting" size="sm" />
          <span>{{ submitting ? "登录中" : "登录" }}</span>
        </button>

        <p class="auth-form__footer">
          <RouterLink :to="activateLink">邀请码</RouterLink>
        </p>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
/**
 * 登录页。
 */
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { loginAndStoreSession } from "@/auth/session";
import { messageApi } from "@/composables/useMessage";
import { IconEye, IconEyeOff, IconLoading } from "@/components/icons";

const route = useRoute();
const router = useRouter();

const username = ref("");
const password = ref("");
const showPassword = ref(false);
const submitting = ref(false);

function normalizeRedirectTarget(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return "/tasks";
  }
  return value;
}

const redirectTarget = computed(() => normalizeRedirectTarget(route.query.redirect));
const redirectHint = computed(() => redirectTarget.value === "/tasks" ? "" : redirectTarget.value);
const activateLink = computed(() => ({
  path: "/activate",
  query: redirectHint.value ? { redirect: redirectHint.value } : undefined
}));

async function handleSubmit() {
  submitting.value = true;
  try {
    await loginAndStoreSession({
      username: username.value,
      password: password.value
    });
    await router.replace(redirectTarget.value);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "登录失败");
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.auth-screen {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--bg-base);
}

.auth-screen__panel {
  width: min(400px, 100%);
  display: grid;
  gap: 20px;
  padding: 28px;
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-subtle);
  background: var(--bg-surface);
  box-shadow: var(--shadow-lg);
}

.auth-screen__hero h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  text-align: center;
}

.auth-form {
  display: grid;
  gap: 12px;
}

.auth-form__field {
  display: grid;
  gap: 6px;
}

.auth-form__field-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.auth-form__field input {
  width: 100%;
  min-height: 44px;
  padding: 0 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-default);
  background: var(--bg-surface);
  color: var(--text-primary);
  font-size: 14px;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.auth-form__field input:focus {
  border-color: var(--accent-indigo);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.auth-form__field input::placeholder {
  color: var(--text-muted);
}

.auth-form__password-wrap {
  position: relative;
}

.auth-form__password-wrap input {
  padding-right: 48px;
}

.auth-form__password-toggle {
  position: absolute;
  top: 50%;
  right: 8px;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.auth-form__password-toggle:hover {
  background: var(--bg-muted);
  color: var(--text-primary);
}

.auth-form__submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 44px;
  border: 0;
  border-radius: var(--radius-md);
  background: var(--accent-indigo);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25);
  transition: transform 160ms ease, box-shadow 160ms ease;
}

.auth-form__submit:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(79, 70, 229, 0.3);
}

.auth-form__submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.auth-form__footer {
  margin: 0;
  color: var(--text-muted);
  text-align: center;
  font-size: 13px;
}

.auth-form__footer a {
  color: var(--accent-indigo);
  font-weight: 700;
}

.auth-form__footer a:hover {
  text-decoration: underline;
}

.auth-form__error {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: rgba(244, 63, 94, 0.08);
  color: var(--accent-rose);
  font-size: 13px;
}
</style>
