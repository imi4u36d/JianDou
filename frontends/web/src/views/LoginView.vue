<template>
  <section class="auth-screen">
    <div class="auth-screen__glow auth-screen__glow-left" aria-hidden="true"></div>
    <div class="auth-screen__glow auth-screen__glow-right" aria-hidden="true"></div>

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
              {{ showPassword ? "隐" : "显" }}
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
  background:
    radial-gradient(circle at 18% 12%, rgba(139, 212, 80, 0.18), transparent 28%),
    radial-gradient(circle at 86% 10%, rgba(27, 124, 255, 0.12), transparent 30%),
    linear-gradient(180deg, #f6fbff 0%, #ffffff 52%, #f4fbf7 100%);
}

.auth-screen__glow {
  display: none;
}

.auth-screen__panel {
  position: relative;
  z-index: 1;
  width: min(430px, 100%);
  display: grid;
  gap: 20px;
  padding: 28px;
  border-radius: 20px;
  border: 1px solid rgba(0, 169, 187, 0.1);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 42px rgba(27, 124, 255, 0.08);
  backdrop-filter: blur(18px);
}

.auth-screen__hero {
  padding: 0 2px;
  text-align: center;
}

.auth-screen__hero h1 {
  margin: 0;
  font-family: inherit;
  font-size: clamp(1.78rem, 4.4vw, 2.35rem);
  line-height: 1.12;
  letter-spacing: 0;
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
  gap: 14px;
  padding: 0;
  border-radius: 0;
  background: transparent;
  border: 0;
}

.auth-form__field {
  display: grid;
  gap: 8px;
}

.auth-form__field-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.auth-form__field span:not(.auth-form__field-label) {
  color: var(--text-body);
  font-size: 0.88rem;
}

.auth-form__field input {
  width: 100%;
  min-height: 48px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid rgba(0, 169, 187, 0.12);
  background: #fff;
  color: var(--text-strong);
}

.auth-form__password-wrap {
  position: relative;
}

.auth-form__password-wrap input {
  padding-right: 54px;
}

.auth-form__password-toggle {
  position: absolute;
  top: 50%;
  right: 10px;
  transform: translateY(-50%);
  width: 34px;
  min-height: 34px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: #effcff;
  color: var(--text-body);
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.auth-form__password-toggle:hover {
  background: #edf5ff;
  color: var(--accent-blue);
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
  border-radius: 14px;
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
    gap: 18px;
    padding: 22px;
  }

  .auth-screen__hero {
    padding: 4px 2px;
  }

  .auth-screen__hero h1 {
    max-width: none;
    font-size: clamp(1.78rem, 9vw, 2.35rem);
  }
}
</style>
