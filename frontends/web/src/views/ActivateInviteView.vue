<template>
  <section class="auth-screen">
    <div class="auth-screen__panel">
      <div class="auth-screen__hero">
        <p class="auth-screen__eyebrow">Invite Activation</p>
        <h1>使用邀请码创建账号</h1>
      </div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label class="auth-form__field">
          <span>邀请码</span>
          <input v-model="code" autocomplete="off" placeholder="邀请码" type="text" />
        </label>
        <label class="auth-form__field">
          <span>用户名</span>
          <input v-model="username" autocomplete="username" placeholder="用户名" type="text" />
        </label>
        <label class="auth-form__field">
          <span>显示名</span>
          <input v-model="displayName" autocomplete="nickname" placeholder="显示名" type="text" />
        </label>
        <label class="auth-form__field">
          <span>密码</span>
          <input v-model="password" autocomplete="new-password" placeholder="密码" type="password" />
        </label>

        <button :disabled="submitting" class="auth-form__submit" type="submit">
          {{ submitting ? "激活中..." : "激活并登录" }}
        </button>

        <p class="auth-form__footer">
          <RouterLink :to="loginLink">返回登录</RouterLink>
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
  background: var(--bg-base);
}

.auth-screen__panel {
  width: min(960px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 440px);
  gap: 28px;
  padding: 30px;
  border-radius: 28px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  background: #fff;
  box-shadow: var(--shadow-panel);
}

.auth-screen__hero {
  padding: 12px 8px;
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
  font-size: clamp(2rem, 4.8vw, 3rem);
  line-height: 1.08;
  letter-spacing: -0.05em;
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
  gap: 15px;
  padding: 24px;
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
