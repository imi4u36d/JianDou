<template>
  <section class="workflow-view">
    <aside class="workflow-rail">
      <div class="workflow-rail-flip-shell">
        <div class="workflow-rail-flip" :class="{ 'workflow-rail-flip-active': createReviewFlipped }">
          <section class="surface-panel workflow-panel workflow-rail-panel workflow-rail-flip__face workflow-rail-flip__face-front">
            <p v-if="createError" class="workflow-error">{{ createError }}</p>

            <div class="workflow-rail__stats">
              <div class="surface-tile workflow-mini-stat">
                <span>总工作流</span>
                <strong>{{ workflows.length }}</strong>
              </div>
              <div class="surface-tile workflow-mini-stat">
                <span>当前选中</span>
                <strong>{{ selectedWorkflowSummary?.title || "未选择" }}</strong>
              </div>
            </div>

            <div class="workflow-rail__actions workflow-rail__actions-inline">
              <button class="btn-secondary btn-sm" type="button" :disabled="loadingWorkflows" @click="loadWorkflows">
                {{ loadingWorkflows ? "刷新中..." : "刷新" }}
              </button>
              <button
                class="btn-primary btn-sm workflow-submit"
                type="button"
                :disabled="creatingWorkflow || loadingOptions"
                @click="startCreateWorkflow"
              >
                {{ creatingWorkflow ? "创建中..." : "新建工作流" }}
              </button>
            </div>

            <label class="workflow-rail__search">
              <span>搜索工作流</span>
              <input v-model="workflowSearch" class="field-input" type="search" placeholder="按标题、阶段、状态筛选" />
            </label>

            <div class="workflow-list-shell">
              <p v-if="listError" class="workflow-error">{{ listError }}</p>
              <div v-else-if="loadingWorkflows" class="workflow-empty">正在加载工作流...</div>
              <div v-else-if="!filteredWorkflows.length" class="workflow-empty">
                {{ workflows.length ? "没有匹配的工作流" : "还没有阶段工作流" }}
              </div>
              <div v-else class="workflow-list">
                <button
                  v-for="item in filteredWorkflows"
                  :key="item.id"
                  type="button"
                  class="workflow-list__item"
                  :class="{ 'workflow-list__item-active': item.id === selectedWorkflowId }"
                  @click="openWorkflow(item.id)"
                >
                  <div class="workflow-list__top">
                    <strong>{{ item.title }}</strong>
                    <span class="surface-chip">{{ item.currentStage }}</span>
                  </div>
                  <div class="workflow-list__meta">
                    <span>{{ item.aspectRatio }}</span>
                    <span>分镜 {{ item.storyboardVersionCount }}</span>
                    <span>关键帧 {{ item.keyframeVersionCount }}</span>
                    <span>视频 {{ item.videoVersionCount }}</span>
                  </div>
                  <div class="workflow-list__meta">
                    <span>{{ item.status }}</span>
                    <span>评分 {{ ratingLabel(item.effectRating) }}</span>
                  </div>
                  <div class="workflow-list__meta">
                    <span>{{ formatDateTime(item.updatedAt) }}</span>
                  </div>
                </button>
              </div>
            </div>
          </section>

          <section class="surface-panel workflow-panel workflow-rail-panel workflow-rail-flip__face workflow-rail-flip__face-back">
            <div class="workflow-review-card workflow-review-card-rail">
              <div class="stage-config-card__head workflow-review-card__head">
                <div>
                  <h3>创建前检查</h3>
                </div>
                <div class="workflow-review-card__status">
                  <span class="surface-chip">必填完成 {{ createReviewConfiguredCount }} / {{ createReviewRequiredItems.length }}</span>
                  <span class="surface-chip" :class="{ 'workflow-review-chip-warning': !canSubmitCreateReview }">
                    {{ canSubmitCreateReview ? "可以保存" : "仍有必填项缺失" }}
                  </span>
                </div>
              </div>

              <p v-if="createError" class="workflow-error">{{ createError }}</p>

              <div class="workflow-review-grid workflow-review-grid-rail">
                <article v-for="section in createReviewSections" :key="section.key" class="workflow-review-section">
                  <div class="workflow-review-section__head">
                    <p class="workflow-eyebrow">{{ section.eyebrow }}</p>
                    <h4>{{ section.title }}</h4>
                  </div>

                  <div class="workflow-review-list">
                    <div v-for="item in section.items" :key="item.key" class="workflow-review-item">
                      <div>
                        <strong>{{ item.label }}</strong>
                        <p>{{ item.valueLabel }}</p>
                      </div>
                      <div class="workflow-review-item__meta">
                        <span class="surface-chip">{{ item.required ? "必填" : "可选" }}</span>
                        <span
                          class="surface-chip"
                          :class="item.configured ? 'workflow-review-chip-success' : (item.required ? 'workflow-review-chip-warning' : 'workflow-review-chip-muted')"
                        >
                          {{ item.configured ? "已配置" : (item.required ? "未配置" : "未填写") }}
                        </span>
                      </div>
                    </div>
                  </div>
                </article>
              </div>

              <div class="workflow-review-actions workflow-review-actions-rail">
                <button class="btn-secondary btn-sm" type="button" :disabled="creatingWorkflow" @click="closeCreateReview">
                  取消
                </button>
                <button
                  class="btn-primary btn-sm"
                  type="button"
                  :disabled="creatingWorkflow || !canSubmitCreateReview"
                  @click="handleCreateWorkflow"
                >
                  {{ creatingWorkflow ? "保存中..." : "保存工作流" }}
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>
    </aside>

    <section class="workflow-main">
      <section v-if="createComposerVisible" class="surface-panel workflow-panel workflow-create-shell">
        <div class="workflow-create-shell__grid">
          <div class="workflow-create-canvas">
            <form id="workflow-create-form" class="workflow-form workflow-stage-create" @submit.prevent>
              <section class="surface-tile stage-config-card stage-config-card--base">
                <div class="stage-config-card__head">
                  <div class="stage-config-card__title-row">
                    <div>
                      <p class="workflow-eyebrow">Workflow Base</p>
                      <h3>工作流基础信息</h3>
                    </div>

                    <div class="stage-switch-row">
                      <button
                        v-for="stage in createStageOptions"
                        :key="stage.key"
                        type="button"
                        class="stage-switch-btn"
                        :class="{ 'stage-switch-btn-active': activeCreateStage === stage.key }"
                        @click="activeCreateStage = stage.key"
                      >
                        {{ stage.shortLabel }}
                      </button>
                    </div>
                  </div>
                </div>

                <div class="stage-config-fields stage-config-fields--single">
                  <label class="workflow-field stage-config-field-title">
                    <span>标题</span>
                    <input v-model="createForm.title" class="field-input" required placeholder="例如：第 12 集阶段拆分版" />
                  </label>

                  <label class="workflow-field stage-config-field-body">
                    <span>正文</span>
                    <textarea
                      v-model="createForm.transcriptText"
                      class="field-textarea"
                      rows="5"
                      placeholder="输入小说正文或脚本内容"
                    ></textarea>
                  </label>

                  <label class="workflow-field stage-config-field-prompt">
                    <span>全局 Prompt</span>
                    <textarea
                      v-model="createForm.globalPrompt"
                      class="field-textarea"
                      rows="4"
                      placeholder="填写这一轮工作流的总体创作要求"
                    ></textarea>
                  </label>
                </div>
              </section>

              <section class="surface-tile stage-config-card stage-config-card--focus">
                <div class="stage-config-card__head">
                  <div>
                    <p class="workflow-eyebrow">{{ activeCreateStageMeta.label }}</p>
                    <h3>{{ activeCreateStageMeta.description }}</h3>
                  </div>
                  <span class="surface-chip">参数步骤 {{ activeStageFieldIndex + 1 }} / {{ activeStageSteps.length }}</span>
                </div>

                <div class="stage-progress-form">
                  <div class="stage-progress-form__rail">
                    <div class="stage-progress-form__bar">
                      <span class="stage-progress-form__fill" :style="{ width: `${activeStageProgress}%` }"></span>
                    </div>
                    <div class="stage-progress-form__steps">
                      <button
                        v-for="(step, index) in activeStageSteps"
                        :key="step.key"
                        type="button"
                        class="stage-progress-form__step"
                        :class="{
                          'stage-progress-form__step-active': index === activeStageFieldIndex,
                          'stage-progress-form__step-done': index < activeStageFieldIndex,
                        }"
                        @click="setStageFieldIndex(index)"
                      >
                        <span>{{ index + 1 }}</span>
                        <strong>{{ step.label }}</strong>
                      </button>
                    </div>
                  </div>

                  <div class="stage-progress-form__panel">
                    <div class="stage-progress-form__panel-head">
                      <div>
                        <h4>{{ currentStageField?.label }}</h4>
                      </div>
                      <span class="surface-chip">{{ currentStageField?.valueLabel }}</span>
                    </div>

                    <div v-if="currentStageField?.key === 'textAnalysisModel'" class="stage-progress-form__field">
                      <span>选择文本分镜模型</span>
                      <div class="stage-option-grid">
                        <button
                          v-for="item in textModelOptions"
                          :key="item.value"
                          type="button"
                          class="stage-option-card"
                          :class="{ 'stage-option-card-active': createForm.textAnalysisModel === item.value }"
                          @click="createForm.textAnalysisModel = item.value"
                        >
                          <strong>{{ item.label }}</strong>
                          <span>{{ item.description || item.provider || item.value }}</span>
                        </button>
                      </div>
                    </div>

                    <div v-else-if="currentStageField?.key === 'minDurationSeconds'" class="stage-progress-form__field stage-progress-form__field-slider">
                      <span>拖动设置最小时长</span>
                      <input
                        v-model="createForm.minDurationSeconds"
                        class="stage-slider__range"
                        type="range"
                        min="1"
                        max="20"
                        step="1"
                      />
                      <div class="stage-slider__meta">
                        <strong>{{ createForm.minDurationSeconds || "1" }} 秒</strong>
                        <input
                          v-model="createForm.minDurationSeconds"
                          class="field-input stage-slider__number"
                          type="number"
                          min="1"
                          max="20"
                          step="1"
                        />
                      </div>
                    </div>

                    <div v-else-if="currentStageField?.key === 'maxDurationSeconds'" class="stage-progress-form__field stage-progress-form__field-slider">
                      <span>拖动设置最大时长</span>
                      <input
                        v-model="createForm.maxDurationSeconds"
                        class="stage-slider__range"
                        type="range"
                        :min="Number(createForm.minDurationSeconds) || 1"
                        max="30"
                        step="1"
                      />
                      <div class="stage-slider__meta">
                        <strong>{{ createForm.maxDurationSeconds || "1" }} 秒</strong>
                        <input
                          v-model="createForm.maxDurationSeconds"
                          class="field-input stage-slider__number"
                          type="number"
                          :min="Number(createForm.minDurationSeconds) || 1"
                          max="30"
                          step="1"
                        />
                      </div>
                    </div>

                    <div v-else-if="currentStageField?.key === 'seed'" class="stage-progress-form__field stage-progress-form__field-slider">
                      <span>选择 Seed 模式</span>
                      <div class="stage-toggle-row">
                        <button
                          type="button"
                          class="stage-toggle-chip"
                          :class="{ 'stage-toggle-chip-active': createForm.seed === '' }"
                          @click="createForm.seed = ''"
                        >
                          自动
                        </button>
                        <button
                          type="button"
                          class="stage-toggle-chip"
                          :class="{ 'stage-toggle-chip-active': createForm.seed !== '' }"
                          @click="createForm.seed = createForm.seed || '1024'"
                        >
                          固定 Seed
                        </button>
                      </div>
                      <template v-if="createForm.seed !== ''">
                        <input
                          v-model="createForm.seed"
                          class="stage-slider__range"
                          type="range"
                          min="0"
                          max="9999"
                          step="1"
                        />
                        <div class="stage-slider__meta">
                          <strong>{{ createForm.seed }}</strong>
                          <input
                            v-model="createForm.seed"
                            class="field-input stage-slider__number"
                            type="number"
                            min="0"
                            max="9999"
                            step="1"
                          />
                        </div>
                      </template>
                    </div>

                    <div v-else-if="currentStageField?.key === 'imageModel'" class="stage-progress-form__field">
                      <span>选择关键帧模型</span>
                      <div class="stage-option-grid">
                        <button
                          v-for="item in imageModelOptions"
                          :key="item.value"
                          type="button"
                          class="stage-option-card"
                          :class="{ 'stage-option-card-active': createForm.imageModel === item.value }"
                          @click="createForm.imageModel = item.value"
                        >
                          <strong>{{ item.label }}</strong>
                          <span>{{ item.description || item.provider || item.value }}</span>
                        </button>
                      </div>
                    </div>

                    <div v-else-if="currentStageField?.key === 'stylePreset'" class="stage-progress-form__field">
                      <span>选择视觉风格</span>
                      <div class="stage-option-grid">
                        <button
                          v-for="item in stylePresetOptions"
                          :key="item.key"
                          type="button"
                          class="stage-option-card"
                          :class="{ 'stage-option-card-active': createForm.stylePreset === item.key }"
                          @click="createForm.stylePreset = item.key"
                        >
                          <strong>{{ item.label }}</strong>
                          <span>{{ item.description || item.key }}</span>
                        </button>
                      </div>
                    </div>

                    <div v-else-if="currentStageField?.key === 'aspectRatio'" class="stage-progress-form__field">
                      <span>选择画面比例</span>
                      <div class="stage-option-grid stage-option-grid--compact">
                        <button
                          v-for="item in aspectRatioOptions"
                          :key="item.value"
                          type="button"
                          class="stage-option-card"
                          :class="{ 'stage-option-card-active': createForm.aspectRatio === item.value }"
                          @click="createForm.aspectRatio = item.value"
                        >
                          <strong>{{ item.label }}</strong>
                          <span>输出画面比例</span>
                        </button>
                      </div>
                    </div>

                    <div v-else-if="currentStageField?.key === 'visionModel'" class="stage-progress-form__field">
                      <span>选择视觉模型</span>
                      <div class="stage-option-grid">
                        <button
                          v-for="item in visionModelOptions"
                          :key="item.value"
                          type="button"
                          class="stage-option-card"
                          :class="{ 'stage-option-card-active': createForm.visionModel === item.value }"
                          @click="createForm.visionModel = item.value"
                        >
                          <strong>{{ item.label }}</strong>
                          <span>{{ item.description || item.provider || item.value }}</span>
                        </button>
                      </div>
                    </div>

                    <div v-else-if="currentStageField?.key === 'videoModel'" class="stage-progress-form__field">
                      <span>选择视频模型</span>
                      <div class="stage-option-grid">
                        <button
                          v-for="item in videoModelOptions"
                          :key="item.value"
                          type="button"
                          class="stage-option-card"
                          :class="{ 'stage-option-card-active': createForm.videoModel === item.value }"
                          @click="createForm.videoModel = item.value"
                        >
                          <strong>{{ item.label }}</strong>
                          <span>{{ item.description || item.provider || item.value }}</span>
                        </button>
                      </div>
                    </div>

                    <div v-else-if="currentStageField?.key === 'videoSize'" class="stage-progress-form__field">
                      <span>选择输出尺寸</span>
                      <div class="stage-option-grid stage-option-grid--compact">
                        <button
                          v-for="item in videoSizeOptions"
                          :key="item.value"
                          type="button"
                          class="stage-option-card"
                          :class="{ 'stage-option-card-active': createForm.videoSize === item.value }"
                          @click="createForm.videoSize = item.value"
                        >
                          <strong>{{ item.label }}</strong>
                          <span>{{ item.width && item.height ? `${item.width} × ${item.height}` : item.value }}</span>
                        </button>
                      </div>
                    </div>

                    <div class="stage-progress-form__actions">
                      <button
                        class="btn-secondary btn-sm"
                        type="button"
                        :disabled="activeStageFieldIndex === 0"
                        @click="previousStageField"
                      >
                        上一步
                      </button>
                      <button class="btn-secondary btn-sm" type="button" @click="nextStageField">
                        {{ activeStageFieldIndex >= activeStageSteps.length - 1 ? "回到第一项" : "下一步" }}
                      </button>
                    </div>
                  </div>

                  <div class="stage-progress-form__summary">
                    <button
                      v-for="(step, index) in activeStageSteps"
                      :key="`${activeCreateStage}-${step.key}`"
                      type="button"
                      class="stage-summary-card"
                      :class="{ 'stage-summary-card-active': index === activeStageFieldIndex }"
                      @click="setStageFieldIndex(index)"
                    >
                      <span>{{ step.label }}</span>
                      <strong>{{ step.valueLabel }}</strong>
                    </button>
                  </div>
                </div>
              </section>
            </form>
          </div>
        </div>
      </section>

      <div v-if="detailError" class="surface-panel workflow-banner workflow-banner-error">
        <p>{{ detailError }}</p>
        <button class="btn-secondary btn-sm" type="button" :disabled="loadingDetail" @click="reloadCurrentWorkflow">重新加载</button>
      </div>

      <div v-if="loadingDetail" class="surface-panel workflow-empty">
        正在加载工作流详情...
      </div>

      <template v-else-if="selectedWorkflow">
        <section v-if="activeCreateStage === 'storyboard'" class="surface-panel workflow-panel workflow-stage-panel">
          <div class="workflow-panel__head">
            <div>
              <p class="workflow-eyebrow">Stage 1</p>
              <h2>文本分镜模块</h2>
              <div class="workflow-summary__meta">
                <span class="surface-chip">{{ selectedWorkflow.title }}</span>
                <span class="surface-chip">{{ selectedWorkflow.status }}</span>
                <span class="surface-chip">{{ selectedWorkflow.currentStage }}</span>
                <span class="surface-chip">{{ selectedWorkflow.aspectRatio }}</span>
              </div>
            </div>
            <div class="workflow-stage-panel__actions">
              <div class="stage-switch-row">
                <button
                  v-for="stage in createStageOptions"
                  :key="`detail-${stage.key}`"
                  type="button"
                  class="stage-switch-btn"
                  :class="{ 'stage-switch-btn-active': activeCreateStage === stage.key }"
                  @click="activeCreateStage = stage.key"
                >
                  {{ stage.shortLabel }}
                </button>
              </div>
              <div class="workflow-summary__actions">
                <button class="btn-primary btn-sm" type="button" :disabled="busyActionKey === 'storyboard'" @click="handleGenerateStoryboard">
                  {{ busyActionKey === "storyboard" ? "生成中..." : "生成分镜版本" }}
                </button>
                <span class="surface-chip">{{ selectedWorkflow.storyboardVersions.length }} 个版本</span>
              </div>
            </div>
          </div>

          <div class="workflow-stage-grid">
            <section class="surface-tile workflow-summary-card workflow-summary-card-compact">
              <h3>工作流快照</h3>
              <div class="workflow-kv">
                <div class="workflow-kv__row">
                  <span>文本模型</span>
                  <strong>{{ selectedWorkflow.textAnalysisModel }}</strong>
                </div>
                <div class="workflow-kv__row">
                  <span>视觉模型</span>
                  <strong>{{ selectedWorkflow.visionModel }}</strong>
                </div>
                <div class="workflow-kv__row">
                  <span>关键帧模型</span>
                  <strong>{{ selectedWorkflow.imageModel }}</strong>
                </div>
                <div class="workflow-kv__row">
                  <span>视频模型</span>
                  <strong>{{ selectedWorkflow.videoModel }}</strong>
                </div>
                <div class="workflow-kv__row">
                  <span>视频尺寸</span>
                  <strong>{{ selectedWorkflow.videoSize || "-" }}</strong>
                </div>
                <div class="workflow-kv__row">
                  <span>风格</span>
                  <strong>{{ selectedWorkflow.stylePreset || "-" }}</strong>
                </div>
              </div>
              <div v-if="selectedWorkflow.transcriptText" class="workflow-note-block">
                <span>正文</span>
                <p>{{ selectedWorkflow.transcriptText }}</p>
              </div>
              <div v-if="selectedWorkflow.globalPrompt" class="workflow-note-block">
                <span>全局 Prompt</span>
                <p>{{ selectedWorkflow.globalPrompt }}</p>
              </div>
            </section>

            <section class="workflow-stage-content">
              <div v-if="!selectedWorkflow.storyboardVersions.length" class="workflow-empty">
                还没有分镜版本，先执行一次分镜生成。
              </div>
              <div v-else>
                <div v-if="selectedWorkflow.storyboardVersions.length > 1" class="workflow-scroll-hint">
                  左右滑动选择分镜版本
                </div>
                <div class="version-grid">
                <article v-for="version in selectedWorkflow.storyboardVersions" :key="version.id" class="surface-tile version-card">
                  <div class="version-card__head">
                    <div>
                      <h3>{{ version.title }}</h3>
                      <div class="version-card__meta">
                        <span class="surface-chip">V{{ version.versionNo }}</span>
                        <span class="surface-chip">{{ version.status }}</span>
                        <span v-if="version.selected" class="surface-chip">当前选中</span>
                      </div>
                    </div>
                    <button class="btn-secondary btn-sm" type="button" :disabled="version.selected || busyActionKey === version.id" @click="handleSelectStoryboard(version.id)">
                      {{ busyActionKey === version.id ? "处理中..." : (version.selected ? "已选中" : "设为当前") }}
                    </button>
                  </div>

                  <pre class="version-card__text">{{ storyboardPreview(version) }}</pre>

                  <div class="rating-row">
                    <button
                      v-for="score in ratingOptions"
                      :key="`${version.id}-${score}`"
                      type="button"
                      class="rating-pill"
                      :class="{ 'rating-pill-active': Number(stageRatingDrafts[version.id] || version.rating || 0) === score }"
                      @click="setStageRatingDraft(version.id, score)"
                    >
                      {{ score }}
                    </button>
                  </div>
                  <textarea
                    v-model="stageNoteDrafts[version.id]"
                    class="field-textarea version-card__textarea"
                    rows="3"
                    placeholder="分镜评价"
                  ></textarea>

                  <div class="version-card__actions">
                    <button class="btn-secondary btn-sm" type="button" :disabled="busyActionKey === `rate-${version.id}`" @click="handleRateStageVersion(version)">
                      {{ busyActionKey === `rate-${version.id}` ? "保存中..." : "保存评分" }}
                    </button>
                    <button
                      class="btn-ghost btn-sm"
                      type="button"
                      :disabled="!version.asset || busyActionKey === `reuse-${version.id}`"
                      @click="handleReuseAsset(version.asset?.id || '', version.id)"
                    >
                      {{ busyActionKey === `reuse-${version.id}` ? "复制中..." : "复制为新工作流" }}
                    </button>
                  </div>

                  <div v-if="version.asset?.tags?.length" class="tag-list">
                    <span v-for="tag in version.asset.tags" :key="tag.id" class="tag-chip">
                      {{ tag.tagKey }}: {{ tag.tagValue }}
                    </span>
                  </div>
                </article>
                </div>
              </div>
            </section>
          </div>
        </section>

        <section v-else-if="activeCreateStage === 'keyframe'" class="surface-panel workflow-panel workflow-stage-panel">
          <div class="workflow-panel__head">
            <div>
              <p class="workflow-eyebrow">Stage 2 / 3</p>
              <h2>关键帧模块</h2>
            </div>
            <div class="workflow-stage-panel__actions">
              <div class="stage-switch-row">
                <button
                  v-for="stage in createStageOptions"
                  :key="`detail-${stage.key}`"
                  type="button"
                  class="stage-switch-btn"
                  :class="{ 'stage-switch-btn-active': activeCreateStage === stage.key }"
                  @click="activeCreateStage = stage.key"
                >
                  {{ stage.shortLabel }}
                </button>
              </div>
              <div class="workflow-summary__actions">
                <span class="surface-chip">{{ selectedWorkflow.clipSlots.length }} 个镜头</span>
              </div>
            </div>
          </div>

          <div v-if="!selectedWorkflow.clipSlots.length" class="workflow-empty">
            选中分镜版本后，这里会展开镜头列表。
          </div>

          <div v-else class="clip-stack">
            <article v-for="slot in selectedWorkflow.clipSlots" :key="slot.clipIndex" class="surface-tile clip-card">
              <div class="clip-card__head">
                <div>
                  <p class="workflow-eyebrow">Clip {{ slot.clipIndex }}</p>
                  <h3>{{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}</h3>
                  <p class="clip-card__desc">{{ slot.scene || "暂无场景描述" }}</p>
                </div>
                <div class="clip-card__meta">
                  <span class="surface-chip">{{ slot.durationHint || `${slot.targetDurationSeconds || 0}s` }}</span>
                  <button class="btn-secondary btn-sm" type="button" :disabled="busyActionKey === `keyframe-${slot.clipIndex}`" @click="handleGenerateKeyframe(slot.clipIndex)">
                    {{ busyActionKey === `keyframe-${slot.clipIndex}` ? "生成中..." : "生成关键帧" }}
                  </button>
                </div>
              </div>

              <div v-if="!slot.keyframeVersions.length" class="workflow-empty workflow-empty-nested">
                还没有关键帧版本。
              </div>
              <div v-else>
                <div v-if="slot.keyframeVersions.length > 1" class="workflow-scroll-hint workflow-scroll-hint-nested">
                  左右滑动选择关键帧版本
                </div>
                <div class="clip-version-list clip-version-list-grid">
                <article v-for="version in slot.keyframeVersions" :key="version.id" class="version-card version-card-compact">
                  <div class="version-card__head">
                    <div class="version-card__meta">
                      <strong>{{ version.title }}</strong>
                      <span class="surface-chip" v-if="version.selected">当前选中</span>
                    </div>
                    <button class="btn-secondary btn-sm" type="button" :disabled="version.selected || busyActionKey === version.id" @click="handleSelectKeyframe(slot.clipIndex, version.id)">
                      {{ busyActionKey === version.id ? "处理中..." : "选中继续" }}
                    </button>
                  </div>

                  <img v-if="version.previewUrl" class="version-card__image" :src="version.previewUrl" :alt="version.title" />

                  <div class="rating-row">
                    <button
                      v-for="score in ratingOptions"
                      :key="`${version.id}-${score}`"
                      type="button"
                      class="rating-pill"
                      :class="{ 'rating-pill-active': Number(stageRatingDrafts[version.id] || version.rating || 0) === score }"
                      @click="setStageRatingDraft(version.id, score)"
                    >
                      {{ score }}
                    </button>
                  </div>

                  <textarea
                    v-model="stageNoteDrafts[version.id]"
                    class="field-textarea version-card__textarea"
                    rows="2"
                    placeholder="关键帧评价"
                  ></textarea>

                  <div class="version-card__actions">
                    <button class="btn-secondary btn-sm" type="button" :disabled="busyActionKey === `rate-${version.id}`" @click="handleRateStageVersion(version)">
                      {{ busyActionKey === `rate-${version.id}` ? "保存中..." : "保存评分" }}
                    </button>
                    <button
                      class="btn-ghost btn-sm"
                      type="button"
                      :disabled="!version.asset || busyActionKey === `reuse-${version.id}`"
                      @click="handleReuseAsset(version.asset?.id || '', version.id)"
                    >
                      {{ busyActionKey === `reuse-${version.id}` ? "复制为新工作流" : "复用" }}
                    </button>
                  </div>
                </article>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section v-else class="surface-panel workflow-panel workflow-stage-panel">
          <div class="workflow-panel__head">
            <div>
              <p class="workflow-eyebrow">Stage 3 / Finalize</p>
              <h2>视频生成模块</h2>
            </div>
            <div class="workflow-stage-panel__actions">
              <div class="stage-switch-row">
                <button
                  v-for="stage in createStageOptions"
                  :key="`detail-${stage.key}`"
                  type="button"
                  class="stage-switch-btn"
                  :class="{ 'stage-switch-btn-active': activeCreateStage === stage.key }"
                  @click="activeCreateStage = stage.key"
                >
                  {{ stage.shortLabel }}
                </button>
              </div>
              <div class="workflow-summary__actions">
                <button
                  class="btn-primary btn-sm"
                  type="button"
                  :disabled="!canFinalize || busyActionKey === 'finalize'"
                  @click="handleFinalize"
                >
                  {{ busyActionKey === "finalize" ? "拼接中..." : "生成最终结果" }}
                </button>
                <span class="surface-chip">{{ selectedWorkflow.clipSlots.length }} 个镜头</span>
              </div>
            </div>
          </div>

          <div class="workflow-stage-grid">
            <section class="surface-tile workflow-summary-card workflow-summary-card-compact">
              <h3>最终结果与评分</h3>
              <div class="rating-row">
                <button
                  v-for="score in ratingOptions"
                  :key="score"
                  type="button"
                  class="rating-pill"
                  :class="{ 'rating-pill-active': Number(workflowRatingDraft) === score }"
                  @click="workflowRatingDraft = String(score)"
                >
                  {{ score }}
                </button>
              </div>
              <textarea
                v-model="workflowRatingNoteDraft"
                class="field-textarea"
                rows="4"
                placeholder="记录最终成片评价"
              ></textarea>
              <button class="btn-secondary btn-sm" type="button" :disabled="busyActionKey === 'workflow-rating'" @click="handleRateWorkflow">
                {{ busyActionKey === "workflow-rating" ? "保存中..." : "保存评分" }}
              </button>

              <div v-if="selectedWorkflow.finalResult" class="workflow-final-compact">
                <video
                  v-if="selectedWorkflow.finalResult.previewUrl"
                  class="final-result-card__video"
                  :src="selectedWorkflow.finalResult.previewUrl"
                  controls
                  playsinline
                  preload="metadata"
                ></video>
                <div class="workflow-kv">
                  <div class="workflow-kv__row">
                    <span>标题</span>
                    <strong>{{ selectedWorkflow.finalResult.title }}</strong>
                  </div>
                  <div class="workflow-kv__row">
                    <span>时长</span>
                    <strong>{{ durationLabel(selectedWorkflow.finalResult.durationSeconds) }}</strong>
                  </div>
                </div>
                <div class="version-card__actions">
                  <a
                    class="btn-primary btn-sm"
                    :href="selectedWorkflow.finalResult.fileUrl"
                    download
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    下载结果视频
                  </a>
                </div>
              </div>
            </section>

            <section class="workflow-stage-content">
              <div v-if="!selectedWorkflow.clipSlots.length" class="workflow-empty">
                选中分镜版本后，这里会展开视频生成列表。
              </div>
              <div v-else class="clip-stack">
                <article v-for="slot in selectedWorkflow.clipSlots" :key="`video-${slot.clipIndex}`" class="surface-tile clip-card">
                  <div class="clip-card__head">
                    <div>
                      <p class="workflow-eyebrow">Clip {{ slot.clipIndex }}</p>
                      <h3>{{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}</h3>
                      <p class="clip-card__desc">{{ slot.scene || "暂无场景描述" }}</p>
                    </div>
                    <div class="clip-card__meta">
                      <span class="surface-chip">
                        {{ selectedKeyframeVersion(slot)?.title || "未选择关键帧" }}
                      </span>
                      <button
                        class="btn-primary btn-sm"
                        type="button"
                        :disabled="!selectedKeyframeVersion(slot) || busyActionKey === `video-${slot.clipIndex}`"
                        @click="handleGenerateVideo(slot.clipIndex)"
                      >
                        {{ busyActionKey === `video-${slot.clipIndex}` ? "生成中..." : "生成视频" }}
                      </button>
                    </div>
                  </div>

                  <div v-if="!slot.videoVersions.length" class="workflow-empty workflow-empty-nested">
                    还没有视频版本。
                  </div>
                  <div v-else>
                    <div v-if="slot.videoVersions.length > 1" class="workflow-scroll-hint workflow-scroll-hint-nested">
                      左右滑动选择视频版本
                    </div>
                    <div class="clip-version-list clip-version-list-grid">
                    <article v-for="version in slot.videoVersions" :key="version.id" class="version-card version-card-compact">
                      <div class="version-card__head">
                        <div class="version-card__meta">
                          <strong>{{ version.title }}</strong>
                          <span class="surface-chip" v-if="version.selected">当前选中</span>
                        </div>
                        <button class="btn-secondary btn-sm" type="button" :disabled="version.selected || busyActionKey === version.id" @click="handleSelectVideo(slot.clipIndex, version.id)">
                          {{ busyActionKey === version.id ? "处理中..." : "选中继续" }}
                        </button>
                      </div>

                      <video v-if="version.previewUrl" class="version-card__video" :src="version.previewUrl" controls playsinline preload="metadata"></video>

                      <div class="rating-row">
                        <button
                          v-for="score in ratingOptions"
                          :key="`${version.id}-${score}`"
                          type="button"
                          class="rating-pill"
                          :class="{ 'rating-pill-active': Number(stageRatingDrafts[version.id] || version.rating || 0) === score }"
                          @click="setStageRatingDraft(version.id, score)"
                        >
                          {{ score }}
                        </button>
                      </div>

                      <textarea
                        v-model="stageNoteDrafts[version.id]"
                        class="field-textarea version-card__textarea"
                        rows="2"
                        placeholder="视频评价"
                      ></textarea>

                      <div class="version-card__actions">
                        <button class="btn-secondary btn-sm" type="button" :disabled="busyActionKey === `rate-${version.id}`" @click="handleRateStageVersion(version)">
                          {{ busyActionKey === `rate-${version.id}` ? "保存中..." : "保存评分" }}
                        </button>
                        <button
                          class="btn-ghost btn-sm"
                          type="button"
                          :disabled="!version.asset || busyActionKey === `reuse-${version.id}`"
                          @click="handleReuseAsset(version.asset?.id || '', version.id)"
                        >
                          {{ busyActionKey === `reuse-${version.id}` ? "复制为新工作流" : "复用" }}
                        </button>
                        <a
                          v-if="version.downloadUrl"
                          class="btn-ghost btn-sm"
                          :href="version.downloadUrl"
                          download
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          下载
                        </a>
                      </div>
                    </article>
                    </div>
                  </div>
                </article>
              </div>
            </section>
          </div>
        </section>
      </template>

      <section v-else-if="!createComposerVisible" class="surface-panel workflow-panel workflow-empty-large workflow-empty-prompt">
        <h2>请新建工作流或选择一个工作流来查看</h2>
        <div class="workflow-empty-prompt__actions">
          <button class="btn-primary btn-sm" type="button" :disabled="creatingWorkflow || loadingOptions" @click="startCreateWorkflow">
            新建工作流
          </button>
        </div>
      </section>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchGenerationOptions } from "@/api/generation";
import { reuseMaterialAsset } from "@/api/material-assets";
import {
  createWorkflow,
  fetchWorkflow,
  fetchWorkflows,
  finalizeWorkflow,
  generateKeyframe,
  generateStoryboard,
  generateVideo,
  rateStageVersion,
  rateWorkflow,
  selectKeyframe,
  selectStoryboard,
  selectVideo,
} from "@/api/workflows";
import type {
  CreateWorkflowRequest,
  GenerationOptionsResponse,
  StageVersion,
  WorkflowClipSlot,
  WorkflowDetail,
  WorkflowSummary,
} from "@/types";

type CreateStageKey = "storyboard" | "keyframe" | "video";

interface StageFieldStep {
  key: string;
  label: string;
  description: string;
  valueLabel: string;
}

interface CreateReviewItem {
  key: string;
  label: string;
  valueLabel: string;
  configured: boolean;
  required: boolean;
}

interface CreateReviewSection {
  key: string;
  title: string;
  eyebrow: string;
  items: CreateReviewItem[];
}

const router = useRouter();
const route = useRoute();

const loadingOptions = ref(false);
const options = ref<GenerationOptionsResponse | null>(null);

const loadingWorkflows = ref(false);
const loadingDetail = ref(false);
const creatingWorkflow = ref(false);
const busyActionKey = ref("");
const workflowSearch = ref("");
const activeCreateStage = ref<CreateStageKey>("storyboard");
const createReviewFlipped = ref(false);
const createComposerVisible = ref(false);
const stageFieldIndexMap = reactive<Record<CreateStageKey, number>>({
  storyboard: 0,
  keyframe: 0,
  video: 0,
});

const listError = ref("");
const detailError = ref("");
const createError = ref("");

const workflows = ref<WorkflowSummary[]>([]);
const selectedWorkflow = ref<WorkflowDetail | null>(null);

const createStageOptions = [
  {
    key: "storyboard" as const,
    label: "文本分镜卡片",
    shortLabel: "分镜脚本",
    description: "文本模型、时长、Seed",
  },
  {
    key: "keyframe" as const,
    label: "关键帧卡片",
    shortLabel: "关键帧",
    description: "图片模型、风格、长宽比",
  },
  {
    key: "video" as const,
    label: "视频生成卡片",
    shortLabel: "视频生成",
    description: "视觉模型、视频模型、尺寸",
  },
];

const workflowRatingDraft = ref("5");
const workflowRatingNoteDraft = ref("");
const stageRatingDrafts = reactive<Record<string, string>>({});
const stageNoteDrafts = reactive<Record<string, string>>({});

const createForm = reactive({
  title: "",
  transcriptText: "",
  globalPrompt: "",
  aspectRatio: "9:16",
  stylePreset: "",
  textAnalysisModel: "",
  visionModel: "",
  imageModel: "",
  videoModel: "",
  videoSize: "",
  seed: "",
  minDurationSeconds: "5",
  maxDurationSeconds: "8",
});

const ratingOptions = [5, 4, 3, 2, 1];

const selectedWorkflowId = computed(() => {
  const workflowId = route.params.workflowId;
  return typeof workflowId === "string" ? workflowId : "";
});

const selectedWorkflowSummary = computed(() =>
  workflows.value.find((item) => item.id === selectedWorkflowId.value) ?? null
);

const filteredWorkflows = computed(() => {
  const keyword = workflowSearch.value.trim().toLowerCase();
  if (!keyword) {
    return workflows.value;
  }
  return workflows.value.filter((item) => {
    const haystack = [
      item.title,
      item.status,
      item.currentStage,
      item.aspectRatio,
    ].join(" ").toLowerCase();
    return haystack.includes(keyword);
  });
});

const activeCreateStageMeta = computed(() =>
  createStageOptions.find((item) => item.key === activeCreateStage.value) ?? createStageOptions[0]
);

const aspectRatioOptions = computed(() => options.value?.aspectRatios ?? [
  { value: "9:16", label: "9:16" },
  { value: "16:9", label: "16:9" },
]);
const stylePresetOptions = computed(() => options.value?.stylePresets ?? []);
const textModelOptions = computed(() => options.value?.textAnalysisModels ?? []);
const visionModelOptions = computed(() => options.value?.visionModels ?? []);
const imageModelOptions = computed(() => options.value?.imageModels ?? []);
const videoModelOptions = computed(() => options.value?.videoModels ?? []);
const videoSizeOptions = computed(() => options.value?.videoSizes ?? []);

const canFinalize = computed(() => {
  const workflow = selectedWorkflow.value;
  if (!workflow || !workflow.clipSlots.length) {
    return false;
  }
  return workflow.clipSlots.every((slot) => slot.videoVersions.some((version) => version.selected));
});

const activeStageSteps = computed<StageFieldStep[]>(() => {
  switch (activeCreateStage.value) {
    case "storyboard":
      return [
        {
          key: "textAnalysisModel",
          label: "文本模型",
          description: "选择这一轮文本分镜所使用的分析模型。",
          valueLabel: valueOptionLabel(textModelOptions.value, createForm.textAnalysisModel, "未设置"),
        },
        {
          key: "minDurationSeconds",
          label: "最小时长",
          description: "设定单镜头分配时长的下限。",
          valueLabel: `${createForm.minDurationSeconds || "1"} 秒`,
        },
        {
          key: "maxDurationSeconds",
          label: "最大时长",
          description: "限制单镜头时长上限，避免镜头过长。",
          valueLabel: `${createForm.maxDurationSeconds || "1"} 秒`,
        },
        {
          key: "seed",
          label: "Seed",
          description: "可选，固定随机种子以便重复生成结果。",
          valueLabel: createForm.seed === "" ? "自动" : createForm.seed,
        },
      ];
    case "keyframe":
      return [
        {
          key: "imageModel",
          label: "关键帧模型",
          description: "选择生成关键帧的图片模型。",
          valueLabel: valueOptionLabel(imageModelOptions.value, createForm.imageModel, "未设置"),
        },
        {
          key: "stylePreset",
          label: "风格预设",
          description: "控制关键帧整体画风和镜头气质。",
          valueLabel: keyOptionLabel(stylePresetOptions.value, createForm.stylePreset, "未设置"),
        },
        {
          key: "aspectRatio",
          label: "长宽比",
          description: "决定关键帧与后续视频的画面比例。",
          valueLabel: valueOptionLabel(aspectRatioOptions.value, createForm.aspectRatio, "未设置"),
        },
      ];
    default:
      return [
        {
          key: "visionModel",
          label: "视觉模型",
          description: "选择负责理解关键帧与文本上下文的视觉模型。",
          valueLabel: valueOptionLabel(visionModelOptions.value, createForm.visionModel, "未设置"),
        },
        {
          key: "videoModel",
          label: "视频模型",
          description: "选择最终视频片段的生成模型。",
          valueLabel: valueOptionLabel(videoModelOptions.value, createForm.videoModel, "未设置"),
        },
        {
          key: "videoSize",
          label: "输出尺寸",
          description: "控制视频输出分辨率与尺寸基线。",
          valueLabel: valueOptionLabel(videoSizeOptions.value, createForm.videoSize, "未设置"),
        },
      ];
  }
});

const activeStageFieldIndex = computed(() => {
  const maxIndex = Math.max(activeStageSteps.value.length - 1, 0);
  return Math.min(stageFieldIndexMap[activeCreateStage.value] ?? 0, maxIndex);
});

const currentStageField = computed(
  () => activeStageSteps.value[activeStageFieldIndex.value] ?? activeStageSteps.value[0] ?? null
);

const activeStageProgress = computed(() => {
  if (!activeStageSteps.value.length) {
    return 0;
  }
  return ((activeStageFieldIndex.value + 1) / activeStageSteps.value.length) * 100;
});

const createReviewSections = computed<CreateReviewSection[]>(() => [
  {
    key: "base",
    eyebrow: "Workflow Base",
    title: "基础信息",
    items: [
      {
        key: "title",
        label: "标题",
        valueLabel: createForm.title.trim() || "未填写",
        configured: Boolean(createForm.title.trim()),
        required: true,
      },
      {
        key: "transcriptText",
        label: "正文",
        valueLabel: createForm.transcriptText.trim() ? "已填写" : "未填写",
        configured: Boolean(createForm.transcriptText.trim()),
        required: true,
      },
      {
        key: "globalPrompt",
        label: "全局 Prompt",
        valueLabel: createForm.globalPrompt.trim() ? "已填写" : "未填写",
        configured: Boolean(createForm.globalPrompt.trim()),
        required: false,
      },
    ],
  },
  {
    key: "storyboard",
    eyebrow: "Stage 1",
    title: "文本分镜",
    items: [
      {
        key: "textAnalysisModel",
        label: "文本模型",
        valueLabel: valueOptionLabel(textModelOptions.value, createForm.textAnalysisModel, "未设置"),
        configured: Boolean(createForm.textAnalysisModel),
        required: true,
      },
      {
        key: "minDurationSeconds",
        label: "最小时长",
        valueLabel: createForm.minDurationSeconds ? `${createForm.minDurationSeconds} 秒` : "未设置",
        configured: isConfiguredNumber(createForm.minDurationSeconds),
        required: true,
      },
      {
        key: "maxDurationSeconds",
        label: "最大时长",
        valueLabel: createForm.maxDurationSeconds ? `${createForm.maxDurationSeconds} 秒` : "未设置",
        configured: isConfiguredNumber(createForm.maxDurationSeconds) && Number(createForm.maxDurationSeconds) >= Number(createForm.minDurationSeconds || 0),
        required: true,
      },
      {
        key: "seed",
        label: "Seed",
        valueLabel: createForm.seed === "" ? "自动" : createForm.seed,
        configured: true,
        required: false,
      },
    ],
  },
  {
    key: "keyframe",
    eyebrow: "Stage 2",
    title: "关键帧",
    items: [
      {
        key: "imageModel",
        label: "关键帧模型",
        valueLabel: valueOptionLabel(imageModelOptions.value, createForm.imageModel, "未设置"),
        configured: Boolean(createForm.imageModel),
        required: true,
      },
      {
        key: "stylePreset",
        label: "风格预设",
        valueLabel: keyOptionLabel(stylePresetOptions.value, createForm.stylePreset, "未设置"),
        configured: Boolean(createForm.stylePreset),
        required: true,
      },
      {
        key: "aspectRatio",
        label: "长宽比",
        valueLabel: valueOptionLabel(aspectRatioOptions.value, createForm.aspectRatio, "未设置"),
        configured: Boolean(createForm.aspectRatio),
        required: true,
      },
    ],
  },
  {
    key: "video",
    eyebrow: "Stage 3",
    title: "视频生成",
    items: [
      {
        key: "visionModel",
        label: "视觉模型",
        valueLabel: valueOptionLabel(visionModelOptions.value, createForm.visionModel, "未设置"),
        configured: Boolean(createForm.visionModel),
        required: true,
      },
      {
        key: "videoModel",
        label: "视频模型",
        valueLabel: valueOptionLabel(videoModelOptions.value, createForm.videoModel, "未设置"),
        configured: Boolean(createForm.videoModel),
        required: true,
      },
      {
        key: "videoSize",
        label: "输出尺寸",
        valueLabel: valueOptionLabel(videoSizeOptions.value, createForm.videoSize, "未设置"),
        configured: Boolean(createForm.videoSize),
        required: true,
      },
    ],
  },
]);

const createReviewRequiredItems = computed(() =>
  createReviewSections.value.flatMap((section) => section.items.filter((item) => item.required))
);

const createReviewConfiguredCount = computed(() =>
  createReviewRequiredItems.value.filter((item) => item.configured).length
);

const canSubmitCreateReview = computed(() =>
  createReviewRequiredItems.value.every((item) => item.configured)
);

function ratingLabel(value?: number | null) {
  return typeof value === "number" && value > 0 ? `${value}/5` : "未评分";
}

function valueOptionLabel<T extends { value: string; label: string }>(options: T[], value?: string | null, fallback = "-") {
  if (!value) {
    return fallback;
  }
  return options.find((item) => item.value === value)?.label || value;
}

function keyOptionLabel<T extends { key: string; label: string }>(options: T[], value?: string | null, fallback = "-") {
  if (!value) {
    return fallback;
  }
  return options.find((item) => item.key === value)?.label || value;
}

function isConfiguredNumber(value?: string | null) {
  if (value === undefined || value === null || value === "") {
    return false;
  }
  const numberValue = Number(value);
  return Number.isFinite(numberValue);
}

function durationLabel(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? `${value.toFixed(1)}s` : "-";
}

function formatDateTime(value?: string | null) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function storyboardPreview(version: StageVersion) {
  const outputSummary = version.outputSummary ?? {};
  const scriptMarkdown = typeof outputSummary.scriptMarkdown === "string" ? outputSummary.scriptMarkdown : "";
  const previewText = typeof outputSummary.previewText === "string" ? outputSummary.previewText : "";
  return scriptMarkdown || previewText || "暂无分镜预览";
}

function selectedKeyframeVersion(slot: WorkflowClipSlot) {
  return slot.keyframeVersions.find((version) => version.selected) ?? null;
}

function setStageFieldIndex(index: number) {
  const maxIndex = Math.max(activeStageSteps.value.length - 1, 0);
  stageFieldIndexMap[activeCreateStage.value] = Math.min(Math.max(index, 0), maxIndex);
}

function nextStageField() {
  if (!activeStageSteps.value.length) {
    return;
  }
  if (activeStageFieldIndex.value >= activeStageSteps.value.length - 1) {
    setStageFieldIndex(0);
    return;
  }
  setStageFieldIndex(activeStageFieldIndex.value + 1);
}

function previousStageField() {
  if (!activeStageSteps.value.length) {
    return;
  }
  setStageFieldIndex(activeStageFieldIndex.value - 1);
}

function openCreateReview() {
  createError.value = "";
  createReviewFlipped.value = true;
}

function closeCreateReview() {
  createReviewFlipped.value = false;
}

function startCreateWorkflow() {
  createError.value = "";
  createComposerVisible.value = true;
  createReviewFlipped.value = true;
}

function applyWorkflowDrafts(workflow: WorkflowDetail | null) {
  if (!workflow) {
    workflowRatingDraft.value = "5";
    workflowRatingNoteDraft.value = "";
    return;
  }
  workflowRatingDraft.value = String(workflow.effectRating ?? 5);
  workflowRatingNoteDraft.value = workflow.effectRatingNote ?? "";
  for (const version of workflow.storyboardVersions) {
    stageRatingDrafts[version.id] = String(version.rating ?? 5);
    stageNoteDrafts[version.id] = version.ratingNote ?? "";
  }
  for (const slot of workflow.clipSlots) {
    for (const version of [...slot.keyframeVersions, ...slot.videoVersions]) {
      stageRatingDrafts[version.id] = String(version.rating ?? 5);
      stageNoteDrafts[version.id] = version.ratingNote ?? "";
    }
  }
}

function openWorkflow(workflowId: string) {
  createComposerVisible.value = false;
  createReviewFlipped.value = false;
  void router.push(`/workflows/${workflowId}`);
}

function setStageRatingDraft(versionId: string, score: number) {
  stageRatingDrafts[versionId] = String(score);
}

async function loadOptions() {
  loadingOptions.value = true;
  try {
    const result = await fetchGenerationOptions();
    options.value = result;
    if (!createForm.stylePreset) {
      createForm.stylePreset = result.defaultStylePreset || result.stylePresets[0]?.key || "cinematic";
    }
    if (!createForm.textAnalysisModel) {
      createForm.textAnalysisModel = result.defaultTextAnalysisModel || result.textAnalysisModels?.[0]?.value || "";
    }
    if (!createForm.visionModel) {
      createForm.visionModel = result.defaultVisionModel || result.visionModels?.[0]?.value || "";
    }
    if (!createForm.imageModel) {
      createForm.imageModel = result.imageModels?.[0]?.value || "";
    }
    if (!createForm.videoModel) {
      createForm.videoModel = result.defaultVideoModel || result.videoModels[0]?.value || "";
    }
    if (!createForm.videoSize) {
      createForm.videoSize = result.defaultVideoSize || result.videoSizes[0]?.value || "";
    }
    if (!createForm.aspectRatio) {
      createForm.aspectRatio = (result.defaultAspectRatio as "9:16" | "16:9" | null) || "9:16";
    }
  } finally {
    loadingOptions.value = false;
  }
}

async function loadWorkflows() {
  loadingWorkflows.value = true;
  listError.value = "";
  try {
    workflows.value = await fetchWorkflows();
  } catch (error) {
    listError.value = error instanceof Error ? error.message : "工作流列表加载失败";
  } finally {
    loadingWorkflows.value = false;
  }
}

async function loadWorkflowDetail(workflowId: string) {
  loadingDetail.value = true;
  detailError.value = "";
  try {
    selectedWorkflow.value = await fetchWorkflow(workflowId);
    applyWorkflowDrafts(selectedWorkflow.value);
  } catch (error) {
    detailError.value = error instanceof Error ? error.message : "工作流详情加载失败";
    selectedWorkflow.value = null;
  } finally {
    loadingDetail.value = false;
  }
}

async function reloadCurrentWorkflow() {
  if (selectedWorkflowId.value) {
    await loadWorkflowDetail(selectedWorkflowId.value);
    await loadWorkflows();
  }
}

function buildCreatePayload(): CreateWorkflowRequest {
  return {
    title: createForm.title.trim(),
    transcriptText: createForm.transcriptText.trim() || null,
    globalPrompt: createForm.globalPrompt.trim() || null,
    aspectRatio: createForm.aspectRatio as "9:16" | "16:9",
    stylePreset: createForm.stylePreset || null,
    textAnalysisModel: createForm.textAnalysisModel,
    visionModel: createForm.visionModel,
    imageModel: createForm.imageModel,
    videoModel: createForm.videoModel,
    videoSize: createForm.videoSize || null,
    seed: createForm.seed === "" ? null : Number(createForm.seed),
    minDurationSeconds: createForm.minDurationSeconds === "" ? null : Number(createForm.minDurationSeconds),
    maxDurationSeconds: createForm.maxDurationSeconds === "" ? null : Number(createForm.maxDurationSeconds),
  };
}

async function handleCreateWorkflow() {
  createError.value = "";
  creatingWorkflow.value = true;
  try {
    const workflow = await createWorkflow(buildCreatePayload());
    createForm.title = "";
    createForm.transcriptText = "";
    createForm.globalPrompt = "";
    createForm.seed = "";
    createComposerVisible.value = false;
    createReviewFlipped.value = false;
    await loadWorkflows();
    openWorkflow(workflow.id);
  } catch (error) {
    createError.value = error instanceof Error ? error.message : "创建工作流失败";
    createReviewFlipped.value = false;
  } finally {
    creatingWorkflow.value = false;
  }
}

async function runAndRefresh(actionKey: string, runner: () => Promise<WorkflowDetail>) {
  busyActionKey.value = actionKey;
  detailError.value = "";
  try {
    selectedWorkflow.value = await runner();
    applyWorkflowDrafts(selectedWorkflow.value);
    await loadWorkflows();
  } catch (error) {
    detailError.value = error instanceof Error ? error.message : "操作失败";
  } finally {
    busyActionKey.value = "";
  }
}

async function handleGenerateStoryboard() {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh("storyboard", () => generateStoryboard(selectedWorkflowId.value));
}

async function handleSelectStoryboard(versionId: string) {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh(versionId, () => selectStoryboard(selectedWorkflowId.value, versionId));
}

async function handleGenerateKeyframe(clipIndex: number) {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh(`keyframe-${clipIndex}`, () => generateKeyframe(selectedWorkflowId.value, clipIndex));
}

async function handleSelectKeyframe(clipIndex: number, versionId: string) {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh(versionId, () => selectKeyframe(selectedWorkflowId.value, clipIndex, versionId));
}

async function handleGenerateVideo(clipIndex: number) {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh(`video-${clipIndex}`, () => generateVideo(selectedWorkflowId.value, clipIndex));
}

async function handleSelectVideo(clipIndex: number, versionId: string) {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh(versionId, () => selectVideo(selectedWorkflowId.value, clipIndex, versionId));
}

async function handleFinalize() {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh("finalize", () => finalizeWorkflow(selectedWorkflowId.value));
}

async function handleRateWorkflow() {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh("workflow-rating", () =>
    rateWorkflow(selectedWorkflowId.value, {
      effectRating: Number(workflowRatingDraft.value || 5),
      effectRatingNote: workflowRatingNoteDraft.value.trim() || null,
    })
  );
}

async function handleRateStageVersion(version: StageVersion) {
  if (!selectedWorkflowId.value) {
    return;
  }
  const actionKey = `rate-${version.id}`;
  await runAndRefresh(actionKey, () =>
    rateStageVersion(selectedWorkflowId.value, version.id, {
      effectRating: Number(stageRatingDrafts[version.id] || version.rating || 5),
      effectRatingNote: stageNoteDrafts[version.id]?.trim() || null,
    })
  );
}

async function handleReuseAsset(assetId: string, versionId: string) {
  if (!assetId) {
    return;
  }
  busyActionKey.value = `reuse-${versionId}`;
  detailError.value = "";
  try {
    const workflow = await reuseMaterialAsset(assetId, { mode: "clone" });
    await loadWorkflows();
    openWorkflow(workflow.id);
  } catch (error) {
    detailError.value = error instanceof Error ? error.message : "素材复用失败";
  } finally {
    busyActionKey.value = "";
  }
}

watch(
  () => selectedWorkflowId.value,
  (workflowId) => {
    if (!workflowId) {
      selectedWorkflow.value = null;
      return;
    }
    void loadWorkflowDetail(workflowId);
  },
  { immediate: true }
);

watch(
  () => createForm.minDurationSeconds,
  (value) => {
    const minDuration = Number(value);
    const maxDuration = Number(createForm.maxDurationSeconds);
    if (Number.isFinite(minDuration) && Number.isFinite(maxDuration) && minDuration > maxDuration) {
      createForm.maxDurationSeconds = value;
    }
  }
);

onMounted(async () => {
  await loadOptions();
  await loadWorkflows();
});
</script>

<style scoped>
.workflow-view {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 20px;
  height: 100%;
  min-height: 0;
}

.workflow-rail,
.workflow-main {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: 0;
}

.workflow-rail {
  overflow: hidden;
}

.workflow-rail-flip-shell {
  flex: 1 1 auto;
  min-height: 0;
  perspective: 2200px;
}

.workflow-rail-flip {
  display: grid;
  min-height: 100%;
  transform-style: preserve-3d;
  transition: transform 0.72s cubic-bezier(0.22, 0.8, 0.2, 1);
}

.workflow-rail-flip-active {
  transform: rotateY(180deg);
}

.workflow-rail-flip__face {
  grid-area: 1 / 1;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  transform-style: preserve-3d;
}

.workflow-rail-flip__face-front {
  transform: rotateY(0deg);
}

.workflow-rail-flip__face-back {
  transform: rotateY(180deg);
}

.workflow-rail-flip__face-back.workflow-rail-panel {
  padding-top: 18px;
}

.workflow-rail-flip-active .workflow-rail-flip__face-front {
  pointer-events: none;
}

.workflow-rail-flip:not(.workflow-rail-flip-active) .workflow-rail-flip__face-back {
  pointer-events: none;
}

.workflow-panel {
  padding: 22px;
  min-height: 0;
}

.workflow-rail-panel {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: calc(100vh - 132px);
  min-height: 0;
  max-height: calc(100vh - 132px);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-top: 28px;
}

.workflow-rail__hero {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.workflow-rail__title-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.workflow-rail__title-row h2 {
  margin: 0;
}

.workflow-rail__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.workflow-rail__actions-inline {
  justify-content: flex-start;
}

.workflow-rail__stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.workflow-mini-stat {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
}

.workflow-mini-stat span {
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.58);
}

.workflow-mini-stat strong {
  font-size: 1rem;
  line-height: 1.4;
}

.workflow-rail__search {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.workflow-rail__search span {
  font-size: 0.84rem;
  color: rgba(255, 255, 255, 0.7);
}

.workflow-list-shell {
  flex: 1 0 auto;
  min-height: 0;
  overflow: visible;
  padding-right: 4px;
}

.workflow-create-shell {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 14px 24px 24px;
  border-radius: 28px;
  background:
    radial-gradient(circle at top right, rgba(89, 208, 255, 0.08), transparent 28%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.03));
}

.workflow-main {
  overflow-y: auto;
  padding-right: 4px;
}

.workflow-main > * {
  flex: 0 0 auto;
}

.workflow-create-shell__grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
}

.workflow-create-canvas {
  display: block;
}

.workflow-review-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-height: 100%;
}

.workflow-review-card__head {
  align-items: flex-start;
}

.workflow-review-card-rail {
  height: 100%;
}

.workflow-review-card__status {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.workflow-review-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.workflow-review-grid-rail {
  grid-template-columns: 1fr;
  overflow-y: auto;
  padding-right: 4px;
}

.workflow-review-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
}

.workflow-review-section__head h4 {
  margin: 6px 0 0;
}

.workflow-review-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.workflow-review-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(5, 7, 11, 0.38);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.workflow-review-item strong {
  display: block;
  margin-bottom: 6px;
}

.workflow-review-item p {
  margin: 0;
  color: rgba(255, 255, 255, 0.62);
  line-height: 1.5;
}

.workflow-review-item__meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.workflow-review-chip-success {
  border-color: rgba(88, 212, 136, 0.38);
  background: rgba(88, 212, 136, 0.12);
  color: #d5ffe2;
}

.workflow-review-chip-warning {
  border-color: rgba(255, 180, 92, 0.46);
  background: rgba(255, 180, 92, 0.14);
  color: #ffe1b1;
}

.workflow-review-chip-muted {
  border-color: rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.58);
}

.workflow-review-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}

.workflow-review-actions-rail {
  margin-top: auto;
}

.workflow-stage-create {
  display: grid;
  grid-template-columns: 1fr;
  grid-template-areas:
    "base"
    "focus";
  gap: 16px;
  align-items: start;
}

.stage-config-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 18px;
  border-radius: 22px;
  background:
    radial-gradient(circle at top right, rgba(255, 180, 92, 0.12), transparent 40%),
    rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.stage-config-card--base {
  grid-area: base;
}

.stage-config-card--focus {
  grid-area: focus;
}

.stage-config-card__head {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stage-config-card__title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.stage-config-card__head h3 {
  margin: 0;
  font-size: 1.08rem;
}

.stage-progress-copy {
  margin: 8px 0 0;
  max-width: 620px;
  color: rgba(255, 255, 255, 0.66);
  line-height: 1.6;
}

.stage-config-card__head :deep(.surface-chip) {
  width: fit-content;
}

.stage-switch-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
}

.stage-switch-btn {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.76);
  font-size: 0.88rem;
  font-weight: 700;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease, color 0.2s ease;
}

.stage-switch-btn:hover,
.stage-switch-btn-active {
  border-color: rgba(255, 180, 92, 0.54);
  background: rgba(255, 180, 92, 0.12);
  color: #fff0d2;
  transform: translateY(-1px);
}

.stage-config-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.stage-config-fields--single {
  grid-template-columns: minmax(280px, 0.92fr) minmax(0, 1.08fr);
  grid-template-areas:
    "title title"
    "prompt body";
  align-items: start;
}

.stage-config-field-title {
  grid-area: title;
}

.stage-config-field-body {
  grid-area: body;
}

.stage-config-field-prompt {
  grid-area: prompt;
}

.stage-config-card--focus {
  min-width: 0;
}

.stage-progress-form {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(220px, 0.7fr);
  gap: 16px;
  align-items: start;
}

.stage-progress-form__rail,
.stage-progress-form__panel,
.stage-progress-form__summary {
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
}

.stage-progress-form__rail {
  grid-column: 1 / -1;
  padding: 16px;
}

.stage-progress-form__bar {
  position: relative;
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.stage-progress-form__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(255, 180, 92, 0.92), rgba(89, 208, 255, 0.82));
}

.stage-progress-form__steps {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.stage-progress-form__step {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 10px 12px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.78);
  text-align: left;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.stage-progress-form__step span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 0.82rem;
  font-weight: 700;
}

.stage-progress-form__step-active,
.stage-progress-form__step:hover {
  border-color: rgba(255, 180, 92, 0.56);
  background: rgba(255, 180, 92, 0.12);
  transform: translateY(-1px);
}

.stage-progress-form__step-done span,
.stage-progress-form__step-active span {
  background: rgba(255, 180, 92, 0.2);
  color: #fff0d2;
}

.stage-progress-form__panel {
  padding: 18px;
}

.stage-progress-form__panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 18px;
}

.stage-progress-form__panel-head h4 {
  margin: 6px 0 8px;
  font-size: 1.06rem;
}

.stage-progress-form__panel-head p:last-child {
  margin: 0;
  color: rgba(255, 255, 255, 0.64);
  line-height: 1.6;
}

.stage-progress-form__field {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stage-progress-form__field > span {
  color: rgba(255, 255, 255, 0.74);
  font-size: 0.9rem;
}

.stage-progress-form__field-slider {
  max-width: 520px;
}

.stage-option-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.stage-option-grid--compact {
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
}

.stage-option-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 84px;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.82);
  text-align: left;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.stage-option-card span {
  color: rgba(255, 255, 255, 0.56);
  font-size: 0.82rem;
  line-height: 1.5;
}

.stage-option-card:hover,
.stage-option-card-active {
  border-color: rgba(255, 180, 92, 0.56);
  background: rgba(255, 180, 92, 0.12);
  transform: translateY(-1px);
}

.stage-slider__range {
  width: 100%;
  accent-color: rgba(255, 180, 92, 0.96);
}

.stage-slider__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.stage-slider__number {
  width: 120px;
}

.stage-toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.stage-toggle-chip {
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.76);
  transition: border-color 0.2s ease, background 0.2s ease;
}

.stage-toggle-chip-active,
.stage-toggle-chip:hover {
  border-color: rgba(255, 180, 92, 0.56);
  background: rgba(255, 180, 92, 0.12);
  color: #fff0d2;
}

.stage-progress-form__actions {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 18px;
}

.stage-progress-form__summary {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
}

.stage-summary-card {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.8);
  text-align: left;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}

.stage-summary-card span {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.54);
}

.stage-summary-card-active,
.stage-summary-card:hover {
  border-color: rgba(89, 208, 255, 0.44);
  background: rgba(89, 208, 255, 0.1);
  transform: translateY(-1px);
}

.stage-config-field-body .field-textarea,
.stage-config-field-prompt .field-textarea {
  min-height: 220px;
}

.workflow-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.workflow-panel__head h2 {
  margin: 6px 0 0;
  font-size: 1.2rem;
  font-weight: 700;
}

.workflow-panel__head-spread {
  align-items: center;
}

.workflow-stage-panel__actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.workflow-eyebrow {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.56);
}

.workflow-form__grid,
.workflow-list,
.workflow-summary-grid,
.clip-stack,
.clip-version-list,
.version-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.workflow-form {
  gap: 14px;
}

.workflow-form__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.workflow-form__footer {
  display: flex;
  justify-content: flex-end;
}

.workflow-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.workflow-field-span-2 {
  grid-column: span 2;
}

.workflow-field span {
  font-size: 0.86rem;
  color: rgba(255, 255, 255, 0.72);
}

.workflow-submit {
  justify-content: center;
}

.workflow-list__item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  border-radius: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  text-align: left;
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

.workflow-list__item:hover,
.workflow-list__item-active {
  border-color: rgba(255, 180, 92, 0.5);
  background: rgba(255, 180, 92, 0.08);
  transform: translateY(-1px);
}

.workflow-list__top,
.workflow-list__meta,
.workflow-summary__meta,
.workflow-summary__actions,
.rating-row,
.tag-list,
.version-card__actions,
.clip-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.workflow-list__meta,
.clip-card__desc {
  color: rgba(255, 255, 255, 0.68);
  font-size: 0.88rem;
}

.workflow-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
}

.workflow-banner-error,
.workflow-error {
  color: #ffb4b4;
}

.workflow-empty {
  padding: 28px 18px;
  border-radius: 20px;
  border: 1px dashed rgba(255, 255, 255, 0.14);
  color: rgba(255, 255, 255, 0.64);
  text-align: center;
}

.workflow-empty-large {
  padding: 64px 24px;
}

.workflow-empty-large h2 {
  margin: 8px 0 10px;
}

.workflow-empty-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-align: center;
}

.workflow-empty-prompt p:not(.workflow-eyebrow) {
  max-width: 520px;
  margin: 0;
  color: rgba(255, 255, 255, 0.64);
  line-height: 1.7;
}

.workflow-empty-prompt__actions {
  display: flex;
  justify-content: center;
  margin-top: 8px;
}

.workflow-empty-nested {
  padding: 18px 14px;
}

.workflow-scroll-hint {
  margin-bottom: 10px;
  font-size: 0.84rem;
  color: rgba(255, 255, 255, 0.54);
}

.workflow-scroll-hint-nested {
  margin-bottom: 12px;
}

.workflow-summary-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
}

.workflow-summary-card h3,
.clip-column__head h4,
.version-card h3 {
  margin: 0;
}

.workflow-stage-panel {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 24px;
  border-radius: 26px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.028));
}

.workflow-stage-grid {
  display: grid;
  grid-template-columns: minmax(220px, 248px) minmax(0, 1fr);
  gap: 18px;
  min-height: 0;
}

.workflow-stage-content {
  min-width: 0;
  min-height: 0;
}

.workflow-summary-card-compact {
  position: sticky;
  top: 0;
  max-height: 72vh;
  overflow-y: auto;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.055), rgba(255, 255, 255, 0.035));
}

.workflow-kv {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.workflow-kv__row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 0.92rem;
}

.workflow-kv__row span {
  color: rgba(255, 255, 255, 0.6);
}

.workflow-note-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.04);
}

.workflow-note-block span {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.52);
}

.workflow-note-block p {
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.6;
}

.version-grid {
  display: flex;
  flex-direction: row;
  gap: 16px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 2px 6px 10px 0;
  scroll-snap-type: x proximity;
  overscroll-behavior-x: contain;
  scrollbar-gutter: stable both-edges;
}

.version-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  flex: 0 0 min(560px, calc(100% - 8px));
  min-width: 0;
  scroll-snap-align: start;
}

.version-card-compact {
  padding: 16px;
}

.version-card__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.version-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.version-card__text {
  margin: 0;
  padding: 14px;
  min-height: 220px;
  max-height: 320px;
  overflow: auto;
  border-radius: 16px;
  background: rgba(4, 6, 10, 0.72);
  color: rgba(255, 255, 255, 0.84);
  font-size: 0.84rem;
  line-height: 1.6;
  white-space: pre-wrap;
}

.version-card__textarea {
  min-height: 86px;
}

.version-card__image,
.version-card__video,
.final-result-card__video {
  width: 100%;
  border-radius: 16px;
  background: rgba(0, 0, 0, 0.35);
}

.clip-card {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.03));
}

.clip-card__head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
}

.clip-stack {
  gap: 18px;
}

.clip-version-list-grid {
  display: flex;
  flex-direction: row;
  gap: 14px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 2px 6px 10px 0;
  scroll-snap-type: x proximity;
  overscroll-behavior-x: contain;
  scrollbar-gutter: stable both-edges;
}

.clip-card__columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.clip-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.clip-column__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.clip-version-list-grid .version-card {
  flex: 0 0 min(360px, calc(100% - 8px));
}

.rating-pill,
.tag-chip {
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  font-size: 0.82rem;
}

.rating-pill-active {
  border-color: rgba(255, 180, 92, 0.72);
  background: rgba(255, 180, 92, 0.16);
  color: #ffe1b1;
}

.workflow-final-compact {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding-top: 6px;
}

.final-result-card {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) 320px;
  gap: 18px;
}

.final-result-card__meta {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

@media (max-width: 1280px) {
  .workflow-view {
    grid-template-columns: 1fr;
  }

  .workflow-rail-panel {
    position: static;
    height: auto;
    min-height: auto;
    max-height: none;
    overflow: visible;
    padding-top: 22px;
  }

  .workflow-form__grid,
  .workflow-create-shell__grid,
  .workflow-stage-grid,
  .workflow-review-grid,
  .stage-progress-form,
  .clip-card__columns,
  .final-result-card {
    grid-template-columns: 1fr;
  }

  .workflow-stage-create {
    grid-template-columns: 1fr;
    grid-template-areas:
      "base"
      "focus"
      "submit";
  }

  .workflow-summary-card-compact {
    position: static;
    max-height: none;
  }

  .stage-config-fields--single {
    grid-template-columns: 1fr;
    grid-template-areas:
      "title"
      "body"
      "prompt";
  }

  .stage-config-card__title-row {
    flex-direction: column;
  }

  .stage-progress-form__summary,
  .stage-progress-form__panel,
  .stage-progress-form__rail {
    grid-column: auto;
  }

  .stage-switch-row {
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .workflow-rail__stats {
    grid-template-columns: 1fr;
  }

  .stage-slider__meta,
  .stage-progress-form__actions,
  .workflow-stage-panel__actions,
  .workflow-review-item,
  .workflow-review-actions,
  .workflow-panel__head,
  .clip-card__head {
    flex-direction: column;
    align-items: stretch;
  }

  .workflow-field-span-2 {
    grid-column: span 1;
  }
}
</style>
