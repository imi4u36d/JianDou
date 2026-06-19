<template>
  <div class="page-shell login-view">
    <div class="login-view__intro">
      <h1>管理端登录</h1>
    </div>

    <el-card class="surface-card login-view__card" shadow="never">
      <el-form label-position="top" @submit.prevent="handleSubmit">
        <el-form-item label="用户名">
          <el-input v-model.trim="form.username" autocomplete="username" placeholder="用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" autocomplete="current-password" placeholder="密码" show-password type="password" />
        </el-form-item>
        <el-button :loading="submitting" class="login-view__submit" native-type="submit" type="primary">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { loginAndStoreSession, logoutAndClearSession } from "@/auth/session";

const route = useRoute();
const router = useRouter();

const form = reactive({
  username: "",
  password: ""
});
const submitting = ref(false);

function normalizeRedirectTarget(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return "/admin";
  }
  return value;
}

async function handleSubmit() {
  submitting.value = true;
  try {
    const session = await loginAndStoreSession({
      username: form.username,
      password: form.password
    });
    if (session.user?.role !== "ADMIN") {
      await logoutAndClearSession();
      throw new Error("当前账号不是管理员，不能进入管理系统");
    }
    ElMessage.success("登录成功");
    await router.replace(normalizeRedirectTarget(route.query.redirect));
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "登录失败");
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.login-view {
  display: grid;
  grid-template-columns: minmax(0, 430px);
  justify-content: center;
  align-items: center;
  gap: 20px;
  padding: 24px;
}

.login-view__intro {
  text-align: center;
}

.login-view__intro h1 {
  margin: 0;
  font-family: inherit;
}

.login-view__intro h1 {
  font-size: clamp(1.8rem, 4.8vw, 2.4rem);
  line-height: 1.12;
}

.login-view__card {
  border-radius: 20px;
  padding-top: 4px;
}

.login-view__alert {
  margin-bottom: 18px;
}

.login-view__submit {
  width: 100%;
  margin-top: 8px;
}

@media (max-width: 980px) {
  .login-view {
    grid-template-columns: 1fr;
    padding: 20px;
  }
}
</style>
