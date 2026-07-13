<template>
  <AuthStandaloneForm
    title="欢迎回来"
    subtitle="继续你的内容创作之旅"
    :username="username"
    :password="password"
    :submitting="submitting"
    submit-label="登录"
    submitting-label="登录中"
    footer-label="邀请码"
    :footer-to="activateLink"
    @update:username="username = $event"
    @update:password="password = $event"
    @submit="handleSubmit"
  />
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { normalizeAuthRedirectTarget } from "@/auth/redirect";
import { loginAndStoreSession } from "@/auth/session";
import AuthStandaloneForm from "@/components/auth/AuthStandaloneForm.vue";
import { messageApi } from "@/composables/useMessage";

const route = useRoute();
const router = useRouter();
const username = ref("");
const password = ref("");
const submitting = ref(false);
const redirectTarget = computed(() => normalizeAuthRedirectTarget(route.query.redirect, "/image-tasks"));
const activateLink = computed(() => ({
  path: "/activate",
  query: redirectTarget.value === "/image-tasks" ? undefined : { redirect: redirectTarget.value },
}));

async function handleSubmit() {
  submitting.value = true;
  try {
    await loginAndStoreSession({ username: username.value, password: password.value });
    await router.replace(redirectTarget.value);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "登录失败");
  } finally {
    submitting.value = false;
  }
}
</script>
