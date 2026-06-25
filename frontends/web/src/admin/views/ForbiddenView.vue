<template>
  <div class="page-shell forbidden-view">
    <el-card class="surface-card forbidden-view__card" shadow="never">
      <h1>没有管理权限</h1>
      <el-button type="primary" @click="goLogin">重新登录</el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { logoutAndClearSession } from "@/auth/session";

const router = useRouter();

async function goLogin() {
  await logoutAndClearSession();
  await router.replace("/admin/login");
}
</script>

<style scoped>
.forbidden-view {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 20px;
  background: var(--jd-bg);
}

.forbidden-view__card {
  width: min(430px, 100%);
  padding: 28px;
  border-radius: var(--jd-radius-card);
  text-align: center;
}

.forbidden-view__card h1 {
  margin: 0;
  font-family: inherit;
  font-size: clamp(1.6rem, 5vw, 2.2rem);
}
</style>
