<template>
  <div class="page-shell forbidden-view">
    <el-card class="surface-card forbidden-view__card" shadow="never">
      <p class="forbidden-view__eyebrow">403 Forbidden</p>
      <h1>当前账号没有管理端权限</h1>
      <p>后台管理系统只允许管理员账号进入。请使用管理员账户重新登录。</p>
      <el-button type="primary" @click="goLogin">返回登录页</el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { logoutAndClearSession } from "@/auth/session";

const router = useRouter();

async function goLogin() {
  await logoutAndClearSession();
  await router.replace("/login");
}
</script>

<style scoped>
.forbidden-view {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 20px;
}

.forbidden-view__card {
  width: min(560px, 100%);
  padding: 20px;
  border-radius: 28px;
  text-align: center;
}

.forbidden-view__eyebrow {
  margin: 0 0 12px;
  color: var(--jd-text-soft);
  font-size: 0.78rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.forbidden-view__card h1 {
  margin: 0;
  font-family: "Space Grotesk", sans-serif;
}

.forbidden-view__card p {
  color: var(--jd-text-soft);
}
</style>
