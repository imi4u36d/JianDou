<template>
  <Teleport to="body">
    <div v-if="modal.open" class="auth-dialog-backdrop" role="dialog" aria-modal="true" aria-labelledby="auth-dialog-title" @click.self="handleClose">
      <section class="auth-dialog">
        <header class="auth-dialog__head">
          <div>
            <p class="auth-dialog__eyebrow">JianDou Account</p>
            <h2 id="auth-dialog-title">{{ modal.title }}</h2>
            <p>{{ modal.message }}</p>
          </div>
          <button class="auth-dialog__close" type="button" aria-label="关闭登录弹窗" @click="handleClose">×</button>
        </header>

        <div class="auth-dialog__tabs" role="tablist" aria-label="账号操作">
          <button type="button" :class="{ 'auth-dialog__tab-active': modal.mode === 'login' }" @click="switchAuthModalMode('login')">
            登录
          </button>
          <button type="button" :class="{ 'auth-dialog__tab-active': modal.mode === 'register' }" @click="switchAuthModalMode('register')">
            邀请码注册
          </button>
        </div>

        <form v-if="modal.mode === 'login'" class="auth-dialog__form" @submit.prevent="handleLogin">
          <label class="auth-dialog__field">
            <span>用户名</span>
            <input v-model.trim="loginForm.username" autocomplete="username" placeholder="用户名" type="text" />
          </label>
          <label class="auth-dialog__field">
            <span>密码</span>
            <input v-model="loginForm.password" autocomplete="current-password" placeholder="密码" type="password" />
          </label>
          <button class="auth-dialog__submit" type="submit" :disabled="submitting">
            {{ submitting ? "登录中..." : "登录并继续" }}
          </button>
        </form>

        <form v-else class="auth-dialog__form" @submit.prevent="handleRegister">
          <label class="auth-dialog__field">
            <span>邀请码</span>
            <input v-model.trim="registerForm.code" autocomplete="off" placeholder="邀请码" type="text" />
          </label>
          <label class="auth-dialog__field">
            <span>用户名</span>
            <input v-model.trim="registerForm.username" autocomplete="username" placeholder="用户名" type="text" />
          </label>
          <label class="auth-dialog__field">
            <span>显示名</span>
            <input v-model.trim="registerForm.displayName" autocomplete="nickname" placeholder="显示名" type="text" />
          </label>
          <label class="auth-dialog__field">
            <span>密码</span>
            <input v-model="registerForm.password" autocomplete="new-password" placeholder="至少 8 位密码" type="password" />
          </label>
          <button class="auth-dialog__submit" type="submit" :disabled="submitting">
            {{ submitting ? "注册中..." : "注册并继续" }}
          </button>
        </form>
      </section>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 全局登录/邀请码注册弹窗。
 */
import { reactive, ref, watch } from "vue";
import { activateInviteAndStoreSession, loginAndStoreSession } from "@/auth/session";
import { messageApi } from "@/composables/useMessage";
import { closeAuthModal, switchAuthModalMode, useAuthModalState } from "@/auth/modal";

const modal = useAuthModalState();
const submitting = ref(false);

const loginForm = reactive({
  username: "",
  password: "",
});

const registerForm = reactive({
  code: "",
  username: "",
  displayName: "",
  password: "",
});

function handleClose() {
  if (submitting.value) {
    return;
  }
  closeAuthModal(false);
}

async function handleLogin() {
  submitting.value = true;
  try {
    await loginAndStoreSession({
      username: loginForm.username,
      password: loginForm.password,
    });
    closeAuthModal(true);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "登录失败");
  } finally {
    submitting.value = false;
  }
}

async function handleRegister() {
  submitting.value = true;
  try {
    await activateInviteAndStoreSession({
      code: registerForm.code,
      username: registerForm.username,
      displayName: registerForm.displayName,
      password: registerForm.password,
    });
    closeAuthModal(true);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "注册失败");
  } finally {
    submitting.value = false;
  }
}

watch(
  () => [modal.open, modal.mode],
  () => {
    // mode switch — no inline error state to clear anymore
  },
);
</script>

<style scoped>
.auth-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  padding: 18px;
  background: rgba(15, 20, 25, 0.42);
  backdrop-filter: blur(14px);
}

.auth-dialog {
  width: min(460px, 100%);
  display: grid;
  gap: 18px;
  padding: 22px;
  border-radius: 18px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  background: #fff;
  box-shadow: 0 24px 70px rgba(15, 20, 25, 0.2);
}

.auth-dialog__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.auth-dialog__eyebrow,
.auth-dialog__head h2,
.auth-dialog__head p {
  margin: 0;
}

.auth-dialog__eyebrow {
  margin-bottom: 7px;
  color: var(--accent-cyan);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.auth-dialog__head h2 {
  color: var(--text-strong);
  font-size: 1.32rem;
  font-weight: 850;
}

.auth-dialog__head p {
  margin-top: 8px;
  color: var(--text-body);
  font-size: 0.9rem;
  line-height: 1.65;
}

.auth-dialog__close {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  border: 0;
  border-radius: 10px;
  background: #f1f4f6;
  color: var(--text-body);
  font-size: 1.3rem;
  line-height: 1;
  cursor: pointer;
}

.auth-dialog__tabs {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  padding: 6px;
  border-radius: 14px;
  background: #f3f6f8;
}

.auth-dialog__tabs button {
  min-height: 38px;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-body);
  font-size: 0.88rem;
  font-weight: 800;
  cursor: pointer;
}

.auth-dialog__tabs .auth-dialog__tab-active {
  background: #fff;
  color: var(--text-strong);
  box-shadow: 0 4px 14px rgba(15, 20, 25, 0.08);
}

.auth-dialog__form {
  display: grid;
  gap: 13px;
}

.auth-dialog__field {
  display: grid;
  gap: 7px;
}

.auth-dialog__field span {
  color: var(--text-body);
  font-size: 0.84rem;
  font-weight: 700;
}

.auth-dialog__field input {
  width: 100%;
  min-height: 46px;
  padding: 0 13px;
  border-radius: 12px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  background: #fff;
  color: var(--text-strong);
}

.auth-dialog__submit {
  min-height: 46px;
  border: 0;
  border-radius: 13px;
  background: var(--bg-accent);
  color: #fff;
  font-weight: 850;
  cursor: pointer;
}

.auth-dialog__submit:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}

@media (max-width: 520px) {
  .auth-dialog {
    padding: 18px;
  }
}
</style>
