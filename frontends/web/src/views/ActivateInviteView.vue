<template>
  <AuthStandaloneForm
    title="激活账号"
    subtitle="创建你的煎豆账号，立即开始创作"
    show-code
    password-autocomplete="new-password"
    :code="code"
    :username="username"
    :password="password"
    :submitting="submitting"
    submit-label="激活"
    submitting-label="激活中"
    footer-label="登录"
    :footer-to="loginLink"
    @update:code="code = $event"
    @update:username="username = $event"
    @update:password="password = $event"
    @submit="handleSubmit"
  />
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { normalizeAuthRedirectTarget } from "@/auth/redirect";
import { activateInviteAndStoreSession } from "@/auth/session";
import AuthStandaloneForm from "@/components/auth/AuthStandaloneForm.vue";
import { messageApi } from "@/composables/useMessage";

const route = useRoute();
const router = useRouter();
const code = ref(typeof route.query.code === "string" ? route.query.code : "");
const username = ref("");
const password = ref("");
const submitting = ref(false);
const redirectTarget = computed(() => normalizeAuthRedirectTarget(route.query.redirect, "/image-tasks"));
const loginLink = computed(() => ({
  path: "/login",
  query: redirectTarget.value === "/image-tasks" ? undefined : { redirect: redirectTarget.value },
}));

async function handleSubmit() {
  submitting.value = true;
  try {
    await activateInviteAndStoreSession({
      code: code.value,
      username: username.value,
      password: password.value,
    });
    await router.replace(redirectTarget.value);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "激活失败");
  } finally {
    submitting.value = false;
  }
}
</script>
