<template>
  <section class="auth-screen">
    <div class="auth-screen__glow auth-screen__glow-left" aria-hidden="true"></div>
    <div class="auth-screen__glow auth-screen__glow-right" aria-hidden="true"></div>

    <div class="auth-screen__panel">
      <div class="auth-screen__hero">
        <p class="auth-screen__eyebrow">Session Access</p>
        <h1>登录后进入煎豆工作台</h1>
        <p>
          当前版本已切换为邀请制账号体系。工作台和管理端都依赖服务端 Session，不再允许匿名进入。
        </p>
      </div>

      <form class="auth-form" @submit.prevent="handleSubmit">
        <label class="auth-form__field">
          <span>用户名</span>
          <input v-model="username" autocomplete="username" placeholder="请输入用户名" type="text" />
        </label>
        <label class="auth-form__field">
          <span>密码</span>
          <input v-model="password" autocomplete="current-password" placeholder="请输入密码" type="password" />
        </label>

        <div v-if="redirectHint" class="auth-form__hint">
          登录成功后会返回到 `{{ redirectHint }}`
        </div>
        <div v-if="errorMessage" class="auth-form__error">
          {{ errorMessage }}
        </div>

        <button :disabled="submitting" class="auth-form__submit" type="submit">
          {{ submitting ? "登录中..." : "登录" }}
        </button>

        <p class="auth-form__footer">
          还没有账号？
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

const route = useRoute();
const router = useRouter();

const username = ref("");
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
const redirectHint = computed(() => redirectTarget.value === "/tasks" ? "" : redirectTarget.value);
const activateLink = computed(() => ({
  path: "/activate",
  query: redirectHint.value ? { redirect: redirectHint.value } : undefined
}));

async function handleSubmit() {
  submitting.value = true;
  errorMessage.value = "";
  try {
    await loginAndStoreSession({
      username: username.value,
      password: password.value
    });
    await router.replace(redirectTarget.value);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "登录失败";
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
    radial-gradient(circle at top left, rgba(255, 196, 86, 0.16), transparent 24%),
    radial-gradient(circle at 84% 18%, rgba(86, 160, 255, 0.18), transparent 24%),
    linear-gradient(135deg, #08101f 0%, #101725 48%, #1a1013 100%);
}

.auth-screen__glow {
  position: absolute;
  border-radius: 999px;
  filter: blur(80px);
  opacity: 0.4;
}

.auth-screen__glow-left {
  top: -40px;
  left: -80px;
  width: 260px;
  height: 260px;
  background: rgba(255, 177, 93, 0.26);
}

.auth-screen__glow-right {
  right: -70px;
  bottom: -60px;
  width: 280px;
  height: 280px;
  background: rgba(88, 176, 255, 0.22);
}

.auth-screen__panel {
  position: relative;
  z-index: 1;
  width: min(980px, 100%);
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 420px);
  gap: 28px;
  padding: 28px;
  border-radius: 32px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(9, 14, 24, 0.82);
  box-shadow:
    0 30px 80px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(26px);
}

.auth-screen__hero {
  padding: 18px 8px;
}

.auth-screen__eyebrow {
  margin: 0 0 12px;
  color: rgba(255, 214, 153, 0.84);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.auth-screen__hero h1 {
  margin: 0;
  font-family: "Sora", "Inter", sans-serif;
  font-size: clamp(2rem, 5vw, 3.2rem);
  line-height: 1.05;
  letter-spacing: -0.06em;
  color: #f8fbff;
}

.auth-screen__hero p {
  margin: 16px 0 0;
  max-width: 30rem;
  color: rgba(236, 242, 255, 0.72);
  line-height: 1.8;
}

.auth-form {
  display: grid;
  gap: 16px;
  padding: 22px;
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

.auth-form__hint,
.auth-form__error,
.auth-form__footer {
  font-size: 0.88rem;
}

.auth-form__hint {
  color: rgba(255, 222, 171, 0.8);
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
  background: linear-gradient(135deg, #ffb25a, #4eb0ff);
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
  color: #ffe0ab;
}

@media (max-width: 860px) {
  .auth-screen__panel {
    grid-template-columns: 1fr;
  }
}
</style>
