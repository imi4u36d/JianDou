<template>
  <section class="auth-screen">
    <div class="auth-screen__panel">
      <div class="auth-screen__hero">
        <h1>激活账号</h1>
      </div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label class="auth-form__field">
          <span class="auth-form__field-label">邀请码</span>
          <input v-model="code" autocomplete="off" placeholder="邀请码" type="text" />
        </label>
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
              autocomplete="new-password"
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
          <span>{{ submitting ? "激活中" : "激活" }}</span>
        </button>

        <p class="auth-form__footer">
          <RouterLink :to="loginLink">登录</RouterLink>
        </p>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
/**
 * 激活页。
 */
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { activateInviteAndStoreSession } from "@/auth/session";
import { messageApi } from "@/composables/useMessage";
import { IconEye, IconEyeOff, IconLoading } from "@/components/icons";

const route = useRoute();
const router = useRouter();

const code = ref(typeof route.query.code === "string" ? route.query.code : "");
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
const loginLink = computed(() => ({
  path: "/login",
  query: redirectTarget.value === "/tasks" ? undefined : { redirect: redirectTarget.value }
}));

async function handleSubmit() {
  submitting.value = true;
  try {
    await activateInviteAndStoreSession({
      code: code.value,
      username: username.value,
      password: password.value
    });
    await router.replace(redirectTarget.value);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "激活失败");
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
  background: linear-gradient(180deg, #f6fbff 0%, #ffffff 52%, #f4fbf7 100%);
}

.auth-screen__panel {
  width: min(410px, 100%);
  display: grid;
  gap: 20px;
  padding: 22px;
  border-radius: 22px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(255, 255, 255, 0.82);
  box-shadow:
    0 16px 38px rgba(99, 102, 241, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(40px) saturate(2.0);
}

.auth-screen__hero {
  padding: 0 2px;
  text-align: center;
}

.auth-screen__hero h1 {
  margin: 0;
  font-family: inherit;
  font-size: clamp(1.5rem, 4vw, 1.9rem);
  line-height: 1.12;
  letter-spacing: 0;
  color: var(--text-strong);
}

.auth-screen__hero p {
  margin: 16px 0 0;
  max-width: 28rem;
  color: var(--text-body);
  line-height: 1.8;
}

.auth-form {
  display: grid;
  gap: 10px;
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
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: rgba(255, 255, 255, 0.9);
  color: var(--text-strong);
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.auth-form__field input:focus {
  border-color: rgba(99, 102, 241, 0.5);
  box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.3);
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
  display: grid;
  place-items: center;
  width: 34px;
  min-height: 34px;
  padding: 0;
  border: 0;
  border-radius: 11px;
  background: rgba(238, 242, 255, 0.92);
  color: var(--text-body);
  line-height: 0;
  cursor: pointer;
}

.auth-form__password-toggle:hover {
  background: #e0e7ff;
  color: var(--accent-blue);
}

.auth-form__password-toggle :deep(svg) {
  width: 16px;
  height: 16px;
}

.auth-form__field input::placeholder {
  color: #9aa5ad;
}

.auth-form__error {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 111, 145, 0.18);
  background: rgba(255, 111, 145, 0.12);
  color: var(--accent-danger);
}

.auth-form__submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 48px;
  border: 0;
  border-radius: 14px;
  background: var(--bg-accent);
  color: #fff;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 12px 26px rgba(99, 102, 241, 0.18);
  transition:
    box-shadow 180ms ease,
    transform 180ms ease,
    opacity 180ms ease;
}

.auth-form__submit :deep(svg) {
  width: 16px;
  height: 16px;
}

.auth-form__submit:hover:not(:disabled),
.auth-form__submit:focus-visible {
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(99, 102, 241, 0.22);
}

.auth-form__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-form__footer {
  margin: 0;
  color: var(--text-muted);
  text-align: center;
}

.auth-form__footer a {
  color: var(--accent-cyan);
  font-weight: 800;
  text-decoration: none;
}

.auth-form__footer a:hover,
.auth-form__footer a:focus-visible {
  color: var(--accent-blue);
  text-decoration: underline;
  text-underline-offset: 0.18em;
}

@media (max-width: 860px) {
  .auth-screen {
    padding: 16px;
  }

  .auth-screen__panel {
    gap: 16px;
    padding: 18px;
  }

  .auth-screen__hero {
    padding: 4px 2px;
  }
}
</style>
