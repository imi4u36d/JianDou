<template>
  <section class="auth-screen">
    <div class="auth-screen__panel">
      <div class="auth-screen__hero">
        <p class="auth-screen__eyebrow">Invite Activation</p>
        <h1>使用邀请码创建账号</h1>
        <p>
          邀请码只能使用一次。激活成功后会立即建立 Session，并直接进入工作台。
        </p>
      </div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label class="auth-form__field">
          <span>邀请码</span>
          <input v-model="code" autocomplete="off" placeholder="例如 ABCD23EFGH89" type="text" />
        </label>
        <label class="auth-form__field">
          <span>用户名</span>
          <input v-model="username" autocomplete="username" placeholder="3-32 位英文数字组合" type="text" />
        </label>
        <label class="auth-form__field">
          <span>显示名</span>
          <input v-model="displayName" autocomplete="nickname" placeholder="用于界面展示" type="text" />
        </label>
        <label class="auth-form__field">
          <span>密码</span>
          <input v-model="password" autocomplete="new-password" placeholder="至少 8 位" type="password" />
        </label>

        <div v-if="errorMessage" class="auth-form__error">
          {{ errorMessage }}
        </div>

        <button :disabled="submitting" class="auth-form__submit" type="submit">
          {{ submitting ? "激活中..." : "激活并登录" }}
        </button>

        <p class="auth-form__footer">
          已有账号？
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

const route = useRoute();
const router = useRouter();

const code = ref(typeof route.query.code === "string" ? route.query.code : "");
const username = ref("");
const displayName = ref("");
const password = ref("");
const submitting = ref(false);
const errorMessage = ref("");

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
  errorMessage.value = "";
  try {
    await activateInviteAndStoreSession({
      code: code.value,
      username: username.value,
      displayName: displayName.value,
      password: password.value
    });
    await router.replace(redirectTarget.value);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "激活失败";
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
    radial-gradient(circle at top right, rgba(103, 214, 255, 0.18), transparent 28%),
    radial-gradient(circle at bottom left, rgba(255, 194, 125, 0.16), transparent 28%),
    linear-gradient(135deg, #0b121d 0%, #121321 50%, #1b1414 100%);
}

.auth-screen__panel {
  width: min(960px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(320px, 440px);
  gap: 28px;
  padding: 30px;
  border-radius: 32px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(11, 16, 24, 0.82);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.42);
  backdrop-filter: blur(22px);
}

.auth-screen__hero {
  padding: 12px 8px;
}

.auth-screen__eyebrow {
  margin: 0 0 12px;
  color: rgba(150, 219, 255, 0.78);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.auth-screen__hero h1 {
  margin: 0;
  font-family: "Sora", "Inter", sans-serif;
  font-size: clamp(2rem, 4.8vw, 3rem);
  line-height: 1.08;
  letter-spacing: -0.05em;
}

.auth-screen__hero p {
  margin: 16px 0 0;
  max-width: 28rem;
  color: rgba(232, 240, 255, 0.72);
  line-height: 1.8;
}

.auth-form {
  display: grid;
  gap: 15px;
  padding: 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.auth-form__field {
  display: grid;
  gap: 8px;
}

.auth-form__field span {
  color: rgba(255, 255, 255, 0.76);
  font-size: 0.88rem;
}

.auth-form__field input {
  width: 100%;
  min-height: 48px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(4, 7, 13, 0.72);
  color: #fff;
}

.auth-form__field input::placeholder {
  color: rgba(255, 255, 255, 0.34);
}

.auth-form__error {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 111, 145, 0.18);
  background: rgba(255, 111, 145, 0.12);
  color: #ffd3de;
}

.auth-form__submit {
  min-height: 48px;
  border: 0;
  border-radius: 16px;
  background: linear-gradient(135deg, #6ad6ff, #f7b768);
  color: #07111c;
  font-weight: 800;
  cursor: pointer;
}

.auth-form__submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.auth-form__footer {
  margin: 0;
  color: rgba(255, 255, 255, 0.62);
}

.auth-form__footer a {
  color: #a8e6ff;
}

@media (max-width: 860px) {
  .auth-screen__panel {
    grid-template-columns: 1fr;
  }
}
</style>
