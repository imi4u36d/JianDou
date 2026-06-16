<template>
  <section class="auth-screen">
    <div class="auth-screen__glow auth-screen__glow-left" aria-hidden="true"></div>
    <div class="auth-screen__glow auth-screen__glow-right" aria-hidden="true"></div>

    <div class="auth-screen__panel">
      <div class="auth-screen__hero">
        <p class="auth-screen__eyebrow">把灵感煎成镜头</p>
        <h1>登录后进入煎豆工作台</h1>
      </div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label class="auth-form__field">
          <span>用户名</span>
          <input v-model="username" autocomplete="username" placeholder="用户名" type="text" />
        </label>
        <label class="auth-form__field">
          <span>密码</span>
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
              {{ showPassword ? "隐藏" : "显示" }}
            </button>
          </div>
        </label>

        <div v-if="redirectHint" class="auth-form__hint">
          登录成功后会返回到 `{{ redirectHint }}`
        </div>

        <button :disabled="submitting" class="auth-form__submit" type="submit">
          {{ submitting ? "登录中..." : "登录" }}
        </button>

        <p class="auth-form__footer">
          <RouterLink :to="activateLink">使用邀请码激活</RouterLink>
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
  position: relative;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  overflow: hidden;
  background: var(--bg-base);
}

.auth-screen__glow {
  display: none;
}

.auth-screen__panel {
  position: relative;
  z-index: 1;
  width: min(980px, 100%);
  display: grid;
  grid-template-columns: minmax(360px, 0.95fr) minmax(320px, 420px);
  gap: 28px;
  padding: 28px;
  border-radius: 28px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  background: #fff;
  box-shadow: var(--shadow-panel);
}

.auth-screen__hero {
  padding: 18px 8px;
}

.auth-screen__eyebrow {
  margin: 0 0 12px;
  color: var(--accent-cyan);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.auth-screen__hero h1 {
  margin: 0;
  font-family: inherit;
  max-width: 10ch;
  font-size: clamp(2.25rem, 4.4vw, 3.55rem);
  line-height: 1.05;
  letter-spacing: -0.06em;
  color: var(--text-strong);
}

.auth-screen__hero p {
  margin: 16px 0 0;
  max-width: 30rem;
  color: var(--text-body);
  line-height: 1.8;
}

.auth-form {
  display: grid;
  gap: 16px;
  padding: 22px;
  border-radius: 24px;
  background: #f7f9fa;
  border: 1px solid rgba(15, 20, 25, 0.06);
}

.auth-form__field {
  display: grid;
  gap: 8px;
}

.auth-form__field span {
  color: var(--text-body);
  font-size: 0.88rem;
}

.auth-form__field input {
  width: 100%;
  min-height: 48px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  background: #fff;
  color: var(--text-strong);
}

.auth-form__password-wrap {
  position: relative;
}

.auth-form__password-wrap input {
  padding-right: 72px;
}

.auth-form__password-toggle {
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
  min-width: 48px;
  padding: 6px 10px;
  border: 0;
  border-radius: 10px;
  background: #eef2f4;
  color: var(--text-body);
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.auth-form__password-toggle:hover {
  background: #e3e8eb;
}

.auth-form__field input::placeholder {
  color: #9aa5ad;
}

.auth-form__hint,
.auth-form__error,
.auth-form__footer {
  font-size: 0.88rem;
}

.auth-form__hint {
  color: var(--text-body);
}

.auth-form__error {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 111, 145, 0.18);
  background: rgba(255, 111, 145, 0.12);
  color: var(--accent-danger);
}

.auth-form__submit {
  min-height: 48px;
  border: 0;
  border-radius: 16px;
  background: var(--bg-accent);
  color: #fff;
  font-weight: 800;
  cursor: pointer;
}

.auth-form__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-form__footer {
  margin: 0;
  color: var(--text-muted);
}

.auth-form__footer a {
  color: var(--accent-cyan);
}

@media (max-width: 860px) {
  .auth-screen__panel {
    grid-template-columns: 1fr;
  }
}
</style>
