<template>
  <el-dialog v-model="editorVisible" :title="editorMode === 'create' ? '新建用户' : '编辑用户'" width="520px">
    <el-form label-position="top">
      <el-form-item label="用户名">
        <el-input v-model.trim="editorUsername" :disabled="editorMode === 'edit'" placeholder="3-32 位登录名" />
      </el-form-item>
      <el-form-item v-if="editorMode === 'create'" label="初始密码">
        <el-input v-model="editorPassword" placeholder="8-72 位密码" show-password type="password" />
      </el-form-item>
      <div class="user-dialogs__grid">
        <el-form-item label="角色">
          <el-select v-model="editorRole">
            <el-option label="管理员" value="ADMIN" />
            <el-option label="普通用户" value="USER" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editorStatus">
            <el-option label="启用" value="ACTIVE" />
            <el-option label="禁用" value="DISABLED" />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item label="任务并发额度">
        <el-input-number v-model="editorConcurrencyLimit" :min="1" :max="20" :step="1" controls-position="right" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editorVisible = false">取消</el-button>
      <el-button :loading="submittingEditor" type="primary" @click="emit('submit-editor')">
        {{ editorMode === "create" ? "创建" : "保存" }}
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="passwordDialogVisible" title="重置用户密码" width="420px">
    <el-form label-position="top">
      <el-form-item label="新密码">
        <el-input v-model="newPassword" placeholder="新密码" show-password type="password" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="passwordDialogVisible = false">取消</el-button>
      <el-button :loading="submittingPassword" type="primary" @click="emit('submit-password')">更新</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="modelKeyDialogVisible" :title="modelKeyDialogTitle" width="720px">
    <el-alert
      :closable="false"
      class="user-dialogs__alert"
      show-icon
      title="只更新已填写的 Key，空项保持不变。"
      type="info"
    />
    <el-form v-loading="loadingModelConfig" label-position="top">
      <div class="user-dialogs__key-list">
        <div v-for="item in modelKeyForm.providers" :key="item.key" class="user-dialogs__key-row">
          <div class="user-dialogs__key-meta">
            <strong>{{ item.vendor || item.provider || item.key }}</strong>
            <span>{{ item.kinds.map(formatModelKind).join(" / ") || "模型接入" }}</span>
          </div>
          <el-input
            :model-value="item.apiKey"
            clearable
            placeholder="新 API Key"
            show-password
            type="password"
            @update:model-value="updateProviderApiKey(item.key, $event)"
          />
        </div>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="modelKeyDialogVisible = false">取消</el-button>
      <el-button :loading="submittingModelKeys" type="primary" @click="emit('submit-model-keys')">重设</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { formatModelKind } from "@/admin/features/users/user-management-presenters";
import type { AdminModelConfigProviderItem, UserRole, UserStatus } from "@/types";

const props = defineProps<{
  editorMode: "create" | "edit";
  editorForm: {
    username: string;
    password: string;
    role: UserRole;
    status: UserStatus;
    taskConcurrencyLimit: number;
  };
  passwordForm: { password: string };
  modelKeyForm: { providers: Array<AdminModelConfigProviderItem & { apiKey: string }> };
  modelKeyDialogTitle: string;
  submittingEditor: boolean;
  submittingPassword: boolean;
  loadingModelConfig: boolean;
  submittingModelKeys: boolean;
}>();

const editorVisible = defineModel<boolean>("editorVisible", { required: true });
const passwordDialogVisible = defineModel<boolean>("passwordDialogVisible", { required: true });
const modelKeyDialogVisible = defineModel<boolean>("modelKeyDialogVisible", { required: true });
const emit = defineEmits<{
  "submit-editor": [];
  "submit-password": [];
  "submit-model-keys": [];
  "update:editorForm": [value: typeof props.editorForm];
  "update:passwordForm": [value: typeof props.passwordForm];
  "update:modelKeyForm": [value: typeof props.modelKeyForm];
}>();

function editorField<K extends keyof typeof props.editorForm>(field: K) {
  return computed({
    get: () => props.editorForm[field],
    set: (value: (typeof props.editorForm)[K]) => emit("update:editorForm", { ...props.editorForm, [field]: value }),
  });
}

const editorUsername = editorField("username");
const editorPassword = editorField("password");
const editorRole = editorField("role");
const editorStatus = editorField("status");
const editorConcurrencyLimit = editorField("taskConcurrencyLimit");
const newPassword = computed({
  get: () => props.passwordForm.password,
  set: (password: string) => emit("update:passwordForm", { password }),
});

function updateProviderApiKey(key: string, apiKey: string) {
  emit("update:modelKeyForm", {
    providers: props.modelKeyForm.providers.map((provider) =>
      provider.key === key ? { ...provider, apiKey } : provider
    ),
  });
}
</script>

<style scoped src="./user-management-dialogs.css"></style>
