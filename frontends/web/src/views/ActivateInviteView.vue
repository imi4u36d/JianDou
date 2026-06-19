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
          <span class="auth-form__field-label">显示名</span>
          <input v-model="displayName" autocomplete="nickname" placeholder="显示名" type="text" />
        </label>
        <label class="auth-form__field">
          <span class="auth-form__field-label">密码</span>
          <input v-model="password" autocomplete="new-password" placeholder="密码" type="password" />
        </label>

        <button :disabled="submitting" class="auth-form__submit" type="submit">
          {{ submitting ? "激活中..." : "激活并登录" }}
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

const route = useRoute();
const router = useRouter();

const code = ref(typeof route.query.code === "string" ? route.query.code : "");
const username = ref("");
const displayName = ref("");
const password = ref("");
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
      displayName: displayName.value,
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
  background:
    radial-gradient(circle at 18% 12%, rgba(139, 212, 80, 0.18), transparent 28%),
    radial-gradient(circle at 86% 10%, rgba(27, 124, 255, 0.12), transparent 30%),
    linear-gradient(180deg, #f6fbff 0%, #ffffff 52%, #f4fbf7 100%);
}

.auth-screen__panel {
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
  max-width: 28rem;
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
}
</style>
