<template>
  <Teleport to="body">
    <div
      v-if="modal.open"
      class="auth-dialog-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-dialog-title"
      @click.self="handleClose"
      @keydown.esc.stop.prevent="handleClose"
    >
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
          <button
            type="button"
            role="tab"
            :aria-selected="modal.mode === 'login'"
            :tabindex="modal.mode === 'login' ? 0 : -1"
            :class="{ 'auth-dialog__tab-active': modal.mode === 'login' }"
            @click="switchAuthModalMode('login')"
          >
            登录
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="modal.mode === 'register'"
            :tabindex="modal.mode === 'register' ? 0 : -1"
            :class="{ 'auth-dialog__tab-active': modal.mode === 'register' }"
            @click="switchAuthModalMode('register')"
          >
            激活
          </button>
        </div>

        <form v-if="modal.mode === 'login'" class="auth-dialog__form" @submit.prevent="handleLogin">
          <label class="auth-dialog__field">
            <span class="auth-dialog__field-label">用户名</span>
            <input
              ref="loginUsernameRef"
              v-model.trim="loginForm.username"
              autocomplete="username"
              placeholder="用户名"
              type="text"
            />
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
            <input
              ref="registerCodeRef"
              v-model.trim="registerForm.code"
              autocomplete="off"
              placeholder="邀请码"
              type="text"
            />
          </label>
          <label class="auth-dialog__field">
            <span class="auth-dialog__field-label">用户名</span>
            <input v-model.trim="registerForm.username" autocomplete="username" placeholder="用户名" type="text" />
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
import { switchAuthModalMode } from "@/auth/modal";
import { IconClose, IconEye, IconEyeOff, IconLoading } from "@/components/icons";
import { useAuthDialog } from "./useAuthDialog";

const {
  modal,
  submitting,
  showLoginPassword,
  showRegisterPassword,
  loginUsernameRef,
  registerCodeRef,
  loginForm,
  registerForm,
  handleClose,
  handleLogin,
  handleRegister,
} = useAuthDialog();
</script>

<style scoped src="./auth-dialog.css"></style>
