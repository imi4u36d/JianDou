<template>
  <Teleport to="body">
    <Transition name="material-favorite-dialog-fade">
      <div
        v-if="open"
        class="material-favorite-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="material-favorite-dialog-title"
        @click.self="close"
        @keydown.esc.stop.prevent="close"
      >
        <div class="material-favorite-dialog__panel">
          <div class="material-favorite-dialog__head">
            <div>
              <h3 id="material-favorite-dialog-title">{{ title }}</h3>
              <p v-if="asset">{{ asset.title }}</p>
              <p v-else-if="batchAssets.length">已选择 {{ batchAssets.length }} 个素材</p>
            </div>
            <button type="button" aria-label="关闭收藏夹弹窗" @click="close">
              <IconClose size="sm" />
            </button>
          </div>

          <div class="material-favorite-dialog__folders">
            <div
              v-for="folder in folders"
              :key="folder.id"
              class="material-favorite-dialog__folder"
              :class="{ 'material-favorite-dialog__folder-active': activeFolderIds.includes(folder.id) }"
            >
              <form
                v-if="editingFolderId === folder.id"
                class="material-favorite-dialog__rename"
                @submit.prevent="submitRename(folder.id)"
              >
                <input
                  v-model="editingFolderName"
                  type="text"
                  maxlength="28"
                  aria-label="收藏夹名称"
                  @keydown.stop
                />
                <button type="submit" :disabled="!editingFolderName.trim()">保存</button>
                <button type="button" @click="cancelRename">取消</button>
              </form>
              <template v-else>
                <button
                  type="button"
                  class="material-favorite-dialog__folder-main"
                  :disabled="!hasTargetAssets"
                  @click="emit('folderClick', folder.id)"
                >
                  <IconHeart size="sm" :filled="activeFolderIds.includes(folder.id)" />
                  <span>{{ folder.name }}</span>
                  <small>{{ folder.assetIds.length }}</small>
                </button>
                <div v-if="!hasTargetAssets" class="material-favorite-dialog__folder-actions">
                  <button type="button" @click="beginRename(folder)">
                    <IconEdit size="xs" />
                    修改
                  </button>
                  <button
                    type="button"
                    class="material-favorite-dialog__folder-delete"
                    @click="emit('delete', folder)"
                  >
                    <IconDelete size="xs" />
                    删除
                  </button>
                </div>
              </template>
            </div>
            <span v-if="!folders.length" class="material-favorite-dialog__empty">还没有收藏夹</span>
          </div>

          <form class="material-favorite-dialog__create" @submit.prevent="submitCreate">
            <input v-model="newFolderName" type="text" maxlength="28" placeholder="输入收藏夹名称" />
            <button type="submit" :disabled="!newFolderName.trim()">
              <IconPlus size="xs" />
              添加
            </button>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { MaterialAssetLibraryItem, MaterialFavoriteFolder } from "@/types";
import { IconClose, IconDelete, IconEdit, IconHeart, IconPlus } from "@/components/icons";
import type {
  MaterialFavoriteCreateRequest,
  MaterialFavoriteRenameRequest,
} from "./material-favorite-dialog";

const props = defineProps<{
  open: boolean;
  folders: MaterialFavoriteFolder[];
  asset: MaterialAssetLibraryItem | null;
  batchAssets: MaterialAssetLibraryItem[];
  activeFolderIds: string[];
}>();

const emit = defineEmits<{
  close: [];
  folderClick: [folderId: string];
  create: [request: MaterialFavoriteCreateRequest];
  rename: [request: MaterialFavoriteRenameRequest];
  delete: [folder: MaterialFavoriteFolder];
}>();

const newFolderName = ref("");
const editingFolderId = ref("");
const editingFolderName = ref("");
const hasTargetAssets = computed(() => Boolean(props.asset || props.batchAssets.length));
const title = computed(() => {
  if (props.batchAssets.length) return "批量添加到收藏夹";
  if (props.asset) return "添加到收藏夹";
  return "管理收藏夹";
});

function resetFormState() {
  newFolderName.value = "";
  editingFolderId.value = "";
  editingFolderName.value = "";
}

function close() {
  resetFormState();
  emit("close");
}

function beginRename(folder: MaterialFavoriteFolder) {
  editingFolderId.value = folder.id;
  editingFolderName.value = folder.name;
}

function cancelRename() {
  editingFolderId.value = "";
  editingFolderName.value = "";
}

function submitCreate() {
  const name = newFolderName.value.trim();
  if (!name) return;
  emit("create", { name, complete: () => (newFolderName.value = "") });
}

function submitRename(folderId: string) {
  const name = editingFolderName.value.trim();
  if (!name) return;
  emit("rename", { folderId, name, complete: cancelRename });
}

watch(
  () => props.open,
  (open) => {
    if (!open) resetFormState();
  },
);
</script>

<style scoped src="./material-favorite-dialog.css"></style>
