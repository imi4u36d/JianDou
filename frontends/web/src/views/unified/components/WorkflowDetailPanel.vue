<template>
  <section class="workflow-canvas-main">
    <div v-if="loadingDetail" class="surface-panel workflow-empty workflow-empty-large">加载中</div>
    <div v-else-if="!selectedWorkflow" class="surface-panel workflow-empty workflow-empty-large">
      <h3>选择工作流</h3>
    </div>

    <template v-else>
      <header class="workflow-canvas-header">
        <div class="workflow-canvas-header__body">
          <h2>{{ selectedWorkflow.title }}</h2>
          <div class="workflow-canvas-header__summary">
            <div class="workflow-summary__parameter-tags">
              <span v-for="item in workflowParameterTags" :key="item.label" class="workflow-summary-tag" :title="`${item.label}：${item.value}`">
                <span class="workflow-summary-tag__label" aria-hidden="true">{{ item.label }}</span>
                <strong class="workflow-summary-tag__value">{{ item.value }}</strong>
              </span>
            </div>
            <button
              class="btn-secondary btn-sm"
              type="button"
              :class="{ 'workflow-settings-btn-active': workflowSettingsOpen }"
              @click="workflowSettingsOpen = !workflowSettingsOpen"
            >
              <IconSettings size="sm" />
            </button>
          </div>
          <section v-if="workflowSettingsOpen" class="workflow-header-settings">
            <form class="workflow-settings-stack" @submit.prevent="handleUpdateWorkflowSettings">
              <label class="workflow-field"><span>文本模型</span><AppSelect v-model="workflowSettingsDraft.textAnalysisModel" :options="textModelSelectOptions" /></label>
              <label class="workflow-field"><span>关键帧模型</span><AppSelect v-model="workflowSettingsDraft.imageModel" :options="imageModelSelectOptions" /></label>
              <label class="workflow-field"><span>视频模型</span><AppSelect v-model="workflowSettingsDraft.videoModel" :options="videoModelSelectOptions" /></label>
              <label class="workflow-field"><span>视觉风格</span><AppSelect v-model="workflowSettingsDraft.stylePreset" :options="stylePresetSelectOptions" /></label>
              <label class="workflow-field"><span>画幅</span><AppSelect v-model="workflowSettingsDraft.aspectRatio" :options="aspectRatioSelectOptions" /></label>
              <label class="workflow-field"><span>输出尺寸</span><AppSelect v-model="workflowSettingsDraft.videoSize" :options="workflowSettingsVideoSizeSelectOptions" /></label>
              <p v-if="workflowSettingsValidationMessage" class="workflow-error">{{ workflowSettingsValidationMessage }}</p>
              <div class="workflow-header-settings__actions">
                <button class="btn-secondary btn-sm" type="button" @click="workflowSettingsOpen = false">收起</button>
                <button class="btn-primary btn-sm" type="submit" :disabled="busyActionKey === 'workflow-settings' || Boolean(workflowSettingsValidationMessage)">
                  <IconLoading v-if="busyActionKey === 'workflow-settings'" size="xs" />
                  <span>{{ busyActionKey === "workflow-settings" ? "保存中" : "保存" }}</span>
                </button>
              </div>
            </form>
          </section>
        </div>
      </header>

      <!-- ── AutoPilot Control Bar ── -->
      <template v-if="executionMode === 'auto' || executionMode === 'manual'">
        <!-- Running state -->
        <div v-if="autoPilot.isRunning.value" class="autopilot-bar autopilot-bar-running surface-panel">
          <div class="autopilot-bar__status">
            <span class="autopilot-bar__dot autopilot-bar__dot-running"></span>
            <strong>{{ autoPilot.currentTask.value || '自动执行中' }}</strong>
          </div>
          <div class="autopilot-bar__log">
            <div
              v-for="(entry) in recentLog"
              :key="entry.id"
              class="autopilot-log-entry autopilot-log-entry--active"
            >
              <span :class="['autopilot-log-entry__stage', entry.stateKey ? `autopilot-log-entry__stage--${entry.stateKey}` : '']">{{ entry.stage }}</span>
              <span class="autopilot-log-entry__message">{{ entry.message }}</span>
            </div>
          </div>
          <div class="autopilot-bar__actions">
            <button class="btn-secondary btn-sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.pauseAutoPilot()">
              <span>⏸ 暂停</span>
            </button>
            <button class="btn-secondary btn-sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.terminateAutoPilot()">
              <span>⏹ 终止</span>
            </button>
          </div>
        </div>

        <!-- Queued state -->
        <div v-else-if="autoPilot.isQueued.value" class="autopilot-bar autopilot-bar-queued surface-panel">
          <div class="autopilot-bar__status">
            <span class="autopilot-bar__dot autopilot-bar__dot-queued"></span>
            <strong>排队中</strong>
            <span v-if="selectedWorkflow?.queuePosition" class="autopilot-bar__queue-info">
              前面还有 {{ selectedWorkflow.queuePosition - 1 }} 个任务
            </span>
          </div>
          <div class="autopilot-bar__log">
            <div v-for="(entry) in recentLog" :key="entry.id" class="autopilot-log-entry autopilot-log-entry--active">
              <span :class="['autopilot-log-entry__stage', entry.stateKey ? `autopilot-log-entry__stage--${entry.stateKey}` : '']">{{ entry.stage }}</span>
              <span class="autopilot-log-entry__message">{{ entry.message }}</span>
            </div>
          </div>
          <div class="autopilot-bar__actions">
            <button class="btn-secondary btn-sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.terminateAutoPilot()">
              <span>取消</span>
            </button>
          </div>
        </div>

        <!-- Paused state -->
        <div v-else-if="autoPilot.isPaused.value" class="autopilot-bar autopilot-bar-paused surface-panel">
          <div class="autopilot-bar__status">
            <span class="autopilot-bar__dot autopilot-bar__dot-paused"></span>
            <strong>已暂停</strong>
          </div>
          <div class="autopilot-bar__log">
            <div v-for="(entry) in recentLog" :key="entry.id" class="autopilot-log-entry">
              <span :class="['autopilot-log-entry__stage', entry.stateKey ? `autopilot-log-entry__stage--${entry.stateKey}` : '']">{{ entry.stage }}</span>
              <span class="autopilot-log-entry__message">{{ entry.message }}</span>
            </div>
          </div>
          <div class="autopilot-bar__actions">
            <button class="btn-primary btn-sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.resumeAutoPilot()">
              <span>▶ 继续自动执行</span>
            </button>
            <button class="btn-secondary btn-sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.terminateAutoPilot()">
              <span>✏ 切换为手动模式</span>
            </button>
          </div>
        </div>

        <!-- Failed state -->
        <div v-else-if="autoPilot.isFailed.value" class="autopilot-bar autopilot-bar-failed surface-panel">
          <div class="autopilot-bar__status">
            <span class="autopilot-bar__dot autopilot-bar__dot-failed"></span>
            <strong>自动执行失败</strong>
          </div>
          <div class="autopilot-bar__log">
            <div v-for="(entry) in recentLog" :key="entry.id" class="autopilot-log-entry">
              <span :class="['autopilot-log-entry__stage', entry.stateKey ? `autopilot-log-entry__stage--${entry.stateKey}` : '']">{{ entry.stage }}</span>
              <span class="autopilot-log-entry__message">{{ entry.message }}</span>
            </div>
          </div>
          <div class="autopilot-bar__actions">
            <button class="btn-primary btn-sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.resumeAutoPilot()">
              <span>重试</span>
            </button>
          </div>
        </div>

        <!-- Idle state (not yet started or just created) -->
        <div v-else class="autopilot-bar autopilot-bar-idle surface-panel">
          <div class="autopilot-bar__status">
            <strong>自动执行就绪</strong>
            <span class="autopilot-bar__hint">点击启动后，工作流将自动依次执行各阶段。</span>
          </div>
          <div class="autopilot-bar__log">
            <div v-for="(entry) in recentLog" :key="entry.id" class="autopilot-log-entry">
              <span :class="['autopilot-log-entry__stage', entry.stateKey ? `autopilot-log-entry__stage--${entry.stateKey}` : '']">{{ entry.stage }}</span>
              <span class="autopilot-log-entry__message">{{ entry.message }}</span>
            </div>
          </div>
          <div class="autopilot-bar__actions">
            <button class="btn-primary btn-sm" type="button" :disabled="autoPilot.busy.value" @click="autoPilot.startAutoPilot()">
              <span>▶ 启动自动执行</span>
            </button>
          </div>
        </div>
      </template>

      <WorkflowStagePipeline :stages="canvasStageItems" :active-stage="activeCanvasStage" @switch="switchCanvasStage" />

      <section class="workflow-canvas-grid">
        <main class="workflow-stage-canvas">
          <!-- ── 分镜脚本 ── -->
          <section v-if="activeCanvasStage === 'storyboard'" class="workflow-stage-board storyboard-board">
            <div class="stage-board__head">
              <h3>分镜脚本</h3>
              <div class="stage-board__head-actions">
                <button
                  v-if="(selectedWorkflow.storyboardVersions ?? []).length"
                  class="btn-secondary btn-sm workflow-menu-danger"
                  type="button"
                  :disabled="busyActionKey === 'clear-storyboard-versions'"
                  @click="handleClearStageVersions('storyboard')"
                >
                  <IconLoading v-if="busyActionKey === 'clear-storyboard-versions'" size="xs" />
                  <IconDelete v-else size="xs" />
                  <span>{{ busyActionKey === 'clear-storyboard-versions' ? '清空中' : '清空分镜版本' }}</span>
                </button>
                <button class="btn-primary btn-sm" type="button" :disabled="busyActionKey === 'storyboard'" @click="handleGenerateStoryboard">
                  <IconLoading v-if="busyActionKey === 'storyboard'" size="xs" />
                  <span>{{ busyActionKey === "storyboard" ? "生成中" : "生成" }}</span>
                </button>
              </div>
            </div>
            <div v-if="!(selectedWorkflow.storyboardVersions ?? []).length" class="workflow-empty workflow-empty-large">暂无分镜版本</div>
            <div v-else class="storyboard-layout">
              <article class="storyboard-preview-card">
                <div class="version-switcher">
                  <div class="version-switcher__tabs">
                    <article
                      v-for="version in selectedWorkflow.storyboardVersions"
                      :key="version.id"
                      class="version-switcher__tab"
                      :class="{ 'version-switcher__tab-active': selectedStoryboardVersion?.id === version.id }"
                    >
                      <button type="button" class="version-switcher__tab-main" @click="setPreviewStoryboardVersion(version.id)">
                        <span class="compact-version-card__badge">V{{ version.versionNo }}</span>
                        <strong>{{ stageVersionDisplayTitle(version) }}</strong>
                        <span class="compact-version-card__status">{{ version.selected ? "当前" : stageStatusLabel(version.status) }}</span>
                      </button>
                      <div class="workflow-more-menu compact-version-menu">
                        <button type="button" class="workflow-more-menu__trigger" aria-label="版本操作" :popovertarget="`wfd-vsm-${version.id}`"><IconMore size="sm" /></button>
                        <div :id="`wfd-vsm-${version.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionVersionMenu">
                          <button type="button" :disabled="version.selected || busyActionKey === version.id" @click="handleSelectStoryboard(version.id)"><IconCheck size="xs" /><span>{{ version.selected ? "当前" : "设为当前" }}</span></button>
                          <button type="button" :disabled="!version.asset || busyActionKey === `reuse-${version.id}`" @click="handleReuseAsset(version.asset?.id || '', version.id)"><IconPlus size="xs" /><span>复用</span></button>
                          <button type="button" class="workflow-menu-danger" :disabled="busyActionKey === `delete-${version.id}`" @click="handleDeleteStageVersion(version)"><IconDelete size="xs" /><span>删除</span></button>
                        </div>
                      </div>
                    </article>
                  </div>
                </div>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <div v-if="selectedStoryboardVersion" class="version-card__markdown storyboard-preview-markdown" v-html="storyboardPreviewHtml(selectedStoryboardVersion)"></div>
                <div v-if="selectedStoryboardVersion" class="storyboard-adjust-panel">
                  <input v-model="storyboardAdjustmentDrafts[selectedStoryboardVersion.id]" class="field-input storyboard-adjust-panel__input" type="text" placeholder="调整要求，可留空" />
                  <button class="btn-primary btn-sm storyboard-adjust-panel__button" type="button" :disabled="busyActionKey === `storyboard-adjust-${selectedStoryboardVersion.id}` || selectedStoryboardVersion.status !== 'SUCCEEDED'" @click="handleAdjustStoryboard(selectedStoryboardVersion.id)">
                    <IconLoading v-if="busyActionKey === `storyboard-adjust-${selectedStoryboardVersion.id}`" size="xs" />
                    <span>{{ busyActionKey === `storyboard-adjust-${selectedStoryboardVersion.id}` ? "调整中" : "调整" }}</span>
                  </button>
                </div>
              </article>
            </div>
          </section>

          <!-- ── 角色三视图 ── -->
          <section v-else-if="activeCanvasStage === 'character'" class="workflow-stage-board character-board">
            <div class="stage-board__head">
              <h3>角色三视图</h3>
              <div class="stage-board__meta">
                <span class="surface-chip">{{ workflowCharacterSheets.length }} 个角色</span>
                <button class="btn-primary btn-sm" type="button" :disabled="!missingCharacterSheets.length || busyActionKey === 'character-missing'" @click="handleGenerateMissingCharacterSheets">
                  <IconLoading v-if="busyActionKey === 'character-missing'" size="xs" />
                  <span>{{ busyActionKey === "character-missing" ? "补齐中" : "补齐" }}</span>
                </button>
              </div>
            </div>
            <div v-if="!workflowCharacterSheets.length" class="workflow-empty workflow-empty-nested">暂无角色三视图</div>
            <div v-else class="character-strip__list">
              <article v-for="sheet in workflowCharacterSheets" :key="characterSheetKey(sheet)" class="character-mini-card">
                <div class="character-mini-card__head"><strong>{{ characterSheetTitle(sheet) }}</strong></div>
                <button type="button" class="character-mini-card__summary" @click="openCharacterSummaryPreview(sheet)">
                  <span class="character-mini-card__summary-label">角色定义</span>
                  <p>{{ characterSheetAppearanceSummary(sheet) }}</p>
                </button>
                <div v-if="previewCharacterSheetVersion(sheet)" class="character-mini-card__frames">
                  <button
                    v-for="frame in characterSheetPreviewFrames(previewCharacterSheetVersion(sheet)!)"
                    :key="`${characterSheetKey(sheet)}-${frame.role}`"
                    type="button"
                    class="character-mini-frame"
                    @click="openImagePreview(frame.url, `${characterSheetTitle(sheet)} ${frame.label}`)"
                  >
                    <img v-if="isPreviewImageAvailable(frame.url)" :src="frame.url" :alt="`${characterSheetTitle(sheet)} ${frame.label}`" @error="markPreviewImageFailed(frame.url)" />
                    <span v-else class="workflow-image-fallback" aria-hidden="true"><IconEmpty size="sm" /></span>
                    <span>{{ frame.label }}</span>
                  </button>
                </div>
                <div class="character-mini-card__actions">
                  <button class="btn-secondary btn-sm" type="button" :disabled="characterSheetClipIndex(sheet) === null" @click="openCharacterAssetPicker(sheet)">
                    <IconSearch size="xs" /><span>素材</span>
                  </button>
                </div>
                <section v-if="isCharacterAssetPickerOpen(sheet)" class="character-asset-picker">
                  <div class="character-asset-picker__head">
                    <h4>{{ characterSheetTitle(sheet) }}素材</h4>
                    <button class="workflow-icon-action" type="button" @click="closeCharacterAssetPicker"><IconClose size="xs" /></button>
                  </div>
                  <div class="character-asset-picker__filters">
                    <input v-model="characterAssetPicker.keyword" class="field-input" type="search" placeholder="关键词" @keyup.enter="loadCharacterAssetCandidates(sheet)" />
                    <button class="btn-secondary btn-sm" type="button" :disabled="characterAssetPicker.loading" @click="loadCharacterAssetCandidates(sheet)">
                      <IconLoading v-if="characterAssetPicker.loading" size="xs" /><IconSearch v-else size="xs" />
                      <span>{{ characterAssetPicker.loading ? "搜索中" : "搜索" }}</span>
                    </button>
                  </div>
                  <div v-if="characterAssetPicker.error" class="workflow-error">{{ characterAssetPicker.error }}</div>
                  <div v-else-if="!characterAssetPicker.assets.length" class="workflow-empty workflow-empty-nested">没有匹配素材</div>
                  <div v-else class="character-asset-grid">
                    <article v-for="asset in characterAssetPicker.assets" :key="asset.id" class="character-asset-card">
                      <button type="button" class="character-asset-card__preview" @click="openImagePreview(materialAssetPreviewUrl(asset), asset.title)">
                        <img v-if="isPreviewImageAvailable(materialAssetPreviewUrl(asset))" :src="materialAssetPreviewUrl(asset)" :alt="asset.title" @error="markPreviewImageFailed(materialAssetPreviewUrl(asset))" />
                        <span v-else class="workflow-image-fallback"><IconEmpty size="sm" /></span>
                      </button>
                      <div class="character-asset-card__body">
                        <strong>{{ asset.title }}</strong>
                        <span class="surface-chip surface-chip-quiet">{{ materialAssetModelLabel(asset) }}</span>
                      </div>
                      <button class="btn-primary btn-sm" type="button" :disabled="busyActionKey === `character-sheet-asset-${characterSheetClipIndex(sheet)}`" @click="handleSelectCharacterSheetAsset(sheet, asset.id)">
                        <span>{{ busyActionKey === `character-sheet-asset-${characterSheetClipIndex(sheet)}` ? "选择中" : "选择" }}</span>
                      </button>
                    </article>
                  </div>
                </section>
              </article>
            </div>
          </section>

          <!-- ── 关键帧 ── -->
          <section v-else-if="activeCanvasStage === 'keyframe'" class="workflow-stage-board keyframe-board">
            <div class="stage-board__head">
              <h3>关键帧</h3>
              <div class="stage-board__head-actions">
                <button
                  v-if="(selectedWorkflow.clipSlots ?? []).some(s => s.keyframeVersions.length > 0)"
                  class="btn-secondary btn-sm workflow-menu-danger"
                  type="button"
                  :disabled="busyActionKey === 'clear-keyframe-versions'"
                  @click="handleClearStageVersions('keyframe')"
                >
                  <IconLoading v-if="busyActionKey === 'clear-keyframe-versions'" size="xs" />
                  <IconDelete v-else size="xs" />
                  <span>{{ busyActionKey === 'clear-keyframe-versions' ? '清空中' : '清空关键帧版本' }}</span>
                </button>
                <button class="btn-primary btn-sm" type="button" :disabled="!selectedCanvasClip || busyActionKey === `keyframe-${selectedCanvasClip.clipIndex}`" @click="selectedCanvasClip && handleGenerateKeyframe(selectedCanvasClip.clipIndex)">
                  <IconLoading v-if="selectedCanvasClip && busyActionKey === `keyframe-${selectedCanvasClip.clipIndex}`" size="xs" />
                  <span>{{ selectedCanvasClip && busyActionKey === `keyframe-${selectedCanvasClip.clipIndex}` ? "生成中" : "生成" }}</span>
                </button>
              </div>
            </div>
            <section class="clip-workbench">
              <nav class="clip-timeline" aria-label="镜头列表">
                <button v-for="slot in selectedWorkflow.clipSlots" :key="slot.clipIndex" type="button" class="clip-timeline__item" :class="{ 'clip-timeline__item-active': selectedCanvasClip?.clipIndex === slot.clipIndex }" @click="selectCanvasClip(slot.clipIndex)">
                  <strong>{{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}</strong>
                  <span>{{ slot.keyframeVersions.length ? `${slot.keyframeVersions.length} 版` : '未生成' }}</span>
                </button>
              </nav>
              <article v-if="selectedCanvasClip" class="clip-detail-card">
                <div class="clip-detail-card__head">
                  <div>
                    <h4>{{ selectedCanvasClip.shotLabel || `镜头 #${selectedCanvasClip.clipIndex}` }}</h4>
                    <p>{{ clipSceneSummary(selectedCanvasClip) }}</p>
                  </div>
                  <span class="surface-chip">{{ selectedCanvasClip.durationHint || `${selectedCanvasClip.targetDurationSeconds || 0}s` }}</span>
                </div>
                <div v-if="selectedCanvasClip.keyframeVersions.length" class="version-switcher">
                  <div class="version-switcher__tabs">
                    <article v-for="version in selectedCanvasClip.keyframeVersions" :key="version.id" class="version-switcher__tab" :class="{ 'version-switcher__tab-active': previewKeyframeVersion?.id === version.id }">
                      <button type="button" class="version-switcher__tab-main" @click="setPreviewKeyframeVersion(selectedCanvasClip.clipIndex, version.id)">
                        <span class="compact-version-card__badge">V{{ version.versionNo }}</span>
                        <strong>{{ stageVersionDisplayTitle(version) }}</strong>
                      </button>
                      <div class="workflow-more-menu compact-version-menu">
                        <button type="button" class="workflow-more-menu__trigger" :popovertarget="`wfd-kf-${version.id}`"><IconMore size="sm" /></button>
                        <div :id="`wfd-kf-${version.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionVersionMenu">
                          <button type="button" :disabled="version.selected" @click="handleSelectKeyframe(selectedCanvasClip.clipIndex, version.id)"><IconCheck size="xs" /><span>设为当前</span></button>
                          <button type="button" class="workflow-menu-danger" @click="handleDeleteStageVersion(version)"><IconDelete size="xs" /><span>删除</span></button>
                        </div>
                      </div>
                    </article>
                  </div>
                </div>
                <div v-if="previewKeyframeVersion" class="keyframe-frame-grid" :class="isLandscapeKeyframeVersion(previewKeyframeVersion) ? 'keyframe-frame-grid-landscape' : 'keyframe-frame-grid-portrait'">
                  <article v-for="frame in keyframePreviewFrames(previewKeyframeVersion, selectedCanvasClip)" :key="`${selectedCanvasClip.clipIndex}-${frame.role}`" class="keyframe-frame-card">
                    <div class="keyframe-frame-card__head">
                      <span class="surface-chip surface-chip-quiet">{{ frame.label }}</span>
                      <span v-if="frame.selected" class="surface-chip">已选</span>
                    </div>
                    <button v-if="frame.url && !isPreviewImageFailed(frame.url)" type="button" class="keyframe-frame-card__preview" @click="openKeyframeImagePreview(previewKeyframeVersion, frame)">
                      <img :src="frame.url" :alt="frame.label" @error="markPreviewImageFailed(frame.url)" />
                    </button>
                    <div v-else class="keyframe-frame-card__failure">
                      <IconWarning v-if="frame.errorMessage" size="sm" />
                      <IconEmpty v-else size="sm" />
                      <strong>{{ frame.errorMessage ? "生成失败" : frame.label }}</strong>
                    </div>
                    <div class="keyframe-frame-card__actions">
                      <button v-if="!frame.selected" class="workflow-icon-action" type="button" :disabled="busyActionKey === `${previewKeyframeVersion.id}-${frame.role}`" @click="handleSelectKeyframeFrame(selectedCanvasClip.clipIndex, previewKeyframeVersion.id, frame.role)"><IconCheck size="xs" /></button>
                      <button class="workflow-icon-action" type="button" :disabled="!frame.regenerable || busyActionKey === `keyframe-${selectedCanvasClip.clipIndex}-${frame.role}`" @click="handleGenerateKeyframeFrame(selectedCanvasClip.clipIndex, frame.role)"><IconRefresh size="xs" /></button>
                    </div>
                  </article>
                </div>
                <div v-else class="workflow-empty workflow-empty-nested">暂无关键帧</div>
              </article>
            </section>
          </section>

          <!-- ── 视频片段 ── -->
          <section v-else-if="activeCanvasStage === 'video'" class="workflow-stage-board video-board">
            <div class="stage-board__head">
              <h3>视频片段</h3>
              <div class="stage-board__meta">
                <div class="readiness-strip">
                  <span>{{ videoReadiness.total }} 镜头</span>
                  <span>{{ videoReadiness.selected }} 已选</span>
                </div>
                <button
                  v-if="videoReadiness.total > 0 && selectedWorkflow.clipSlots.some(s => s.videoVersions.length > 0)"
                  class="btn-secondary btn-sm workflow-menu-danger"
                  type="button"
                  :disabled="busyActionKey === 'clear-video-versions'"
                  @click="handleClearStageVersions('video')"
                >
                  <IconLoading v-if="busyActionKey === 'clear-video-versions'" size="xs" />
                  <IconDelete v-else size="xs" />
                  <span>{{ busyActionKey === 'clear-video-versions' ? '清空中' : '清空视频版本' }}</span>
                </button>
                <button class="btn-primary btn-sm" type="button" :disabled="!selectedCanvasClip || busyActionKey === `video-${selectedCanvasClip?.clipIndex}`" @click="selectedCanvasClip && handleGenerateVideo(selectedCanvasClip.clipIndex)">
                  <IconLoading v-if="selectedCanvasClip && busyActionKey === `video-${selectedCanvasClip.clipIndex}`" size="xs" />
                  <span>{{ selectedCanvasClip && busyActionKey === `video-${selectedCanvasClip.clipIndex}` ? "生成中" : "生成" }}</span>
                </button>
              </div>
            </div>
            <section class="clip-workbench">
              <nav class="clip-timeline" aria-label="视频镜头列表">
                <button v-for="slot in selectedWorkflow.clipSlots" :key="`video-${slot.clipIndex}`" type="button" class="clip-timeline__item" :class="{ 'clip-timeline__item-active': selectedCanvasClip?.clipIndex === slot.clipIndex }" @click="selectCanvasClip(slot.clipIndex)">
                  <strong>{{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}</strong>
                  <span>{{ videoSlotStatusLabel(slot) }}</span>
                </button>
              </nav>
              <article v-if="selectedCanvasClip" class="clip-detail-card video-clip-detail">
                <div class="clip-detail-card__head">
                  <div>
                    <h4>{{ selectedCanvasClip.shotLabel || `镜头 #${selectedCanvasClip.clipIndex}` }}</h4>
                    <p>{{ clipSceneSummary(selectedCanvasClip) }}</p>
                  </div>
                </div>
                <div v-if="!selectedCanvasClip.videoVersions.length" class="workflow-empty workflow-empty-nested">暂无视频版本</div>
                <div v-else class="video-version-panel">
                  <div class="version-switcher">
                    <div class="version-switcher__tabs">
                      <article v-for="version in selectedCanvasClip.videoVersions" :key="version.id" class="version-switcher__tab" :class="{ 'version-switcher__tab-active': previewVideoVersion?.id === version.id }">
                        <button type="button" class="version-switcher__tab-main" @click="setPreviewVideoVersion(selectedCanvasClip.clipIndex, version.id)">
                          <span class="compact-version-card__badge">V{{ version.versionNo }}</span>
                          <strong>{{ stageVersionDisplayTitle(version) }}</strong>
                          <span v-if="version.selected" class="surface-chip">当前</span>
                        </button>
                        <div class="workflow-more-menu compact-version-menu">
                          <button type="button" class="workflow-more-menu__trigger" :popovertarget="`wfd-vid-${version.id}`"><IconMore size="sm" /></button>
                          <div :id="`wfd-vid-${version.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionVersionMenu">
                            <button type="button" :disabled="!canSelectVideoVersion(version) || version.selected" @click="handleSelectVideo(selectedCanvasClip.clipIndex, version.id)"><IconCheck size="xs" /><span>设为当前</span></button>
                            <a v-if="version.downloadUrl" :href="version.downloadUrl" download target="_blank"><IconDownload size="xs" /><span>下载</span></a>
                            <button type="button" class="workflow-menu-danger" @click="handleDeleteStageVersion(version)"><IconDelete size="xs" /><span>删除</span></button>
                          </div>
                        </div>
                      </article>
                    </div>
                  </div>
                  <article v-if="previewVideoVersion" class="video-version-card" :class="{ 'video-version-card-active': previewVideoVersion.selected }">
                    <div v-if="videoVersionErrorMessage(previewVideoVersion)" class="workflow-error" :title="videoVersionErrorMessage(previewVideoVersion)">{{ compactVideoVersionError(previewVideoVersion) }}</div>
                    <video v-else-if="previewVideoVersion.previewUrl && canSelectVideoVersion(previewVideoVersion)" :src="previewVideoVersion.previewUrl" controls playsinline preload="metadata"></video>
                    <div v-else class="workflow-empty workflow-empty-nested">{{ videoVersionStatusLabel(previewVideoVersion) }}</div>
                    <div class="version-card__actions">
                      <button class="workflow-icon-action" type="button" :disabled="!canSelectVideoVersion(previewVideoVersion) || previewVideoVersion.selected" @click="handleSelectVideo(selectedCanvasClip.clipIndex, previewVideoVersion.id)"><IconCheck size="xs" /></button>
                    </div>
                  </article>
                </div>
              </article>
            </section>
          </section>

          <!-- ── 成片 ── -->
          <section v-else class="workflow-stage-board final-board">
            <div class="stage-board__head">
              <h3>成片</h3>
              <div class="stage-board__meta">
                <div class="readiness-strip"><span>{{ videoReadiness.selected }}/{{ videoReadiness.total }} 已选</span><span>{{ finalizeHint }}</span></div>
                <button class="btn-primary btn-sm" type="button" :disabled="!canFinalize || busyActionKey === 'finalize'" @click="handleFinalize">
                  <IconLoading v-if="busyActionKey === 'finalize'" size="xs" />
                  <span>{{ busyActionKey === "finalize" ? "拼接中" : finalizeButtonLabel }}</span>
                </button>
              </div>
            </div>
            <article v-if="selectedWorkflow.finalResult" class="final-result-card-v2">
              <video v-if="selectedWorkflow.finalResult.previewUrl" class="final-result-card__video" :src="selectedWorkflow.finalResult.previewUrl" controls playsinline preload="metadata"></video>
              <div class="final-result-card-v2__meta">
                <h4>{{ selectedWorkflow.finalResult.title }}</h4>
                <span>{{ durationLabel(selectedWorkflow.finalResult.durationSeconds) }}</span>
                <a class="btn-primary btn-sm" :href="selectedWorkflow.finalResult.fileUrl" download target="_blank"><IconDownload size="xs" /> 下载</a>
              </div>
            </article>
            <div v-else class="workflow-empty workflow-empty-large">{{ canFinalize ? "可拼接" : `缺 ${videoReadiness.missing.length} 个镜头` }}</div>
          </section>
        </main>
      </section>
    </template>

    <!-- 角色摘要弹窗 -->
    <div v-if="characterSummaryPreviewState.open" class="character-summary-dialog-overlay" role="dialog" aria-modal="true" @click.self="closeCharacterSummaryPreview">
      <div class="character-summary-dialog">
        <div class="character-summary-dialog__head">
          <h4>{{ characterSummaryPreviewState.title }}</h4>
          <button type="button" class="character-summary-dialog__close" @click="closeCharacterSummaryPreview"><IconClose size="sm" /></button>
        </div>
        <p class="character-summary-dialog__content">{{ characterSummaryPreviewState.content }}</p>
      </div>
    </div>

    <!-- 图片预览弹窗 -->
    <div v-if="imagePreviewState.open" ref="imagePreviewOverlayRef" class="image-preview-overlay" role="dialog" aria-modal="true" @click.self="closeImagePreview">
      <div class="image-preview-caption"><strong>{{ imagePreviewCaption }}</strong></div>
      <button type="button" class="image-preview-close" @click="closeImagePreview"><IconClose size="sm" /></button>
      <img class="image-preview-full" :src="imagePreviewState.url" :alt="imagePreviewState.alt" @error="imagePreviewLoadFailed = true" />
    </div>

    <AppConfirmDialog v-bind="confirmDialog" @confirm="acceptConfirm" @cancel="cancelConfirm" />
  </section>
</template>

<script setup lang="ts">
/**
 * 工作流详情面板组件。
 * 从 StageWorkflowView 提取，展示工作流的阶段流水线编辑器。
 */
import AppConfirmDialog from "@/components/common/AppConfirmDialog.vue";
import AppSelect from "@/components/common/AppSelect.vue";
import WorkflowStagePipeline from "@/views/workflow/components/WorkflowStagePipeline.vue";
import {
  IconCheck,
  IconClose,
  IconDelete,
  IconDownload,
  IconEmpty,
  IconLoading,
  IconMore,
  IconPlus,
  IconRefresh,
  IconSearch,
  IconSettings,
  IconWarning,
} from "@/components/icons";
import { useWorkflowDetail } from "../composables/useWorkflowDetail";
import { useAutoPilot } from "@/composables/workflow/useAutoPilot";
import { watch, computed, ref } from "vue";

const props = defineProps<{
  selectedWorkflowId: string;
  reloadWorkflows: () => Promise<void>;
}>();

const detail = useWorkflowDetail({
  selectedWorkflowId: () => props.selectedWorkflowId,
  reloadWorkflows: props.reloadWorkflows,
});

// ── AutoPilot ──

const autoPilot = useAutoPilot(() => props.selectedWorkflowId);

// Extract execution mode from the workflow summary
const executionMode = computed(() => detail.selectedWorkflow.value?.executionMode ?? detail.selectedWorkflow.value?.durationMode ?? "manual");

// Show only the last 2 log entries
const recentLog = computed(() => autoPilot.statusLog.value.slice(-1));

// Sync autoPilotState from workflow detail and push status log entries.
// Uses a ref to track whether the first data load has completed.
const _autoPilotInitialized = ref(false);

watch(
  () => detail.selectedWorkflow.value?.autoPilotState,
  (state, prevState) => {
    // On first data load, initialize from backend state.
    if (!_autoPilotInitialized.value) {
      _autoPilotInitialized.value = true;
      autoPilot.autoPilotState.value = state || 'idle';
      autoPilot.nextStage.value = detail.selectedWorkflow.value?.autoPilotNextStage ?? detail.selectedWorkflow.value?.currentStage ?? "";
      autoPilot.currentTask.value = detail.selectedWorkflow.value?.autoPilotCurrentTask ?? "";
      autoPilot.errorMessage.value = detail.selectedWorkflow.value?.autoPilotErrorMessage ?? "";
      if (state) {
        const labels: Record<string, string> = {
          queued: '排队中',
          running: '自动执行',
          paused: '已暂停',
          failed: '执行失败',
          completed: '已完成',
          idle: '已停止',
        };
        const messages: Record<string, string> = {
          queued: '已加入队列，等待执行',
          running: '',
          paused: '已暂停',
          failed: '执行失败',
          completed: '已完成',
          idle: '已停止',
        };
        const msg = messages[state] ?? state;
        if (msg) autoPilot.pushStatusLog(labels[state] ?? state, msg, state);
      }
      return;
    }

    // Subsequent changes: only update when backend explicitly changes state.
    if (state !== prevState) {
      autoPilot.autoPilotState.value = state || 'idle';
      autoPilot.nextStage.value = detail.selectedWorkflow.value?.autoPilotNextStage ?? detail.selectedWorkflow.value?.currentStage ?? "";
      autoPilot.currentTask.value = detail.selectedWorkflow.value?.autoPilotCurrentTask ?? "";
      autoPilot.errorMessage.value = detail.selectedWorkflow.value?.autoPilotErrorMessage ?? "";

      const labels: Record<string, string> = {
        queued: '排队中',
        running: '自动执行',
        paused: '已暂停',
        failed: '执行失败',
        completed: '已完成',
        idle: '已停止',
      };
      const messages: Record<string, string> = {
        queued: '已加入队列，等待执行',
        running: '',
        paused: '已暂停',
        failed: '执行失败',
        completed: '已完成',
        idle: '已停止',
      };
      if (state) {
        const msg = messages[state] ?? state;
        if (msg) autoPilot.pushStatusLog(labels[state] ?? state, msg, state);
      }
    }
  }
);

// Sync currentTask from polling data and push to log when it changes.
let _lastTask = '';
watch(
  () => detail.selectedWorkflow.value?.autoPilotCurrentTask,
  (task) => {
    const t = task ?? '';
    autoPilot.currentTask.value = t;
    if (t && t !== _lastTask && autoPilot.isRunning.value) {
      autoPilot.pushStatusLog('自动执行', t, 'running');
    }
    _lastTask = t;
  }
);

// Start/stop polling based on auto mode (queued or running)
watch(
  () => autoPilot.isActive.value,
  (active) => {
    if (active) {
      autoPilot.startPolling(detail.pollCurrentWorkflow);
    } else {
      autoPilot.stopPolling();
    }
  }
);

// Stop polling when auto-pilot reaches a terminal state.
watch(
  () => autoPilot.autoPilotState.value,
  (state) => {
    if (state === 'idle' || state === 'failed' || state === 'completed') {
      autoPilot.stopPolling();
    }
  }
);

const {
  selectedWorkflow,
  loadingDetail,
  busyActionKey,
  activeCanvasStage,
  workflowSettingsOpen,
  workflowSettingsDraft,
  workflowSettingsValidationMessage,
  storyboardAdjustmentDrafts,
  characterSummaryPreviewState,
  confirmDialog,
  acceptConfirm,
  cancelConfirm,
  canvasStageItems,
  workflowParameterTags,
  workflowCharacterSheets,
  missingCharacterSheets,
  selectedStoryboardVersion,
  selectedCanvasClip,
  previewKeyframeVersion,
  previewVideoVersion,
  canFinalize,
  finalizeButtonLabel,
  finalizeHint,
  videoReadiness,
  textModelSelectOptions,
  imageModelSelectOptions,
  videoModelSelectOptions,
  aspectRatioSelectOptions,
  stylePresetSelectOptions,
  workflowSettingsVideoSizeSelectOptions,
  imagePreviewOverlayRef,
  imagePreviewState,
  imagePreviewCaption,
  imagePreviewLoadFailed,
  openImagePreview,
  closeImagePreview,
  characterAssetPicker,
  materialAssetPreviewUrl,
  materialAssetModelLabel,
  isCharacterAssetPickerOpen,
  openCharacterAssetPicker,
  closeCharacterAssetPicker,
  loadCharacterAssetCandidates,
  stageVersionDisplayTitle,
  stageStatusLabel,
  videoVersionErrorMessage,
  compactVideoVersionError,
  canSelectVideoVersion,
  videoVersionStatusLabel,
  videoSlotStatusLabel,
  selectCanvasClip,
  storyboardPreviewHtml,
  isLandscapeKeyframeVersion,
  keyframePreviewFrames,
  isPreviewImageFailed,
  isPreviewImageAvailable,
  markPreviewImageFailed,
  durationLabel,
  clipSceneSummary,
  openCharacterSummaryPreview,
  closeCharacterSummaryPreview,
  openKeyframeImagePreview,
  positionVersionMenu,
  previewCharacterSheetVersion,
  characterSheetKey,
  characterSheetClipIndex,
  characterSheetTitle,
  characterSheetAppearanceSummary,
  characterSheetPreviewFrames,
  setPreviewStoryboardVersion,
  setPreviewKeyframeVersion,
  setPreviewVideoVersion,
  switchCanvasStage,
  handleUpdateWorkflowSettings,
  handleGenerateStoryboard,
  handleAdjustStoryboard,
  handleSelectStoryboard,
  handleGenerateKeyframe,
  handleGenerateMissingCharacterSheets,
  handleGenerateKeyframeFrame,
  handleSelectKeyframe,
  handleSelectKeyframeFrame,
  handleSelectCharacterSheetAsset,
  handleGenerateVideo,
  handleSelectVideo,
  handleFinalize,
  handleDeleteStageVersion,
  handleClearStageVersions,
  handleReuseAsset,
} = detail;
</script>

<style scoped>
.workflow-canvas-main {
  display: grid;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  padding: 0;
  gap: 16px;
}

/* ── AutoPilot Control Bar ── */

.autopilot-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: #fff;
  box-shadow: var(--shadow-soft);
}

.autopilot-bar__status {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  min-width: 0;
}

.autopilot-bar__status strong {
  font-size: 0.88rem;
  color: var(--text-strong);
  white-space: nowrap;
}

.autopilot-bar__hint {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.autopilot-bar__next-stage {
  font-size: 0.78rem;
  color: var(--text-muted);
  font-weight: 400;
}

.autopilot-bar__error {
  font-size: 0.78rem;
  color: var(--accent-danger);
}

.autopilot-bar__actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.autopilot-bar__dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.autopilot-bar__dot-running {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.5);
  animation: autopilot-pulse 2s ease-in-out infinite;
}

.autopilot-bar__dot-paused {
  background: #f59e0b;
}

.autopilot-bar__dot-failed {
  background: var(--accent-danger);
}

@keyframes autopilot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.autopilot-bar-running {
  border-color: rgba(34, 197, 94, 0.2);
  background: rgba(34, 197, 94, 0.03);
}

.autopilot-bar-paused {
  border-color: rgba(245, 158, 11, 0.2);
  background: rgba(245, 158, 11, 0.03);
}

.autopilot-bar-failed {
  border-color: rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.03);
}

.autopilot-bar__dot-queued {
  background: #f59e0b;
  box-shadow: 0 0 6px rgba(245, 158, 11, 0.5);
  animation: autopilot-pulse 2s ease-in-out infinite;
}

.autopilot-bar-queued {
  border-color: rgba(245, 158, 11, 0.2);
  background: rgba(245, 158, 11, 0.03);
}

.autopilot-bar__queue-info {
  font-size: 0.78rem;
  color: var(--text-muted);
}

.autopilot-bar-idle {
  border-color: rgba(99, 102, 241, 0.2);
  background: rgba(99, 102, 241, 0.03);
}

/* ── Status Log ── */

.autopilot-bar__log {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  background: rgba(0, 0, 0, 0.025);
  font-size: 0.74rem;
}

.autopilot-log-entry {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-body);
}

.autopilot-log-entry__time {
  flex-shrink: 0;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  font-size: 0.7rem;
}

.autopilot-log-entry__stage {
  flex-shrink: 0;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 0.65rem;
  font-weight: 600;
}

.autopilot-log-entry__stage--running {
  background: #22c55e;
  color: #fff;
}

.autopilot-log-entry__stage--queued {
  background: #f59e0b;
  color: #fff;
}

.autopilot-log-entry__stage--paused {
  background: #f59e0b;
  color: #fff;
}

.autopilot-log-entry__stage--failed {
  background: #ef4444;
  color: #fff;
}

.autopilot-log-entry__stage--idle {
  background: #9ca3af;
  color: #fff;
}

.autopilot-log-entry__stage--completed {
  background: #22c55e;
  color: #fff;
}

.autopilot-log-entry__message {
  flex: 1;
  min-width: 0;
  color: var(--text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Active log entry shimmer ── */
.autopilot-log-entry--active {
  position: relative;
  overflow: hidden;
}

.autopilot-log-entry--active::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(99, 102, 241, 0.08) 40%,
    rgba(99, 102, 241, 0.12) 50%,
    rgba(99, 102, 241, 0.08) 60%,
    transparent 100%
  );
  transform: translateX(-100%);
  animation: autopilot-shimmer 2s ease-in-out infinite;
}

@keyframes autopilot-shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

@keyframes autopilot-log-slide-up {
  0% {
    opacity: 0;
    transform: translateY(6px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.workflow-canvas-header {
  position: relative;
  z-index: 20;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 16px 18px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: #fff;
  box-shadow: var(--shadow-soft);
  border-radius: var(--radius-md);
}

.workflow-canvas-header__body {
  display: grid;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.workflow-canvas-header__body h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--text-strong);
}

.workflow-canvas-header__summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.workflow-settings-btn-active {
  background: var(--bg-soft) !important;
}

.workflow-summary__parameter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.workflow-summary-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  background: var(--bg-softer);
  font-size: 0.75rem;
}

.workflow-summary-tag__label { color: var(--text-muted); }
.workflow-summary-tag__value { color: var(--text-strong); font-weight: 600; }

.workflow-header-settings {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--bg-softer);
}

.workflow-settings-stack {
  display: grid;
  gap: 10px;
}

.workflow-header-settings__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 8px;
}

.workflow-field {
  display: grid;
  gap: 6px;
}

.workflow-field span {
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 700;
}

.workflow-error {
  color: var(--accent-danger);
  font-size: 0.82rem;
  padding: 6px 0;
}

.workflow-canvas-grid {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.workflow-stage-canvas {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.workflow-stage-board {
  display: grid;
  gap: 14px;
  padding: 16px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: #fff;
  box-shadow: var(--shadow-soft);
  border-radius: var(--radius-md);
}

.stage-board__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.stage-board__head h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-strong);
}

.stage-board__meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.workflow-empty {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 0.88rem;
}

.workflow-empty-large { min-height: 120px; display: grid; place-items: center; }
.workflow-empty-nested { padding: 16px; }

/* ── Version Switcher ── */
.version-switcher { display: grid; gap: 8px; }
.version-switcher__tabs { display: flex; flex-wrap: wrap; gap: 6px; }

.version-switcher__tab {
  display: flex;
  align-items: center;
  gap: 4px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: var(--bg-softer);
  overflow: hidden;
}

.version-switcher__tab-active {
  border-color: var(--accent-indigo);
  background: rgba(99, 102, 241, 0.06);
}

.version-switcher__tab-main {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 0;
  background: transparent;
  cursor: pointer;
  font-size: 0.82rem;
  color: var(--text-strong);
}

.compact-version-card__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 20px;
  padding: 0 5px;
  border-radius: 5px;
  background: var(--accent-indigo);
  color: white;
  font-size: 0.68rem;
  font-weight: 700;
}

.compact-version-card__status {
  font-size: 0.72rem;
  color: var(--text-muted);
}

/* ── More Menu ── */
.workflow-more-menu { position: relative; }

.workflow-more-menu__trigger {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.workflow-more-menu__trigger:hover { background: var(--bg-soft); }

.workflow-more-menu__popover {
  position: fixed;
  inset: unset;
  margin: 0;
  z-index: 100;
  min-width: 140px;
  padding: 6px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.workflow-more-menu__popover button,
.workflow-more-menu__popover a {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--text-strong);
  font-size: 0.82rem;
  cursor: pointer;
  text-decoration: none;
}

.workflow-more-menu__popover button:hover,
.workflow-more-menu__popover a:hover { background: var(--bg-softer); }
.workflow-more-menu__popover button:disabled { opacity: 0.4; cursor: not-allowed; }

.workflow-menu-danger { color: var(--accent-danger) !important; }

/* ── Storyboard ── */
.storyboard-layout { display: grid; gap: 12px; }

.storyboard-preview-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: var(--radius-md);
  background: var(--bg-softer);
}

.storyboard-preview-markdown {
  padding: 12px;
  border-radius: 8px;
  background: #fff;
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--text-body);
  max-height: 400px;
  overflow: auto;
}

.storyboard-adjust-panel {
  display: flex;
  gap: 8px;
  align-items: center;
}

.storyboard-adjust-panel__input { flex: 1; }

/* ── Character ── */
.character-strip__list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.character-mini-card {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: var(--radius-md);
  background: var(--bg-softer);
}

.character-mini-card__head strong {
  font-size: 0.9rem;
  color: var(--text-strong);
}

.character-mini-card__summary {
  display: grid;
  gap: 4px;
  padding: 8px;
  border: 0;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  text-align: left;
}

.character-mini-card__summary-label { font-size: 0.7rem; color: var(--text-muted); }
.character-mini-card__summary p { margin: 0; font-size: 0.8rem; color: var(--text-body); }

.character-mini-card__frames {
  display: flex;
  gap: 6px;
}

.character-mini-frame {
  display: grid;
  gap: 4px;
  padding: 4px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 0.7rem;
  color: var(--text-muted);
}

.character-mini-frame img {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
}

.character-mini-card__actions {
  display: flex;
  gap: 6px;
}

.character-asset-picker {
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--accent-indigo);
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.03);
}

.character-asset-picker__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.character-asset-picker__filters {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.character-asset-picker__filters input { flex: 1; }

.character-asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px;
}

.character-asset-card {
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  background: #fff;
}

.character-asset-card__preview {
  border: 0;
  padding: 0;
  cursor: pointer;
  border-radius: 6px;
  overflow: hidden;
}

.character-asset-card__preview img { width: 100%; height: 100px; object-fit: cover; }

.character-asset-card__body {
  display: grid;
  gap: 4px;
}

.character-asset-card__body strong { font-size: 0.82rem; }

/* ── Clip Workbench ── */
.clip-workbench { display: grid; gap: 12px; }

.clip-timeline {
  display: flex;
  gap: 4px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.clip-timeline__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 80px;
  padding: 8px 10px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  background: var(--bg-softer);
  cursor: pointer;
  font-size: 0.75rem;
  color: var(--text-body);
}

.clip-timeline__item strong { font-size: 0.78rem; color: var(--text-strong); }

.clip-timeline__item-active {
  border-color: var(--accent-indigo);
  background: rgba(99, 102, 241, 0.06);
}

.clip-detail-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: var(--radius-md);
  background: var(--bg-softer);
}

.clip-detail-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.clip-detail-card__head h4 { margin: 0; font-size: 0.92rem; }
.clip-detail-card__head p { margin: 4px 0 0; font-size: 0.8rem; color: var(--text-muted); }

/* ── Keyframe ── */
.keyframe-frame-grid {
  display: grid;
  gap: 12px;
}

.keyframe-frame-grid-landscape { grid-template-columns: repeat(2, 1fr); }
.keyframe-frame-grid-portrait { grid-template-columns: repeat(2, 1fr); }

.keyframe-frame-card {
  display: grid;
  gap: 6px;
  padding: 8px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: #fff;
}

.keyframe-frame-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.keyframe-frame-card__preview {
  border: 0;
  padding: 0;
  cursor: pointer;
  border-radius: 6px;
  overflow: hidden;
}

.keyframe-frame-card__preview img { width: 100%; height: auto; display: block; }

.keyframe-frame-card__failure {
  display: grid;
  place-items: center;
  gap: 4px;
  min-height: 80px;
  border-radius: 6px;
  background: var(--bg-softer);
  color: var(--text-muted);
  font-size: 0.78rem;
}

.keyframe-frame-card__actions {
  display: flex;
  gap: 4px;
  justify-content: flex-end;
}

/* ── Video ── */
.video-version-panel { display: grid; gap: 12px; }

.video-version-card {
  display: grid;
  gap: 8px;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 10px;
  background: #fff;
}

.video-version-card-active { border-color: var(--accent-indigo); }

.video-version-card video { width: 100%; border-radius: 6px; }

.version-card__actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.readiness-strip {
  display: flex;
  gap: 8px;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.readiness-strip span {
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--bg-softer);
}

/* ── Final ── */
.final-result-card-v2 {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: var(--radius-md);
  background: var(--bg-softer);
}

.final-result-card__video { width: 100%; border-radius: 8px; }

.final-result-card-v2__meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.final-result-card-v2__meta h4 { margin: 0; flex: 1; }

/* ── Dialogs ── */
.character-summary-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.3);
}

.character-summary-dialog {
  max-width: 480px;
  width: 90vw;
  padding: 20px;
  border-radius: var(--radius-lg);
  background: #fff;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.character-summary-dialog__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.character-summary-dialog__head h4 { margin: 0; }

.character-summary-dialog__close {
  border: 0;
  background: transparent;
  cursor: pointer;
  color: var(--text-muted);
}

.character-summary-dialog__content {
  margin: 12px 0 0;
  font-size: 0.88rem;
  color: var(--text-body);
  line-height: 1.6;
  white-space: pre-wrap;
}

/* ── Image Preview ── */
.image-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.85);
}

.image-preview-caption {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  color: white;
  font-size: 0.88rem;
  text-align: center;
}

.image-preview-close {
  position: absolute;
  top: 16px;
  right: 16px;
  border: 0;
  background: rgba(255, 255, 255, 0.15);
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  display: grid;
  place-items: center;
}

.image-preview-full {
  max-width: 90vw;
  max-height: 85vh;
  object-fit: contain;
}

.workflow-image-fallback {
  display: grid;
  place-items: center;
  min-height: 60px;
  color: var(--text-muted);
}

.workflow-icon-action {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 6px;
  background: transparent;
  color: var(--text-body);
  cursor: pointer;
}

.workflow-icon-action:hover { background: var(--bg-softer); }
.workflow-icon-action:disabled { opacity: 0.4; cursor: not-allowed; }

@media (max-width: 900px) {
  .character-strip__list { grid-template-columns: 1fr; }
  .keyframe-frame-grid-landscape,
  .keyframe-frame-grid-portrait { grid-template-columns: 1fr; }
}
</style>
