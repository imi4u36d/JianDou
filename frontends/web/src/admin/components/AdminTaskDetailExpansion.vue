<template>
  <div class="task-page__detail-panel">
    <div v-if="loading" class="task-page__detail-loading">
      <el-skeleton :rows="4" animated />
    </div>
    <el-alert
      v-else-if="error"
      :closable="false"
      show-icon
      type="error"
      :title="error"
    />
    <div v-else-if="expandedDetail(task)" class="task-page__detail-grid">
      <section class="task-page__detail-section">
        <div class="task-page__detail-section-head">
          <h3>执行进度</h3>
          <el-tag
            :type="statusTagType(expandedDetail(task)?.status || task.status)"
            effect="light"
            size="small"
          >
            {{ statusLabel(expandedDetail(task)?.status || task.status) }}
          </el-tag>
        </div>
        <div class="task-page__detail-progress">
          <div class="task-page__detail-progress-head">
            <strong>{{ detailProgressValue(task) }}%</strong>
            <span>{{ progressHint(expandedDetail(task) || task) }}</span>
          </div>
          <el-progress :percentage="detailProgressValue(task)" :stroke-width="10" />
        </div>
        <dl class="task-page__detail-list">
          <div v-for="item in executionRows(task)" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </div>
        </dl>
      </section>

      <section class="task-page__detail-section">
        <div class="task-page__detail-section-head">
          <h3>失败原因</h3>
          <el-tag :type="failureTagType(task)" effect="light" size="small">{{
            failureStateLabel(task)
          }}</el-tag>
        </div>
        <el-alert
          v-if="failureMessage(task)"
          :closable="false"
          show-icon
          type="error"
          :title="failureMessage(task)"
        />
        <div v-else class="task-page__detail-empty">暂无失败信息</div>
        <dl class="task-page__detail-list task-page__detail-list--compact">
          <div v-for="item in failureRows(task)" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </div>
        </dl>
      </section>

      <section class="task-page__detail-section task-page__detail-section--wide">
        <div class="task-page__detail-section-head">
          <h3>任务参数</h3>
          <el-tag effect="plain" size="small">{{ requestDurationMode(task) }}</el-tag>
        </div>
        <dl class="task-page__detail-list task-page__detail-list--params">
          <div v-for="item in requestRows(task)" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </div>
        </dl>
        <div v-if="creativePrompt(task)" class="task-page__detail-text">
          <strong>创意提示</strong>
          <p>{{ creativePrompt(task) }}</p>
        </div>
        <div v-if="transcriptPreview(task)" class="task-page__detail-text">
          <strong>正文预览</strong>
          <p>{{ transcriptPreview(task) }}</p>
        </div>
        <el-collapse v-if="requestSnapshotJson(task)" class="task-page__detail-json">
          <el-collapse-item title="原始请求参数" name="request">
            <pre>{{ requestSnapshotJson(task) }}</pre>
          </el-collapse-item>
        </el-collapse>
      </section>

      <section class="task-page__detail-section task-page__detail-section--wide">
        <div class="task-page__detail-section-head">
          <h3>产物与监控</h3>
          <el-tag effect="plain" size="small">{{ renderedClipLabel(expandedDetail(task) || task) }}</el-tag>
        </div>
        <dl class="task-page__detail-list task-page__detail-list--params">
          <div v-for="item in outputRows(task)" :key="item.label">
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </div>
        </dl>
      </section>
    </div>
    <div v-else class="task-page__detail-empty">点击展开后读取任务详情</div>
  </div>
</template>

<script setup lang="ts">
import { createAdminTaskPresenters } from "@/admin/features/tasks/task-management-presenters";
import type { AdminTaskListItem, TaskDetail } from "@/types";

const props = defineProps<{
  task: AdminTaskListItem;
  detail?: TaskDetail;
  loading: boolean;
  error: string;
}>();

const {
  statusTagType,
  statusLabel,
  expandedDetail,
  detailProgressValue,
  progressHint,
  executionRows,
  failureTagType,
  failureStateLabel,
  failureMessage,
  failureRows,
  requestDurationMode,
  requestRows,
  creativePrompt,
  transcriptPreview,
  requestSnapshotJson,
  renderedClipLabel,
  outputRows,
} = createAdminTaskPresenters((task) => task.id === props.task.id ? props.detail : undefined);
</script>

<style scoped src="./admin-task-detail-expansion.css"></style>
