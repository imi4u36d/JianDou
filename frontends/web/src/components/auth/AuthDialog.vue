<template>
  <Teleport to="body">
    <div v-if="modal.open" class="auth-dialog-backdrop" role="dialog" aria-modal="true" aria-labelledby="auth-dialog-title" @click.self="handleClose">
      <section class="auth-dialog">
        <header class="auth-dialog__head">
          <div>
            <h2 id="auth-dialog-title">{{ modal.title }}</h2>
            <p v-if="modal.message">{{ modal.message }}</p>
          </div>
          <button class="auth-dialog__close" type="button" aria-label="关闭登录弹窗" @click="handleClose">
            <IconClose size="sm" />
          </button>
        </header>

        <div class="auth-dialog__tabs" role="tablist" aria-label="账号操作">
          <button type="button" :class="{ 'auth-dialog__tab-active': modal.mode === 'login' }" @click="switchAuthModalMode('login')">
            登录
          </button>
          <button type="button" :class="{ 'auth-dialog__tab-active': modal.mode === 'register' }" @click="switchAuthModalMode('register')">
            激活
          </button>
        </div>

        <form v-if="modal.mode === 'login'" class="auth-dialog__form" @submit.prevent="handleLogin">
          <label class="auth-dialog__field">
            <span class="auth-dialog__field-label">用户名</span>
            <input v-model.trim="loginForm.username" autocomplete="username" placeholder="用户名" type="text" />
          </label>
          <label class="auth-dialog__field">
            <span class="auth-dialog__field-label">密码</span>
            <div class="auth-dialog__password-wrap">
              <input
                v-model="loginForm.password"
                :type="showLoginPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="密码"
              />
              <button
                class="auth-dialog__password-toggle"
                type="button"
                :aria-label="showLoginPassword ? '隐藏密码' : '显示密码'"
                :title="showLoginPassword ? '隐藏密码' : '显示密码'"
                @click="showLoginPassword = !showLoginPassword"
              >
                <IconEyeOff v-if="showLoginPassword" size="sm" />
                <IconEye v-else size="sm" />
              </button>
            </div>
          </label>
          <button class="auth-dialog__submit" type="submit" :disabled="submitting">
            <IconLoading v-if="submitting" size="sm" />
            <span>{{ submitting ? "登录中" : "登录" }}</span>
          </button>
        </form>

        <form v-else class="auth-dialog__form" @submit.prevent="handleRegister">
          <label class="auth-dialog__field">
            <span class="auth-dialog__field-label">邀请码</span>
            <input v-model.trim="registerForm.code" autocomplete="off" placeholder="邀请码" type="text" />
          </label>
          <label class="auth-dialog__field">
            <span class="auth-dialog__field-label">用户名</span>
            <input v-model.trim="registerForm.username" autocomplete="username" placeholder="用户名" type="text" />
          </label>
          <label class="auth-dialog__field">
            <span class="auth-dialog__field-label">显示名</span>
            <input v-model.trim="registerForm.displayName" autocomplete="nickname" placeholder="显示名" type="text" />
          </label>
          <label class="auth-dialog__field">
            <span class="auth-dialog__field-label">密码</span>
            <div class="auth-dialog__password-wrap">
              <input
                v-model="registerForm.password"
                :type="showRegisterPassword ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="密码"
              />
              <button
                class="auth-dialog__password-toggle"
                type="button"
                :aria-label="showRegisterPassword ? '隐藏密码' : '显示密码'"
                :title="showRegisterPassword ? '隐藏密码' : '显示密码'"
                @click="showRegisterPassword = !showRegisterPassword"
              >
                <IconEyeOff v-if="showRegisterPassword" size="sm" />
                <IconEye v-else size="sm" />
              </button>
            </div>
          </label>
          <button class="auth-dialog__submit" type="submit" :disabled="submitting">
            <IconLoading v-if="submitting" size="sm" />
            <span>{{ submitting ? "激活中" : "激活" }}</span>
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
import { IconClose, IconEye, IconEyeOff, IconLoading } from "@/components/icons";

const modal = useAuthModalState();
const submitting = ref(false);
const showLoginPassword = ref(false);
const showRegisterPassword = ref(false);

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
    showLoginPassword.value = false;
    showRegisterPassword.value = false;
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
  max-height: min(620px, calc(100dvh - 36px));
  overflow: auto;
  display: grid;
  gap: 16px;
  padding: 20px;
  border-radius: 22px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 22px 56px rgba(15, 20, 25, 0.14);
  backdrop-filter: blur(20px);
}

.auth-dialog__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.auth-dialog__head h2,
.auth-dialog__head p {
  margin: 0;
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
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  border: 0;
  border-radius: 11px;
  background: #f1f4f6;
  color: var(--text-body);
  line-height: 0;
  cursor: pointer;
}

.auth-dialog__close :deep(svg) {
  width: 16px;
  height: 16px;
}

.auth-dialog__close:hover,
.auth-dialog__close:focus-visible {
  background: #fff;
  color: var(--accent-blue);
  box-shadow: 0 8px 18px rgba(15, 20, 25, 0.08);
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
  color: var(--accent-blue);
  box-shadow: 0 4px 14px rgba(15, 20, 25, 0.08);
}

.auth-dialog__form {
  display: grid;
  gap: 13px;
}

.auth-dialog__field {
  display: grid;
  gap: 0;
}

.auth-dialog__field-label {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

.auth-dialog__field span:not(.auth-dialog__field-label) {
  color: var(--text-body);
  font-size: 0.84rem;
  font-weight: 700;
}

.auth-dialog__field input {
  width: 100%;
  min-height: 48px;
  padding: 0 13px;
  border-radius: 14px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  background: rgba(255, 255, 255, 0.92);
  color: var(--text-strong);
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.auth-dialog__field input:focus {
  border-color: rgba(0, 169, 187, 0.42);
  box-shadow:
    0 0 0 3px rgba(0, 169, 187, 0.1),
    0 10px 24px rgba(27, 124, 255, 0.06);
}

.auth-dialog__password-wrap {
  position: relative;
}

.auth-dialog__password-wrap input {
  padding-right: 54px;
}

.auth-dialog__password-toggle {
  position: absolute;
  top: 50%;
  right: 9px;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 34px;
  min-height: 34px;
  padding: 0;
  border: 0;
  border-radius: 11px;
  background: rgba(239, 252, 255, 0.92);
  color: var(--text-body);
  line-height: 0;
  cursor: pointer;
}

.auth-dialog__password-toggle:hover {
  background: #edf5ff;
  color: var(--accent-blue);
}

.auth-dialog__password-toggle :deep(svg) {
  width: 16px;
  height: 16px;
}

.auth-dialog__submit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 48px;
  border: 0;
  border-radius: 14px;
  background: var(--bg-accent);
  color: #fff;
  font-weight: 850;
  cursor: pointer;
  box-shadow: 0 12px 26px rgba(27, 124, 255, 0.18);
  transition:
    box-shadow 180ms ease,
    transform 180ms ease,
    opacity 180ms ease;
}

.auth-dialog__submit :deep(svg) {
  width: 16px;
  height: 16px;
}

.auth-dialog__submit:hover:not(:disabled),
.auth-dialog__submit:focus-visible {
  transform: translateY(-1px);
  box-shadow: 0 14px 30px rgba(27, 124, 255, 0.22);
}

.auth-dialog__submit:disabled {
  opacity: 0.62;
  cursor: not-allowed;
}

@media (max-width: 520px) {
  .auth-dialog-backdrop {
    align-items: end;
    padding: 14px;
  }

  .auth-dialog {
    width: 100%;
    max-height: min(680px, calc(100dvh - 72px));
    padding: 20px 16px 16px;
    border-radius: 22px;
  }

  .auth-dialog::before {
    content: "";
    justify-self: center;
    width: 38px;
    height: 4px;
    margin: -9px 0 2px;
    border-radius: 999px;
    background: rgba(15, 20, 25, 0.16);
  }

  .auth-dialog__head h2 {
    font-size: 1.12rem;
  }
}
</style>
