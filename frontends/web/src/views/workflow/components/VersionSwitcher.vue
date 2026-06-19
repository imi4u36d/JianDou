<script setup lang="ts">
import type { StageVersion } from "@/types";
import { IconMore } from "@/components/icons";

const props = defineProps<{
  versions: StageVersion[];
  activeVersionId?: string;
  busyActionKey?: string;
  showMenu?: boolean;
}>();

const emit = defineEmits<{
  select: [versionId: string];
  reuse: [assetId: string, versionId: string];
  delete: [version: StageVersion];
}>();

function displayTitle(version: StageVersion): string {
  const rawTitle = (version.title || "").trim();
  const versionPrefixPattern = new RegExp(`^V${version.versionNo}[.、\\-_:：·\\s]*`, "i");
  const dedupedTitle = rawTitle.replace(versionPrefixPattern, "").trim();
  return dedupedTitle || rawTitle || "未命名版本";
}

function positionMenu(event: ToggleEvent) {
  if (event.newState !== "open") return;
  const popover = event.target as HTMLElement;
  const trigger = popover.parentElement?.querySelector<HTMLElement>(".workflow-more-menu__trigger");
  if (!trigger) return;
  const rect = trigger.getBoundingClientRect();
  const popoverWidth = 150;
  let left = rect.right - popoverWidth;
  if (left < 8) left = 8;
  if (left + popoverWidth > window.innerWidth - 8) left = window.innerWidth - popoverWidth - 8;
  popover.style.left = `${left}px`;
  popover.style.top = `${rect.bottom + 4}px`;
}
</script>

<template>
  <div class="version-switcher">
    <div class="version-switcher__tabs">
      <article
        v-for="version in versions"
        :key="version.id"
        class="version-switcher__tab"
        :class="{ 'version-switcher__tab-active': activeVersionId === version.id }"
      >
        <button type="button" class="version-switcher__tab-main" @click="emit('select', version.id)">
          <span class="compact-version-card__badge">V{{ version.versionNo }}</span>
          <strong>{{ displayTitle(version) }}</strong>
          <span v-if="version.selected" class="compact-version-card__status">已选中</span>
          <span v-else class="compact-version-card__status">{{ version.status }}</span>
        </button>
        <div v-if="showMenu !== false" class="workflow-more-menu compact-version-menu">
          <button type="button" class="workflow-more-menu__trigger" aria-label="版本操作" :popovertarget="`vsm-${version.id}`">
            <IconMore size="sm" />
          </button>
          <div :id="`vsm-${version.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionMenu">
            <button type="button" :disabled="version.selected || busyActionKey === version.id" @click="emit('select', version.id)">
              {{ version.selected ? "已选中" : "设为当前" }}
            </button>
            <button type="button" :disabled="!version.asset || busyActionKey === `reuse-${version.id}`" @click="emit('reuse', version.asset?.id || '', version.id)">复用</button>
            <button type="button" class="workflow-menu-danger" :disabled="busyActionKey === `delete-${version.id}`" @click="emit('delete', version)">删除版本</button>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>
