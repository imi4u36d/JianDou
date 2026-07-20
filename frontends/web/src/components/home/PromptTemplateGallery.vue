<template>
  <section class="prompt-template-gallery" aria-label="提示词模板">
    <div class="prompt-template-gallery__head">
      <h2>模板</h2>
    </div>

    <div class="prompt-template-gallery__rail">
      <button
        v-for="template in promptTemplates"
        :key="template.id"
        type="button"
        class="prompt-template-card"
        @click="openPreview(template)"
      >
        <img :src="template.imageUrl" :alt="template.title" loading="lazy" />
        <span class="prompt-template-card__meta">
          <strong>{{ template.title }}</strong>
          <small>{{ template.tag }}</small>
        </span>
      </button>
    </div>

    <AppPreviewDialog
      :open="Boolean(previewTemplate)"
      kind="image"
      :title="previewTemplate?.title ?? ''"
      :subtitle="previewTemplate?.tag ?? ''"
      :url="previewTemplate?.imageUrl ?? ''"
      :show-download="false"
      :wide="false"
      @close="closePreview"
    >
      <template v-if="previewTemplate" #actions>
        <button
          type="button"
          class="jd-button jd-button--sm prompt-template-preview__apply"
          @click="applyTemplate(previewTemplate)"
        >
          <IconCheck size="xs" />
          <span>应用</span>
        </button>
      </template>

      <div v-if="previewTemplate" class="prompt-template-preview__body">
        <div class="prompt-template-preview__media">
          <img :src="previewTemplate.imageUrl" :alt="previewTemplate.title" />
        </div>
        <section class="prompt-template-preview__prompt">
          <h4>提示词</h4>
          <p>{{ previewTemplate.prompt }}</p>
          <button type="button" @click="applyTemplate(previewTemplate)">
            <IconCheck size="xs" />
            使用模板
          </button>
        </section>
      </div>
    </AppPreviewDialog>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import AppPreviewDialog from "@/components/common/AppPreviewDialog.vue";
import { IconCheck } from "@/components/icons";
import { promptTemplates, type PromptTemplate } from "./prompt-templates";

const emit = defineEmits<{
  apply: [template: PromptTemplate];
}>();

const previewTemplate = ref<PromptTemplate | null>(null);

function openPreview(template: PromptTemplate) {
  previewTemplate.value = template;
}

function closePreview() {
  previewTemplate.value = null;
}

function applyTemplate(template: PromptTemplate) {
  emit("apply", template);
  closePreview();
}
</script>

<style scoped src="./prompt-template-gallery.css"></style>
