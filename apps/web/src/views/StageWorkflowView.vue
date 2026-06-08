<template>
  <section class="workflow-canvas-view" :class="{ 'workflow-canvas-view-detail': selectedWorkflowId }">
    <aside class="workflow-project-drawer">
      <button
        class="btn-primary btn-sm"
        type="button"
        :disabled="creatingWorkflow || loadingOptions"
        @click="startCreateWorkflow"
      >
        {{ creatingWorkflow ? "创建中..." : "新建画布" }}
      </button>

      <label class="workflow-search-box">
        <span class="workflow-search-box__icon"><IconSearch size="sm" /></span>
        <input
          ref="workflowSearchInput"
          v-model="workflowSearch"
          class="field-input workflow-search-box__field"
          type="search"
          placeholder="搜索标题、阶段或状态..."
        />
        <button
          v-if="workflowSearch"
          class="workflow-search-box__clear"
          type="button"
          @click="clearWorkflowSearch"
          aria-label="清除搜索"
        >
          <IconClose size="xs" />
        </button>
      </label>

      <div v-if="loadingWorkflows" class="workflow-empty-state">
        <div class="workflow-empty-state__icon">
          <IconLoading size="2xl" />
        </div>
        <p class="workflow-empty-state__text">正在加载工作流...</p>
      </div>

      <div v-else-if="!filteredWorkflows.length" class="workflow-empty-state">
        <div class="workflow-empty-state__icon">
          <IconEmpty size="2xl" />
        </div>
        <p class="workflow-empty-state__text">
          {{ workflows.length ? "没有找到匹配的工作流" : "还没有创建阶段工作流" }}
        </p>
        <p class="workflow-empty-state__hint">
          {{ workflows.length ? "尝试修改搜索关键词" : "点击上方按钮开始创建第一个工作流" }}
        </p>
      </div>

      <div v-else class="workflow-project-list">
        <article
          v-for="item in filteredWorkflows"
          :key="item.id"
          class="workflow-nav-item"
          :class="{ 'workflow-nav-item-active': item.id === selectedWorkflowId }"
          @click="openWorkflow(item.id, workflowSummaryCanvasStage(item))"
        >
          <span class="workflow-nav-item__dot" :class="{ 'workflow-nav-item__dot-active': item.id === selectedWorkflowId }"></span>
          <span class="workflow-nav-item__title">{{ item.title }}</span>
          <div class="workflow-more-menu workflow-nav-item__menu">
            <button type="button" class="workflow-more-menu__trigger" aria-label="更多操作" :popovertarget="`wfm-${item.id}`" @click.stop>
              <IconMore size="sm" />
            </button>
            <div :id="`wfm-${item.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionVersionMenu">
              <button
                type="button"
                class="workflow-menu-danger"
                :disabled="busyActionKey === `delete-workflow-${item.id}`"
                @click="handleDeleteWorkflow(item)"
              >
                {{ busyActionKey === `delete-workflow-${item.id}` ? "删除中..." : "删除工作流" }}
              </button>
            </div>
          </div>
        </article>
      </div>
    </aside>

    <section class="workflow-canvas-main">
      <section v-if="createComposerVisible" class="workflow-create-board">
        <div class="workflow-create-shell">
          <form class="workflow-composer-card workflow-composer-card-chat" @submit.prevent="handleCreateWorkflow">
            <button
              type="button"
              class="workflow-composer-upload"
              :disabled="uploadingCreateText"
              @click="createTextFileInput?.click()"
            >
              <span>+</span>
              <small>{{ uploadingCreateText ? "上传中" : "导入正文" }}</small>
            </button>
            <input
              ref="createTextFileInput"
              type="file"
              accept=".txt,text/plain"
              class="workflow-hidden-input"
              @change="handleCreateTextFileChange"
            />

            <div class="workflow-composer-fields">
              <label class="workflow-composer-title-field workflow-composer-title-field-chat">
                <span>画布标题</span>
                <input v-model="createForm.title" required placeholder="例如：第 12 集阶段拆分版" />
              </label>
              <label class="workflow-composer-body-field workflow-composer-body-field-chat">
                <span>正文 / 创作输入</span>
                <textarea
                  v-model="createForm.transcriptText"
                  rows="8"
                  placeholder="输入小说正文、剧情设定或脚本内容。也可以上传 txt，先把内容放进画布，再继续阶段创作。"
                ></textarea>
              </label>
            </div>

            <div class="workflow-composer-toolbar workflow-composer-toolbar-chat">
              <div class="workflow-create-menu">
                <button
                  type="button"
                  class="tool-pill tool-pill-interactive"
                  :class="{ 'tool-pill-active': createComposerMenu === 'models' }"
                  @click="toggleCreateComposerMenu('models')"
                >
                  {{ createModelMenuLabel }}
                </button>
                <div v-if="createComposerMenu === 'models'" class="workflow-create-popover workflow-create-popover-grid">
                  <label class="workflow-field">
                    <span>文本模型</span>
                    <select v-model="createForm.textAnalysisModel" class="field-input">
                      <option v-for="item in textModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                    </select>
                  </label>
                  <label class="workflow-field">
                    <span>关键帧模型</span>
                    <select v-model="createForm.imageModel" class="field-input">
                      <option v-for="item in imageModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                    </select>
                  </label>
                  <label class="workflow-field">
                    <span>视频模型</span>
                    <select v-model="createForm.videoModel" class="field-input">
                      <option v-for="item in videoModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                    </select>
                  </label>
                </div>
              </div>

              <div class="workflow-create-menu">
                <button
                  type="button"
                  class="tool-pill tool-pill-interactive"
                  :class="{ 'tool-pill-active': createComposerMenu === 'output' }"
                  @click="toggleCreateComposerMenu('output')"
                >
                  {{ createOutputMenuLabel }}
                </button>
                <div v-if="createComposerMenu === 'output'" class="workflow-create-popover workflow-create-popover-grid">
                  <label class="workflow-field">
                    <span>视觉风格</span>
                    <select v-model="createForm.stylePreset" class="field-input">
                      <option v-for="item in stylePresetOptions" :key="item.key" :value="item.key">{{ item.label }}</option>
                    </select>
                  </label>
                  <label class="workflow-field">
                    <span>画幅</span>
                    <select v-model="createForm.aspectRatio" class="field-input">
                      <option v-for="item in aspectRatioOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                    </select>
                  </label>
                  <label class="workflow-field">
                    <span>输出尺寸</span>
                    <select v-model="createForm.videoSize" class="field-input">
                      <option v-for="item in videoSizeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
                    </select>
                  </label>
                </div>
              </div>

              <div class="workflow-create-menu">
                <button
                  type="button"
                  class="tool-pill tool-pill-interactive"
                  :class="{ 'tool-pill-active': createComposerMenu === 'duration' }"
                  @click="toggleCreateComposerMenu('duration')"
                >
                  {{ createDurationMenuLabel }}
                </button>
                <div v-if="createComposerMenu === 'duration'" class="workflow-create-popover workflow-create-popover-compact">
                  <div class="workflow-field">
                    <span>镜头时长</span>
                    <div class="stage-toggle-row">
                      <button type="button" class="stage-toggle-chip" :class="{ 'stage-toggle-chip-active': storyboardDurationMode === 'auto' }" @click="storyboardDurationMode = 'auto'">自动</button>
                      <button type="button" class="stage-toggle-chip" :class="{ 'stage-toggle-chip-active': storyboardDurationMode === 'manual' }" @click="storyboardDurationMode = 'manual'">手动</button>
                    </div>
                  </div>
                  <label v-if="storyboardDurationMode === 'manual'" class="workflow-field">
                    <span>固定秒数</span>
                    <input v-model="storyboardManualDurationSeconds" class="field-input" type="number" :min="STORYBOARD_MANUAL_DURATION_MIN_SECONDS" :max="STORYBOARD_MANUAL_DURATION_MAX_SECONDS" step="1" />
                  </label>
                  <p v-if="storyboardManualDurationValidationMessage" class="workflow-error workflow-create-popover__error">{{ storyboardManualDurationValidationMessage }}</p>
                </div>
              </div>

              <div class="workflow-create-menu">
                <button
                  type="button"
                  class="tool-pill tool-pill-interactive"
                  :class="{ 'tool-pill-active': createComposerMenu === 'seed' }"
                  @click="toggleCreateComposerMenu('seed')"
                >
                  {{ createSeedMenuLabel }}
                </button>
                <div v-if="createComposerMenu === 'seed'" class="workflow-create-popover workflow-create-popover-grid">
                  <label class="workflow-field">
                    <span>关键帧 Seed</span>
                    <input v-model="createForm.keyframeSeed" class="field-input" type="number" min="0" placeholder="自动" />
                  </label>
                  <label class="workflow-field">
                    <span>视频 Seed</span>
                    <input v-model="createForm.videoSeed" class="field-input" type="number" min="0" placeholder="自动" />
                  </label>
                </div>
              </div>

              <span class="composer-required-count">必填 {{ createReviewConfiguredCount }} / {{ createReviewRequiredItems.length }}</span>
            </div>

            <div class="workflow-composer-footer">
              <div class="workflow-composer-meta">
                <span>{{ createTranscriptCharacterCount > 0 ? `${createTranscriptCharacterCount} 字` : "等待正文输入" }}</span>
              </div>
              <div class="workflow-composer-actions">
                <button class="btn-secondary btn-sm" type="button" :disabled="creatingWorkflow" @click="closeCreateReview">取消</button>
                <button
                  class="workflow-composer-submit workflow-composer-submit-inline"
                  type="submit"
                  :disabled="creatingWorkflow || !canSubmitCreateReview"
                  :title="canSubmitCreateReview ? '创建画布' : '请先补全必填项'"
                >
                  <span v-if="creatingWorkflow">...</span>
                  <span v-else>↑</span>
                </button>
              </div>
            </div>
          </form>

        </div>
      </section>

      <div v-else-if="showDetailLoadFailed" class="surface-panel workflow-banner workflow-banner-error">
        <p>工作流详情加载失败</p>
        <button class="btn-secondary btn-sm" type="button" :disabled="loadingDetail" @click="reloadCurrentWorkflow">重新加载</button>
      </div>

      <div v-else-if="loadingDetail" class="surface-panel workflow-empty workflow-empty-large">
        正在加载工作流详情...
      </div>

      <template v-else-if="selectedWorkflow">
        <header class="workflow-canvas-header">
          <div class="workflow-canvas-header__body">
            <h2>{{ selectedWorkflow.title }}</h2>
            <div class="workflow-canvas-header__summary">
              <div class="workflow-summary__parameter-tags workflow-summary__parameter-tags-header">
                <span v-for="item in workflowParameterTags" :key="item.label" class="workflow-summary-tag">
                  <span class="workflow-summary-tag__label">{{ item.label }}</span>
                  <strong class="workflow-summary-tag__value">{{ item.value }}</strong>
                </span>
              </div>
              <button class="btn-secondary btn-sm workflow-canvas-header__settings-button" type="button" @click="workflowSettingsOpen = !workflowSettingsOpen">
                {{ workflowSettingsOpen ? "收起参数" : "参数" }}
              </button>
            </div>
            <section v-if="workflowSettingsOpen" class="workflow-header-settings">
              <div class="workflow-header-settings__head">
                <div>
                  <p class="workflow-eyebrow">Settings</p>
                  <h3>编辑参数</h3>
                </div>
              </div>
              <form class="workflow-settings-stack workflow-header-settings__form" @submit.prevent="handleUpdateWorkflowSettings">
                <label class="workflow-field"><span>文本模型</span><select v-model="workflowSettingsDraft.textAnalysisModel" class="field-input"><option v-for="item in textModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
                <label class="workflow-field"><span>关键帧模型</span><select v-model="workflowSettingsDraft.imageModel" class="field-input"><option v-for="item in imageModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
                <label class="workflow-field"><span>视频模型</span><select v-model="workflowSettingsDraft.videoModel" class="field-input"><option v-for="item in videoModelOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
                <label class="workflow-field"><span>视觉风格</span><select v-model="workflowSettingsDraft.stylePreset" class="field-input"><option v-for="item in stylePresetOptions" :key="item.key" :value="item.key">{{ item.label }}</option></select></label>
                <label class="workflow-field"><span>长宽比</span><select v-model="workflowSettingsDraft.aspectRatio" class="field-input"><option v-for="item in aspectRatioOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
                <label class="workflow-field"><span>输出尺寸</span><select v-model="workflowSettingsDraft.videoSize" class="field-input"><option v-for="item in workflowSettingsVideoSizeOptions" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
                <label class="workflow-field"><span>关键帧 Seed</span><input v-model="workflowSettingsDraft.keyframeSeed" class="field-input" type="number" min="0" placeholder="自动" /></label>
                <label class="workflow-field"><span>视频 Seed</span><input v-model="workflowSettingsDraft.videoSeed" class="field-input" type="number" min="0" placeholder="自动" /></label>
                <div class="workflow-field"><span>镜头时长</span><div class="stage-toggle-row"><button type="button" class="stage-toggle-chip" :class="{ 'stage-toggle-chip-active': workflowSettingsDraft.durationMode === 'auto' }" @click="workflowSettingsDraft.durationMode = 'auto'">自动</button><button type="button" class="stage-toggle-chip" :class="{ 'stage-toggle-chip-active': workflowSettingsDraft.durationMode === 'manual' }" @click="workflowSettingsDraft.durationMode = 'manual'">手动</button></div></div>
                <label class="workflow-field"><span>最小时长</span><input v-model="workflowSettingsDraft.minDurationSeconds" class="field-input" type="number" min="1" max="60" step="1" :disabled="workflowSettingsDraft.durationMode === 'auto'" /></label>
                <label class="workflow-field"><span>最大时长</span><input v-model="workflowSettingsDraft.maxDurationSeconds" class="field-input" type="number" min="1" max="60" step="1" :disabled="workflowSettingsDraft.durationMode === 'auto'" /></label>
                <p v-if="workflowSettingsValidationMessage" class="workflow-error workflow-header-settings__error">{{ workflowSettingsValidationMessage }}</p>
                <div class="workflow-header-settings__actions">
                  <button class="btn-secondary btn-sm" type="button" :disabled="busyActionKey === 'workflow-settings'" @click="workflowSettingsOpen = false">收起参数</button>
                  <button class="btn-primary btn-sm" type="submit" :disabled="busyActionKey === 'workflow-settings' || Boolean(workflowSettingsValidationMessage)">
                    {{ busyActionKey === "workflow-settings" ? "保存中..." : "保存设置" }}
                  </button>
                </div>
              </form>
            </section>
          </div>
        </header>

        <WorkflowStagePipeline :stages="canvasStageItems" :active-stage="activeCanvasStage" @switch="switchCanvasStage" />

        <section class="workflow-canvas-grid">
          <main class="workflow-stage-canvas">
            <section v-if="activeCanvasStage === 'storyboard'" class="workflow-stage-board storyboard-board">
              <div class="stage-board__head">
                <h3>分镜脚本</h3>
                <button class="btn-primary btn-sm" type="button" :disabled="busyActionKey === 'storyboard'" @click="handleGenerateStoryboard">
                  {{ busyActionKey === "storyboard" ? "生成中..." : "生成分镜版本" }}
                </button>
              </div>

              <div v-if="!selectedWorkflow.storyboardVersions.length" class="workflow-empty workflow-empty-large">
                还没有分镜版本，先执行一次分镜生成。
              </div>
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
                          <span class="compact-version-card__status">{{ version.selected ? "已选中" : version.status }}</span>
                        </button>
                        <div class="workflow-more-menu compact-version-menu">
                          <button type="button" class="workflow-more-menu__trigger" aria-label="版本操作" :popovertarget="`vsm-${version.id}`">•••</button>
                          <div :id="`vsm-${version.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionVersionMenu">
                            <button type="button" :disabled="version.selected || busyActionKey === version.id" @click="handleSelectStoryboard(version.id)">
                              {{ version.selected ? "已选中" : "设为当前" }}
                            </button>
                            <button type="button" :disabled="!version.asset || busyActionKey === `reuse-${version.id}`" @click="handleReuseAsset(version.asset?.id || '', version.id)">复制为新工作流</button>
                            <button type="button" class="workflow-menu-danger" :disabled="busyActionKey === `delete-${version.id}`" @click="handleDeleteStageVersion(version)">删除版本</button>
                          </div>
                        </div>
                      </article>
                    </div>
                  </div>
                  <div v-if="selectedStoryboardVersion" class="version-card__markdown storyboard-preview-markdown" v-html="storyboardPreviewHtml(selectedStoryboardVersion)"></div>
                  <div v-if="selectedStoryboardVersion" class="storyboard-adjust-panel">
                    <input v-model="storyboardAdjustmentDrafts[selectedStoryboardVersion.id]" class="field-input storyboard-adjust-panel__input" type="text" placeholder="输入调整要求，留空则自动审查" />
                    <button
                      class="btn-primary btn-sm storyboard-adjust-panel__button"
                      type="button"
                      :disabled="busyActionKey === `storyboard-adjust-${selectedStoryboardVersion.id}` || selectedStoryboardVersion.status !== 'SUCCEEDED'"
                      @click="handleAdjustStoryboard(selectedStoryboardVersion.id)"
                    >
                      {{ busyActionKey === `storyboard-adjust-${selectedStoryboardVersion.id}` ? "调整中..." : "调整分镜" }}
                    </button>
                  </div>
                </article>
              </div>
            </section>

            <section v-else-if="activeCanvasStage === 'character'" class="workflow-stage-board character-board">
              <div class="stage-board__head">
                <h3>角色三视图</h3>
                <div class="stage-board__meta">
                  <span class="surface-chip">{{ workflowCharacterSheets.length }} 个角色</span>
                  <button class="btn-primary btn-sm" type="button" :disabled="!missingCharacterSheets.length || busyActionKey === 'character-missing'" @click="handleGenerateMissingCharacterSheets">
                    {{ busyActionKey === "character-missing" ? "生成中..." : "生成缺失角色" }}
                  </button>
                </div>
              </div>

              <div v-if="!workflowCharacterSheets.length" class="workflow-empty workflow-empty-nested">当前工作流还没有角色三视图。</div>
              <div v-else class="character-strip__list">
                <article v-for="sheet in workflowCharacterSheets" :key="characterSheetKey(sheet)" class="character-mini-card">
                  <div class="character-mini-card__head">
                    <strong>{{ characterSheetTitle(sheet) }}</strong>
                  </div>
                  <button
                    type="button"
                    class="character-mini-card__summary"
                    :aria-label="`查看${characterSheetTitle(sheet)}完整角色定义`"
                    @click="openCharacterSummaryPreview(sheet)"
                  >
                    <span class="character-mini-card__summary-label">角色定义</span>
                    <p>{{ characterSheetAppearanceSummary(sheet) }}</p>
                    <span class="character-mini-card__summary-hint">点击查看完整内容</span>
                  </button>
                  <div v-if="characterSheetVersions(sheet).length > 1" class="version-switcher version-switcher-compact">
                    <div class="version-switcher__tabs">
                      <article
                        v-for="version in characterSheetVersions(sheet)"
                        :key="version.id"
                        class="version-switcher__tab"
                        :class="{ 'version-switcher__tab-active': previewCharacterSheetVersion(sheet)?.id === version.id }"
                      >
                        <button type="button" class="version-switcher__tab-main" @click="setPreviewCharacterSheetVersion(characterSheetKey(sheet), version.id)">
                          <span class="compact-version-card__badge">V{{ version.versionNo }}</span>
                          <strong>{{ stageVersionDisplayTitle(version) }}</strong>
                          <span v-if="version.selected" class="surface-chip">当前</span>
                        </button>
                      </article>
                    </div>
                  </div>
                  <div v-if="previewCharacterSheetVersion(sheet)" class="character-mini-card__frames">
                    <button
                      v-for="frame in characterSheetPreviewFrames(previewCharacterSheetVersion(sheet)!)"
                      :key="`${characterSheetKey(sheet)}-${frame.role}`"
                      type="button"
                      class="character-mini-frame"
                      :aria-label="`查看${characterSheetTitle(sheet)}${frame.label}`"
                      @click="openImagePreview(frame.url, `${characterSheetTitle(sheet)} ${frame.label}`)"
                    >
                      <img :src="frame.url" :alt="`${characterSheetTitle(sheet)} ${frame.label}`" />
                      <span>{{ frame.label }}</span>
                    </button>
                  </div>
                  <div class="character-mini-card__actions">
                    <button class="btn-secondary btn-sm" type="button" :disabled="characterSheetClipIndex(sheet) === null" @click="openCharacterAssetPicker(sheet)">素材库</button>
                    <button class="btn-ghost btn-sm" type="button" :disabled="characterSheetClipIndex(sheet) === null || busyActionKey === 'character-missing' || busyActionKey === `keyframe-${characterSheetClipIndex(sheet)}`" @click="handleGenerateKeyframe(characterSheetClipIndex(sheet) || 0)">
                      {{ previewCharacterSheetVersion(sheet) ? "重生" : "生成" }}
                    </button>
                  </div>
                  <section v-if="isCharacterAssetPickerOpen(sheet)" class="character-asset-picker">
                    <div class="character-asset-picker__head">
                      <div>
                        <p class="workflow-eyebrow">Material Library</p>
                        <h4>选择 {{ characterSheetTitle(sheet) }} 的三视图素材</h4>
                      </div>
                      <button class="btn-secondary btn-sm" type="button" @click="closeCharacterAssetPicker">收起</button>
                    </div>
                    <div class="character-asset-picker__filters">
                      <label class="workflow-field">
                        <span>关键词</span>
                        <input v-model="characterAssetPicker.keyword" class="field-input" type="search" placeholder="按角色名、标题搜索" @keyup.enter="loadCharacterAssetCandidates(sheet)" />
                      </label>
                      <label class="workflow-field">
                        <span>模型</span>
                        <input v-model="characterAssetPicker.model" class="field-input" type="search" placeholder="按模型筛选" @keyup.enter="loadCharacterAssetCandidates(sheet)" />
                      </label>
                      <button class="btn-secondary btn-sm character-asset-picker__search" type="button" :disabled="characterAssetPicker.loading" @click="loadCharacterAssetCandidates(sheet)">
                        {{ characterAssetPicker.loading ? "搜索中..." : "搜索素材" }}
                      </button>
                    </div>
                    <p v-if="characterAssetPicker.error" class="workflow-error">{{ characterAssetPicker.error }}</p>
                    <div v-else-if="characterAssetPicker.loading" class="workflow-empty workflow-empty-nested">正在加载三视图素材...</div>
                    <div v-else-if="!characterAssetPicker.assets.length" class="workflow-empty workflow-empty-nested">没有匹配的角色三视图素材。</div>
                    <div v-else class="character-asset-grid">
                      <article v-for="asset in characterAssetPicker.assets" :key="asset.id" class="character-asset-card">
                        <button type="button" class="character-asset-card__preview" :aria-label="`查看${asset.title}素材预览`" @click="openImagePreview(materialAssetPreviewUrl(asset), asset.title)">
                          <img :src="materialAssetPreviewUrl(asset)" :alt="asset.title" />
                        </button>
                        <div class="character-asset-card__body">
                          <strong>{{ asset.title }}</strong>
                          <div class="character-asset-card__meta">
                            <span class="surface-chip surface-chip-quiet">{{ materialAssetModelLabel(asset) }}</span>
                          </div>
                        </div>
                        <button class="btn-primary btn-sm" type="button" :disabled="busyActionKey === `character-sheet-asset-${characterSheetClipIndex(sheet)}`" @click="handleSelectCharacterSheetAsset(sheet, asset.id)">
                          {{ busyActionKey === `character-sheet-asset-${characterSheetClipIndex(sheet)}` ? "选择中..." : "选择此素材" }}
                        </button>
                      </article>
                    </div>
                  </section>
                </article>
              </div>
            </section>

            <section v-else-if="activeCanvasStage === 'keyframe'" class="workflow-stage-board keyframe-board">
              <div class="stage-board__head">
                <h3>关键帧</h3>
                <button class="btn-primary btn-sm" type="button" :disabled="!selectedCanvasClip || busyActionKey === `keyframe-${selectedCanvasClip.clipIndex}`" @click="selectedCanvasClip && handleGenerateKeyframe(selectedCanvasClip.clipIndex)">
                  {{ selectedCanvasClip && busyActionKey === `keyframe-${selectedCanvasClip.clipIndex}` ? "生成中..." : "生成当前镜头关键帧" }}
                </button>
              </div>

              <section class="clip-workbench">
                <nav class="clip-timeline" aria-label="镜头列表">
                  <button
                    v-for="slot in selectedWorkflow.clipSlots"
                    :key="slot.clipIndex"
                    type="button"
                    class="clip-timeline__item"
                    :class="{ 'clip-timeline__item-active': selectedCanvasClip?.clipIndex === slot.clipIndex }"
                    @click="selectCanvasClip(slot.clipIndex)"
                  >
                    <strong>{{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}</strong>
                    <span>{{ slot.keyframeVersions.length ? `${slot.keyframeVersions.length} 版` : '未生成' }}</span>
                  </button>
                </nav>

                <article v-if="selectedCanvasClip" class="clip-detail-card">
                  <div class="clip-detail-card__head">
                    <div>
                      <p class="workflow-eyebrow">Clip {{ selectedCanvasClip.clipIndex }}</p>
                      <h4>{{ selectedCanvasClip.shotLabel || `镜头 #${selectedCanvasClip.clipIndex}` }}</h4>
                      <p>{{ clipSceneSummary(selectedCanvasClip) }}</p>
                    </div>
                    <span class="surface-chip">{{ selectedCanvasClip.durationHint || `${selectedCanvasClip.targetDurationSeconds || 0}s` }}</span>
                  </div>
                  <div v-if="selectedCanvasClip.keyframeVersions.length" class="version-switcher">
                    <div class="version-switcher__head">
                      <strong>版本历史</strong>
                      <span class="surface-chip">{{ selectedCanvasClip.keyframeVersions.length }} 个版本</span>
                    </div>
                    <div class="version-switcher__tabs">
                      <article
                        v-for="version in selectedCanvasClip.keyframeVersions"
                        :key="version.id"
                        class="version-switcher__tab"
                        :class="{ 'version-switcher__tab-active': previewKeyframeVersion?.id === version.id }"
                      >
                        <button type="button" class="version-switcher__tab-main" @click="setPreviewKeyframeVersion(selectedCanvasClip.clipIndex, version.id)">
                          <span class="compact-version-card__badge">V{{ version.versionNo }}</span>
                          <strong>{{ stageVersionDisplayTitle(version) }}</strong>
                          <span v-if="keyframeVersionHasSelectedFrame(version)" class="surface-chip">当前</span>
                        </button>
                        <div class="workflow-more-menu compact-version-menu">
                          <button type="button" class="workflow-more-menu__trigger" aria-label="版本操作" :popovertarget="`vsm-${version.id}`">•••</button>
                          <div :id="`vsm-${version.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionVersionMenu">
                            <button type="button" :disabled="version.selected || busyActionKey === version.id" @click="handleSelectKeyframe(selectedCanvasClip.clipIndex, version.id)">选中继续</button>
                            <button type="button" :disabled="!version.asset || busyActionKey === `reuse-${version.id}`" @click="handleReuseAsset(version.asset?.id || '', version.id)">复用</button>
                            <button type="button" class="workflow-menu-danger" :disabled="busyActionKey === `delete-${version.id}`" @click="handleDeleteStageVersion(version)">删除版本</button>
                          </div>
                        </div>
                      </article>
                    </div>
                  </div>
                  <div
                    v-if="previewKeyframeVersion"
                    class="keyframe-frame-grid"
                    :class="isLandscapeKeyframeVersion(previewKeyframeVersion) ? 'keyframe-frame-grid-landscape' : 'keyframe-frame-grid-portrait'"
                  >
                    <article v-for="frame in keyframePreviewFrames(previewKeyframeVersion, selectedCanvasClip)" :key="`${selectedCanvasClip.clipIndex}-${frame.role}`" class="keyframe-frame-card">
                      <div class="keyframe-frame-card__head">
                        <span class="surface-chip surface-chip-quiet">{{ frame.label }}</span>
                        <span v-if="frame.selected" class="surface-chip">已选中</span>
                      </div>
                      <button
                        v-if="frame.url"
                        type="button"
                        class="character-sheet-preview-trigger keyframe-frame-card__preview"
                        :class="isLandscapeKeyframeVersion(previewKeyframeVersion) ? 'keyframe-frame-card__preview-landscape' : 'keyframe-frame-card__preview-portrait'"
                        :aria-label="`查看${frame.label}原图`"
                        @click="openKeyframeImagePreview(previewKeyframeVersion, frame)"
                      >
                        <img class="version-card__image keyframe-frame-card__image" :src="frame.url" :alt="frame.label" />
                      </button>
                      <div v-else class="keyframe-frame-card__failure">
                        <strong>{{ frame.label }}生成失败</strong>
                        <span>{{ frame.errorMessage || "请单独重生此帧" }}</span>
                      </div>
                      <div class="keyframe-frame-card__actions">
                        <button class="btn-secondary btn-sm" type="button" :disabled="frame.selected || busyActionKey === `${previewKeyframeVersion.id}-${frame.role}`" @click="handleSelectKeyframeFrame(selectedCanvasClip.clipIndex, previewKeyframeVersion.id, frame.role)">选中此帧</button>
                        <button class="btn-ghost btn-sm" type="button" :disabled="!frame.regenerable || busyActionKey === `keyframe-${selectedCanvasClip.clipIndex}-${frame.role}`" @click="handleGenerateKeyframeFrame(selectedCanvasClip.clipIndex, frame.role)">重生此帧</button>
                      </div>
                    </article>
                  </div>
                  <div v-else class="workflow-empty workflow-empty-nested">当前镜头还没有选中的关键帧。</div>
                </article>
                <div v-else class="workflow-empty workflow-empty-large">选中分镜版本后，这里会展开镜头列表。</div>
              </section>
            </section>

            <section v-else-if="activeCanvasStage === 'video'" class="workflow-stage-board video-board">
              <div class="stage-board__head">
                <h3>视频片段</h3>
                <div class="stage-board__meta">
                  <div class="readiness-strip stage-board__readiness">
                    <span>总镜头 {{ videoReadiness.total }}</span>
                    <span>已生成 {{ videoReadiness.generated }}</span>
                    <span>已选中 {{ videoReadiness.selected }}</span>
                    <span>{{ canFinalize ? "可拼接" : `还差 ${videoReadiness.missing.length} 个镜头` }}</span>
                  </div>
                  <button class="btn-primary btn-sm" type="button" :disabled="!selectedCanvasClip || !selectedKeyframeVersion(selectedCanvasClip) || busyActionKey === `video-${selectedCanvasClip.clipIndex}`" @click="selectedCanvasClip && handleGenerateVideo(selectedCanvasClip.clipIndex)">
                    {{ selectedCanvasClip && busyActionKey === `video-${selectedCanvasClip.clipIndex}` ? "生成中..." : "生成当前镜头视频" }}
                  </button>
                </div>
              </div>

              <section class="clip-workbench">
                <nav class="clip-timeline" aria-label="视频镜头列表">
                  <button
                    v-for="slot in selectedWorkflow.clipSlots"
                    :key="`video-tab-${slot.clipIndex}`"
                    type="button"
                    class="clip-timeline__item"
                    :class="{ 'clip-timeline__item-active': selectedCanvasClip?.clipIndex === slot.clipIndex }"
                    @click="selectCanvasClip(slot.clipIndex)"
                  >
                    <strong>{{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}</strong>
                    <span>{{ slot.videoVersions.some((version) => version.selected) ? '已选中' : (slot.videoVersions.length ? '待选择' : '未生成') }}</span>
                  </button>
                </nav>

                <article v-if="selectedCanvasClip" class="clip-detail-card video-clip-detail">
                  <div class="clip-detail-card__head">
                    <div>
                      <p class="workflow-eyebrow">Clip {{ selectedCanvasClip.clipIndex }}</p>
                      <h4>{{ selectedCanvasClip.shotLabel || `镜头 #${selectedCanvasClip.clipIndex}` }}</h4>
                      <p>{{ clipSceneSummary(selectedCanvasClip) }}</p>
                    </div>
                    <span class="surface-chip">{{ selectedKeyframeVersion(selectedCanvasClip) ? stageVersionDisplayTitle(selectedKeyframeVersion(selectedCanvasClip)!) : "未选择关键帧" }}</span>
                  </div>

                  <div v-if="selectedKeyframePreviewFrames(selectedCanvasClip).length" class="keyframe-thumb-list">
                    <article v-for="frame in selectedKeyframePreviewFrames(selectedCanvasClip)" :key="`video-input-${selectedCanvasClip.clipIndex}-${frame.role}`" class="keyframe-thumb-card">
                      <img class="keyframe-thumb-card__image" :src="frame.url" :alt="frame.label" />
                      <span class="surface-chip surface-chip-quiet">{{ frame.label }}</span>
                    </article>
                  </div>

                  <div v-if="!selectedCanvasClip.videoVersions.length" class="workflow-empty workflow-empty-nested">还没有视频版本。</div>
                  <div v-else class="video-version-panel">
                    <div class="version-switcher">
                      <div class="version-switcher__head">
                        <strong>版本历史</strong>
                        <span class="surface-chip">{{ selectedCanvasClip.videoVersions.length }} 个版本</span>
                      </div>
                      <div class="version-switcher__tabs">
                        <article
                          v-for="version in selectedCanvasClip.videoVersions"
                          :key="version.id"
                          class="version-switcher__tab"
                          :class="{ 'version-switcher__tab-active': previewVideoVersion?.id === version.id }"
                        >
                          <button type="button" class="version-switcher__tab-main" @click="setPreviewVideoVersion(selectedCanvasClip.clipIndex, version.id)">
                            <span class="compact-version-card__badge">V{{ version.versionNo }}</span>
                            <strong>{{ stageVersionDisplayTitle(version) }}</strong>
                            <span v-if="version.selected" class="surface-chip">当前</span>
                          </button>
                          <div class="workflow-more-menu compact-version-menu">
                            <button type="button" class="workflow-more-menu__trigger" aria-label="版本操作" :popovertarget="`vsm-${version.id}`">•••</button>
                            <div :id="`vsm-${version.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionVersionMenu">
                              <button type="button" :disabled="version.selected || busyActionKey === version.id" @click="handleSelectVideo(selectedCanvasClip.clipIndex, version.id)">选中继续</button>
                              <button type="button" :disabled="!version.asset || busyActionKey === `reuse-${version.id}`" @click="handleReuseAsset(version.asset?.id || '', version.id)">复用</button>
                              <a v-if="version.downloadUrl" :href="version.downloadUrl" download target="_blank" rel="noopener noreferrer">下载</a>
                              <button type="button" class="workflow-menu-danger" :disabled="busyActionKey === `delete-${version.id}`" @click="handleDeleteStageVersion(version)">删除版本</button>
                            </div>
                          </div>
                        </article>
                      </div>
                    </div>
                    <article v-if="previewVideoVersion" class="video-version-card" :class="{ 'video-version-card-active': previewVideoVersion.selected }">
                      <div class="video-version-card__head">
                        <div class="video-version-card__title">
                          <span class="compact-version-card__badge">V{{ previewVideoVersion.versionNo }}</span>
                          <strong>{{ stageVersionDisplayTitle(previewVideoVersion) }}</strong>
                        </div>
                        <span v-if="previewVideoVersion.selected" class="surface-chip">当前选中</span>
                      </div>
                      <video v-if="previewVideoVersion.previewUrl" class="version-card__video" :src="previewVideoVersion.previewUrl" controls playsinline preload="metadata"></video>
                      <div class="version-card__actions">
                        <button class="btn-secondary btn-sm" type="button" :disabled="previewVideoVersion.selected || busyActionKey === previewVideoVersion.id" @click="handleSelectVideo(selectedCanvasClip.clipIndex, previewVideoVersion.id)">选中继续</button>
                        <div class="workflow-more-menu compact-version-menu">
                          <button type="button" class="workflow-more-menu__trigger" aria-label="版本操作" :popovertarget="`vsm-card-${previewVideoVersion.id}`">•••</button>
                          <div :id="`vsm-card-${previewVideoVersion.id}`" popover class="workflow-more-menu__popover" @beforetoggle="positionVersionMenu">
                            <button type="button" :disabled="!previewVideoVersion.asset || busyActionKey === `reuse-${previewVideoVersion.id}`" @click="handleReuseAsset(previewVideoVersion.asset?.id || '', previewVideoVersion.id)">复用</button>
                            <a v-if="previewVideoVersion.downloadUrl" :href="previewVideoVersion.downloadUrl" download target="_blank" rel="noopener noreferrer">下载</a>
                            <button type="button" class="workflow-menu-danger" :disabled="busyActionKey === `delete-${previewVideoVersion.id}`" @click="handleDeleteStageVersion(previewVideoVersion)">删除版本</button>
                          </div>
                        </div>
                      </div>
                    </article>
                  </div>
                </article>
              </section>
            </section>

            <section v-else class="workflow-stage-board final-board">
              <div class="stage-board__head">
                <h3>成片</h3>
                <div class="stage-board__meta">
                  <div class="readiness-strip readiness-strip-final stage-board__readiness">
                    <span>总镜头 {{ videoReadiness.total }}</span>
                    <span>已选中 {{ videoReadiness.selected }}</span>
                    <span>{{ finalizeHint }}</span>
                  </div>
                  <button class="btn-primary btn-sm" type="button" :disabled="!canFinalize || busyActionKey === 'finalize'" @click="handleFinalize">
                    {{ busyActionKey === "finalize" ? "拼接中..." : finalizeButtonLabel }}
                  </button>
                </div>
              </div>

              <article v-if="selectedWorkflow.finalResult" class="final-result-card-v2">
                <video v-if="selectedWorkflow.finalResult.previewUrl" class="final-result-card__video" :src="selectedWorkflow.finalResult.previewUrl" controls playsinline preload="metadata"></video>
                <div class="final-result-card-v2__meta">
                  <div class="final-result-card-v2__summary">
                    <h4>{{ selectedWorkflow.finalResult.title }}</h4>
                    <div class="workflow-kv">
                      <div class="workflow-kv__row"><span>时长</span><strong>{{ durationLabel(selectedWorkflow.finalResult.durationSeconds) }}</strong></div>
                    </div>
                  </div>
                  <section v-if="videoReadiness.missing.length" class="missing-clip-list">
                    <div class="missing-clip-list__head">
                      <strong>待补齐镜头</strong>
                      <span class="missing-clip-list__hint">这些分镜还没有选中视频版本，补齐后才能重新拼接完整视频。</span>
                    </div>
                    <div class="missing-clip-list__chips">
                      <button v-for="slot in videoReadiness.missing" :key="`missing-${slot.clipIndex}`" type="button" class="missing-clip-card" @click="selectCanvasClip(slot.clipIndex); switchCanvasStage('video')">
                        {{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}
                      </button>
                    </div>
                  </section>
                  <div class="final-result-card-v2__actions">
                    <a class="btn-primary btn-sm" :href="selectedWorkflow.finalResult.fileUrl" download target="_blank" rel="noopener noreferrer">下载结果视频</a>
                  </div>
                </div>
              </article>
              <div v-else class="workflow-empty workflow-empty-large">
                {{ canFinalize ? "可以拼接完整视频。" : `还有 ${videoReadiness.missing.length} 个镜头未选中视频版本。` }}
              </div>

              <section v-if="!selectedWorkflow.finalResult && videoReadiness.missing.length" class="missing-clip-list">
                <div class="missing-clip-list__head">
                  <strong>待补齐镜头</strong>
                  <span class="missing-clip-list__hint">先为这些分镜选中一个视频版本，才能进行完整视频拼接。</span>
                </div>
                <div class="missing-clip-list__chips">
                  <button v-for="slot in videoReadiness.missing" :key="`missing-${slot.clipIndex}`" type="button" class="missing-clip-card" @click="selectCanvasClip(slot.clipIndex); switchCanvasStage('video')">
                    {{ slot.shotLabel || `镜头 #${slot.clipIndex}` }}
                  </button>
                </div>
              </section>
            </section>
          </main>

        </section>
      </template>

      <section v-else class="surface-panel workflow-panel workflow-empty-large workflow-empty-prompt">
        <h2>请新建画布或选择一个工作流来查看</h2>
        <div class="workflow-empty-prompt__actions">
          <button class="btn-primary btn-sm" type="button" :disabled="creatingWorkflow || loadingOptions" @click="startCreateWorkflow">新建画布</button>
        </div>
      </section>
    </section>
  </section>

  <div
    v-if="characterSummaryPreviewState.open"
    class="character-summary-dialog-overlay"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    @click.self="closeCharacterSummaryPreview"
  >
    <div class="character-summary-dialog">
      <div class="character-summary-dialog__head">
        <div>
          <p class="workflow-eyebrow">Character Summary</p>
          <h4>{{ characterSummaryPreviewState.title }}</h4>
        </div>
        <button type="button" class="character-summary-dialog__close" aria-label="关闭角色定义弹窗" @click="closeCharacterSummaryPreview">关闭</button>
      </div>
      <p class="character-summary-dialog__content">{{ characterSummaryPreviewState.content }}</p>
    </div>
  </div>

  <div
    v-if="imagePreviewState.open"
    ref="imagePreviewOverlayRef"
    class="image-preview-overlay"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    @click.self="closeImagePreview"
  >
    <div class="image-preview-caption">
      <strong>{{ imagePreviewCaption }}</strong>
      <span v-if="imagePreviewState.gallery.length > 1">按 ← / → 切换首尾帧</span>
    </div>
    <button type="button" class="image-preview-close" aria-label="关闭原图预览" @click="closeImagePreview">关闭</button>
    <img class="image-preview-full" :src="imagePreviewState.url" :alt="imagePreviewState.alt" />
  </div>
</template>
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { requireAuth } from "@/auth/modal";
import {
  adjustStoryboard,
  createWorkflow,
  deleteStageVersion,
  deleteWorkflow,
  fetchWorkflow,
  fetchWorkflows,
  finalizeWorkflow,
  generateKeyframe,
  generateKeyframeFrame,
  generateStoryboard,
  generateVideo,
  reuseMaterialAsset,
  selectCharacterSheetAsset,
  selectKeyframe,
  selectKeyframeFrame,
  selectStoryboard,
  selectVideo,
  updateWorkflowSettings,
} from "@/features/workflows";
import {
  normalizeWorkflowCanvasStage,
  normalizeWorkflowDetailStage,
  summaryFrameFailures,
  summaryNumberValue,
  summaryUrlListValue,
  summaryUrlValue,
  workflowCanvasStageFromCurrent as resolveWorkflowCanvasStageFromCurrent,
  workflowStageLabel,
  workflowSummaryCanvasStage,
  workflowSummaryCharacterCountLabel,
} from "@/features/workflows/summary";
import type { WorkflowCanvasStageKey, WorkflowCreateStageKey, WorkflowDetailRouteStageKey } from "@/features/workflows/summary";
import { formatApiErrorMessage } from "@/utils/api-error";
import { messageApi } from "@/composables/useMessage";
import { renderMarkdownToHtml } from "@/utils/markdown";
import type {
  CreateWorkflowRequest,
  StageVersion,
  UpdateWorkflowSettingsRequest,
  WorkflowCharacterSheet,
  WorkflowClipSlot,
  WorkflowDeleteResult,
  WorkflowDetail,
  WorkflowSummary,
} from "@/types";
import { useWorkflowOptions } from "@/composables/workflow/useWorkflowOptions";
import { useWorkflowList } from "@/composables/workflow/useWorkflowList";
import { useCreateWorkflow } from "@/composables/workflow/useCreateWorkflow";
import { useImagePreview } from "@/composables/workflow/useImagePreview";
import { useCharacterAssetPicker } from "@/composables/workflow/useCharacterAssetPicker";
import {
  characterSheetKey,
  characterSheetClipIndex,
  characterSheetTitle,
  characterSheetAppearanceSummary,
  characterSheetVersions,
  selectedCharacterSheetVersion,
  hasMissingCharacterSheets,
  characterSheetPreviewFrames,
} from "@/composables/workflow/useCharacterSheetUtils";
import WorkflowStagePipeline from "./workflow/components/WorkflowStagePipeline.vue";
import ImagePreviewOverlay from "./workflow/components/ImagePreviewOverlay.vue";
import { IconSearch, IconClose, IconMore, IconLoading, IconEmpty } from "@/components/icons";

type CreateStageKey = WorkflowCreateStageKey;
type DetailRouteStageKey = WorkflowDetailRouteStageKey;
type CanvasStageKey = WorkflowCanvasStageKey;

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

interface PreviewFrame {
  role: string;
  label: string;
  url: string;
  selected?: boolean;
  regenerable?: boolean;
  errorMessage?: string;
}

interface ImagePreviewItem {
  url: string;
  alt: string;
  caption: string;
}

const router = useRouter();
const route = useRoute();

// --- Composables ---
const workflowOptions = useWorkflowOptions();
const workflowList = useWorkflowList();
const createWorkflowState = useCreateWorkflow(workflowOptions);
const imagePreview = useImagePreview();
const characterAssetPickerState = useCharacterAssetPicker();

const {
  loadingOptions, options, aspectRatioOptions, stylePresetOptions,
  textModelOptions, imageModelOptions, videoModelOptions, catalogVideoSizeOptions,
  filterVideoSizeOptions, syncVideoSizeSelection, valueOptionLabel, keyOptionLabel, loadOptions,
} = workflowOptions;

const {
  loadingWorkflows, workflowSearch, workflowSearchInput, workflows,
  filteredWorkflows, focusWorkflowSearch, clearWorkflowSearch,
  workflowCompletionPercentage, loadWorkflows,
} = workflowList;

const {
  creatingWorkflow, createComposerVisible, createComposerMenu, createStatusText,
  createTextFileInput, uploadingCreateText, storyboardDurationMode,
  storyboardManualDurationSeconds, STORYBOARD_MANUAL_DURATION_MIN_SECONDS,
  STORYBOARD_MANUAL_DURATION_MAX_SECONDS, createForm, videoSizeOptions,
  normalizedStoryboardManualDurationSeconds, storyboardManualDurationValidationMessage,
  isStoryboardDurationConfigured, createTranscriptCharacterCount, createModelMenuLabel,
  createOutputMenuLabel, createDurationMenuLabel, createSeedMenuLabel,
  createReviewSections, createReviewRequiredItems, createReviewConfiguredCount,
  canSubmitCreateReview, toggleCreateComposerMenu,
  startCreateWorkflow,
  closeCreateReview: closeCreateReviewBase,
  handleCreateTextFileChange, handleCreateWorkflow: handleCreateWorkflowBase,
  readTextFile, optionalInteger, seedLabel,
} = createWorkflowState;

const {
  imagePreviewOverlayRef, imagePreviewTriggerRef, imagePreviewState,
  imagePreviewCaption, openImagePreview, closeImagePreview, switchImagePreviewFrame,
  captureImagePreviewTrigger, focusImagePreviewOverlay, applyImagePreviewItem,
} = imagePreview;

const {
  characterAssetPicker, materialAssetPreviewUrl, materialAssetModelLabel,
  isCharacterAssetPickerOpen, openCharacterAssetPicker, closeCharacterAssetPicker,
  loadCharacterAssetCandidates,
} = characterAssetPickerState;

const loadingDetail = ref(false);
const busyActionKey = ref("");
const activeCreateStage = ref<DetailRouteStageKey>("storyboard");
const activeCanvasStage = ref<CanvasStageKey>("storyboard");
const previewStoryboardVersionId = ref("");
const previewCharacterSheetVersionIds = reactive<Record<string, string>>({});
const selectedCanvasClipIndex = ref<number | null>(null);
const previewKeyframeVersionIds = reactive<Record<number, string>>({});
const previewVideoVersionIds = reactive<Record<number, string>>({});
const characterSummaryPreviewState = reactive({
  open: false,
  title: "",
  content: "",
});
const selectedWorkflow = ref<WorkflowDetail | null>(null);

const storyboardAdjustmentDrafts = reactive<Record<string, string>>({});
const workflowSettingsOpen = ref(false);
const workflowSettingsDraft = reactive({
  aspectRatio: "16:9",
  stylePreset: "",
  textAnalysisModel: "",
  imageModel: "",
  videoModel: "",
  videoSize: "",
  keyframeSeed: "",
  videoSeed: "",
  durationMode: "auto" as "auto" | "manual",
  minDurationSeconds: "5",
  maxDurationSeconds: "12",
});
const selectedWorkflowId = computed(() => {
  const workflowId = route.params.workflowId;
  return typeof workflowId === "string" ? workflowId : "";
});

const showDetailLoadFailed = computed(
  () => selectedWorkflowId.value !== "" && !selectedWorkflow.value && !loadingDetail.value
);

const workflowCharacterSheets = computed(() => selectedWorkflow.value?.characterSheets ?? []);
const missingCharacterSheets = computed(() =>
  workflowCharacterSheets.value.filter((sheet) => !selectedCharacterSheetVersion(sheet))
);
const selectedStoryboardVersion = computed(() => {
  const versions = selectedWorkflow.value?.storyboardVersions ?? [];
  if (!versions.length) {
    return null;
  }
  return (
    versions.find((version) => version.id === previewStoryboardVersionId.value)
    ?? versions.find((version) => version.selected)
    ?? versions[0]
  );
});
const selectedCanvasClip = computed(() => {
  const slots = selectedWorkflow.value?.clipSlots ?? [];
  if (!slots.length) {
    return null;
  }
  return slots.find((slot) => slot.clipIndex === selectedCanvasClipIndex.value) ?? slots[0];
});
const previewKeyframeVersion = computed(() => {
  const clip = selectedCanvasClip.value;
  if (!clip) {
    return null;
  }
  const previewId = previewKeyframeVersionIds[clip.clipIndex] || "";
  return clip.keyframeVersions.find((version) => version.id === previewId)
    ?? clip.keyframeVersions.find((version) => version.selected)
    ?? clip.keyframeVersions[0]
    ?? null;
});
const previewVideoVersion = computed(() => {
  const clip = selectedCanvasClip.value;
  if (!clip) {
    return null;
  }
  const previewId = previewVideoVersionIds[clip.clipIndex] || "";
  return clip.videoVersions.find((version) => version.id === previewId)
    ?? clip.videoVersions.find((version) => version.selected)
    ?? clip.videoVersions[0]
    ?? null;
});
const selectedStageVersion = computed(() => {
  if (activeCanvasStage.value === "storyboard") {
    return selectedStoryboardVersion.value;
  }
  if (activeCanvasStage.value === "character") {
    const sheet = workflowCharacterSheets.value.find((item) => Boolean(selectedCharacterSheetVersion(item))) ?? workflowCharacterSheets.value[0];
    return sheet ? previewCharacterSheetVersion(sheet) : null;
  }
  if (activeCanvasStage.value === "keyframe") {
    return previewKeyframeVersion.value;
  }
  if (activeCanvasStage.value === "video") {
    return previewVideoVersion.value;
  }
  return null;
});
const videoReadiness = computed(() => {
  const slots = selectedWorkflow.value?.clipSlots ?? [];
  return {
    total: slots.length,
    generated: slots.filter((slot) => slot.videoVersions.length > 0).length,
    selected: slots.filter((slot) => slot.videoVersions.some((version) => version.selected)).length,
    missing: slots.filter((slot) => !slot.videoVersions.some((version) => version.selected)),
  };
});
const canvasStageItems = computed(() => {
  const workflow = selectedWorkflow.value;
  const storyboardCount = workflow?.storyboardVersions.length ?? 0;
  const keyframeCount = workflow?.clipSlots.reduce((sum, slot) => sum + slot.keyframeVersions.length, 0) ?? 0;
  const videoCount = workflow?.clipSlots.reduce((sum, slot) => sum + slot.videoVersions.length, 0) ?? 0;
  const selectedCharacterCount = workflowCharacterSheets.value.filter((sheet) => Boolean(selectedCharacterSheetVersion(sheet))).length;
  return [
    {
      key: "storyboard" as const,
      index: 1,
      label: "分镜脚本",
      status: storyboardCount ? "已有版本" : "待生成",
      count: `${storyboardCount} 版`,
      ready: storyboardCount > 0,
    },
    {
      key: "character" as const,
      index: 2,
      label: "角色三视图",
      status: selectedCharacterCount ? "已有角色" : (storyboardCount ? "可生成" : "等分镜"),
      count: `${selectedCharacterCount}/${workflowCharacterSheets.value.length || 0}`,
      ready: selectedCharacterCount > 0,
    },
    {
      key: "keyframe" as const,
      index: 3,
      label: "关键帧",
      status: keyframeCount ? "已有关键帧" : (storyboardCount ? "可生成" : "等角色"),
      count: `${keyframeCount} 版`,
      ready: keyframeCount > 0,
    },
    {
      key: "video" as const,
      index: 4,
      label: "视频片段",
      status: videoCount ? "已有视频" : (keyframeCount ? "可生成" : "等关键帧"),
      count: `${videoCount} 版`,
      ready: videoCount > 0,
    },
    {
      key: "final" as const,
      index: 5,
      label: "成片",
      status: workflow?.finalResult ? "已拼接" : (canFinalize.value ? "可拼接" : "未就绪"),
      count: workflow?.finalResult ? "已完成" : `${videoReadiness.value.selected}/${videoReadiness.value.total || 0}`,
      ready: Boolean(workflow?.finalResult || canFinalize.value),
    },
  ];
});

// focusWorkflowSearch, clearWorkflowSearch, workflowCompletionPercentage
// are imported from @/composables/workflow/useWorkflowList

// videoSizeOptions is provided by useCreateWorkflow composable
const workflowSettingsVideoSizeOptions = computed(() =>
  filterVideoSizeOptions(catalogVideoSizeOptions.value, workflowSettingsDraft.videoModel, workflowSettingsDraft.aspectRatio)
);
const workflowParameterTags = computed(() => {
  const workflow = selectedWorkflow.value;
  if (!workflow) {
    return [];
  }
  return [
    {
      label: "文本模型",
      value: valueOptionLabel(textModelOptions.value, workflow.textAnalysisModel, workflow.textAnalysisModel || "未设置"),
    },
    {
      label: "关键帧模型",
      value: valueOptionLabel(imageModelOptions.value, workflow.imageModel, workflow.imageModel || "未设置"),
    },
    {
      label: "视频模型",
      value: valueOptionLabel(videoModelOptions.value, workflow.videoModel, workflow.videoModel || "未设置"),
    },
    {
      label: "画幅",
      value: workflow.aspectRatio || "未设置",
    },
    {
      label: "尺寸",
      value: valueOptionLabel(catalogVideoSizeOptions.value, workflow.videoSize, workflow.videoSize || "未设置"),
    },
    {
      label: "关键帧 Seed",
      value: seedLabel(workflow.keyframeSeed),
    },
    {
      label: "视频 Seed",
      value: seedLabel(workflow.videoSeed),
    },
  ];
});
const canFinalize = computed(() => {
  const workflow = selectedWorkflow.value;
  if (!workflow || !workflow.clipSlots.length) {
    return false;
  }
  return workflow.clipSlots.every((slot) => slot.videoVersions.some((version) => version.selected));
});

const finalizeButtonLabel = computed(() => selectedWorkflow.value?.finalResult ? "重新拼接完整视频" : "拼接完整视频");

const finalizeHint = computed(() => {
  const workflow = selectedWorkflow.value;
  if (!workflow || !workflow.clipSlots.length) {
    return "先生成并选中每个分镜的视频版本，才能按分镜顺序拼接成完整视频。";
  }
  if (canFinalize.value) {
    return "会按当前选中的视频版本，依照分镜顺序拼接为完整视频。";
  }
  return "所有分镜都需要先有一个选中的视频版本，之后才能进行拼接。";
});

const workflowSettingsValidationMessage = computed(() => {
  if (!workflowSettingsDraft.textAnalysisModel) {
    return "请选择文本模型";
  }
  if (!workflowSettingsDraft.imageModel) {
    return "请选择关键帧模型";
  }
  if (!workflowSettingsDraft.stylePreset) {
    return "请选择视觉风格";
  }
  if (!workflowSettingsDraft.aspectRatio) {
    return "请选择长宽比";
  }
  if (!workflowSettingsDraft.videoModel) {
    return "请选择视频模型";
  }
  if (!workflowSettingsDraft.videoSize) {
    return "请选择输出尺寸";
  }
  if (workflowSettingsDraft.durationMode === "auto") {
    return "";
  }
  const minDuration = optionalInteger(workflowSettingsDraft.minDurationSeconds);
  const maxDuration = optionalInteger(workflowSettingsDraft.maxDurationSeconds);
  if (minDuration === null || maxDuration === null || minDuration < 1 || maxDuration < 1) {
    return "请填写合法的镜头时长";
  }
  if (maxDuration < minDuration) {
    return "最大时长不能小于最小时长";
  }
  return "";
});

function workflowCanvasStageFromCurrent(workflow: WorkflowDetail): CanvasStageKey {
  return resolveWorkflowCanvasStageFromCurrent(workflow, hasMissingCharacterSheets);
}

function switchCanvasStage(stage: CanvasStageKey) {
  activeCanvasStage.value = stage;
  if (stage === "final") {
    return;
  }
  switchWorkflowStage(stage);
}

function setPreviewStoryboardVersion(versionId: string) {
  previewStoryboardVersionId.value = versionId;
}

function setPreviewCharacterSheetVersion(sheetKey: string, versionId: string) {
  previewCharacterSheetVersionIds[sheetKey] = versionId;
}

function setPreviewKeyframeVersion(clipIndex: number, versionId: string) {
  previewKeyframeVersionIds[clipIndex] = versionId;
}

function setPreviewVideoVersion(clipIndex: number, versionId: string) {
  previewVideoVersionIds[clipIndex] = versionId;
}

function stageVersionDisplayTitle(version: StageVersion) {
  const rawTitle = (version.title || "").trim();
  const versionPrefixPattern = new RegExp(`^V${version.versionNo}[.、\\-_:：·\\s]*`, "i");
  const dedupedTitle = rawTitle.replace(versionPrefixPattern, "").trim();
  return dedupedTitle || rawTitle || "未命名版本";
}

function selectCanvasClip(clipIndex: number) {
  selectedCanvasClipIndex.value = clipIndex;
}

// valueOptionLabel, keyOptionLabel are imported from @/composables/workflow/useWorkflowOptions

// normalizeModelName, resolveVideoSizeAspectRatio, compareVideoSizeByArea,
// filterVideoSizeOptions, syncVideoSizeSelection
// are imported from @/composables/workflow/useWorkflowOptions

function parseStoryboardDurationSeconds(value?: string | null) {
  if (value === undefined || value === null) {
    return null;
  }
  const raw = String(value).trim();
  if (!raw) {
    return null;
  }
  const numericValue = Number(raw);
  if (!Number.isFinite(numericValue) || !Number.isInteger(numericValue)) {
    return null;
  }
  return Math.trunc(numericValue);
}

// seedLabel, readTextFile, optionalInteger
// are imported from @/composables/workflow/useCreateWorkflow

function versionSeed(version: StageVersion) {
  const inputSummary = version.inputSummary ?? {};
  const seed = inputSummary.seed;
  if (seed === undefined || seed === null || seed === "") {
    return null;
  }
  const numericValue = Number(seed);
  return Number.isFinite(numericValue) ? numericValue : null;
}

function durationLabel(value?: number | null) {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? `${value.toFixed(1)}s` : "-";
}

function clipSceneText(slot: WorkflowClipSlot) {
  return (slot.scene?.trim() || "暂无场景描述");
}

function clipSceneSummary(slot: WorkflowClipSlot) {
  const text = clipSceneText(slot);
  return text.length > 120 ? `${text.slice(0, 120)}...` : text;
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

function storyboardPreviewHtml(version: StageVersion) {
  return renderMarkdownToHtml(storyboardPreview(version));
}

function isLandscapeKeyframeVersion(version: StageVersion) {
  const outputSummary = version.outputSummary ?? {};
  const width = summaryNumberValue(outputSummary, "width") || Number(version.asset?.width ?? 0);
  const height = summaryNumberValue(outputSummary, "height") || Number(version.asset?.height ?? 0);
  if (Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
    return width > height;
  }
  const aspectRatio = selectedWorkflow.value?.aspectRatio || "";
  return aspectRatio.trim().startsWith("16:");
}

function keyframePreviewFrames(version: StageVersion, slot?: WorkflowClipSlot): PreviewFrame[] {
  const outputSummary = version.outputSummary ?? {};
  const firstFrameUrl = summaryUrlValue(outputSummary, "startFrameUrl", "firstFrameUrl");
  const frameFailures = summaryFrameFailures(outputSummary);
  const lastFailure = frameFailures.find((item) => item.role === "last");
  const lastFrameUrl = summaryUrlValue(outputSummary, "endFrameUrl", "lastFrameUrl")
    || (!lastFailure ? summaryUrlValue(outputSummary, "fileUrl") || (typeof version.previewUrl === "string" ? version.previewUrl : "") : "");
  const hasExplicitFirstSelection = slot ? slot.keyframeVersions.some((item) => Boolean(item.outputSummary?.selectedFirstFrame)) : false;
  const hasExplicitLastSelection = slot ? slot.keyframeVersions.some((item) => Boolean(item.outputSummary?.selectedLastFrame)) : false;
  const frames: PreviewFrame[] = [];
  if (firstFrameUrl) {
    frames.push({
      role: "first",
      label: "首帧",
      url: firstFrameUrl,
      selected: Boolean(outputSummary.selectedFirstFrame || (!hasExplicitFirstSelection && version.selected)),
      regenerable: version.clipIndex <= 1,
    });
  }
  const firstFailure = frameFailures.find((item) => item.role === "first");
  if (!firstFrameUrl && firstFailure) {
    frames.push({
      role: "first",
      label: "首帧",
      url: "",
      selected: false,
      regenerable: version.clipIndex <= 1,
      errorMessage: firstFailure.message,
    });
  }
  if (lastFrameUrl && (!firstFrameUrl || lastFrameUrl !== firstFrameUrl || version.clipIndex === 1)) {
    frames.push({
      role: "last",
      label: "尾帧",
      url: lastFrameUrl,
      selected: Boolean(outputSummary.selectedLastFrame || (!hasExplicitLastSelection && version.selected)),
      regenerable: true,
    });
  }
  if (!lastFrameUrl && lastFailure) {
    frames.push({
      role: "last",
      label: "尾帧",
      url: "",
      selected: false,
      regenerable: true,
      errorMessage: lastFailure.message,
    });
  }
  return frames;
}

function keyframeVersionHasSelectedFrame(version: StageVersion) {
  const outputSummary = version.outputSummary ?? {};
  return Boolean(version.selected || outputSummary.selectedFirstFrame || outputSummary.selectedLastFrame);
}

// characterSheetKey, characterSheetClipIndex, characterSheetTitle, characterSheetAppearanceSummary
// are imported from @/composables/workflow/useCharacterSheetUtils

function openCharacterSummaryPreview(sheet: WorkflowCharacterSheet) {
  characterSummaryPreviewState.open = true;
  characterSummaryPreviewState.title = characterSheetTitle(sheet);
  characterSummaryPreviewState.content = characterSheetAppearanceSummary(sheet);
}

function closeCharacterSummaryPreview() {
  characterSummaryPreviewState.open = false;
  characterSummaryPreviewState.title = "";
  characterSummaryPreviewState.content = "";
}

// characterSheetVersions, hasMissingCharacterSheets, characterSheetPreviewFrames
// are imported from @/composables/workflow/useCharacterSheetUtils

function previewCharacterSheetVersion(sheet: WorkflowCharacterSheet) {
  const versions = characterSheetVersions(sheet);
  const previewId = previewCharacterSheetVersionIds[characterSheetKey(sheet)] || "";
  return versions.find((version) => version.id === previewId)
    ?? selectedCharacterSheetVersion(sheet)
    ?? versions[0]
    ?? null;
}

// isCharacterAssetPickerOpen, openCharacterAssetPicker, closeCharacterAssetPicker,
// materialAssetPreviewUrl, materialAssetModelLabel, isCharacterSheetSelectableAsset,
// loadCharacterAssetCandidates, characterAssetPicker
// are imported from @/composables/workflow/useCharacterAssetPicker

// openImagePreview, closeImagePreview, switchImagePreviewFrame,
// imagePreviewState, imagePreviewOverlayRef, imagePreviewTriggerRef, imagePreviewCaption
// are imported from @/composables/workflow/useImagePreview

function openKeyframeImagePreview(version: StageVersion, frame: PreviewFrame) {
  if (!frame.url) return;
  const frames = keyframePreviewFrames(version).filter((item) => item.url);
  const gallery = frames.map((item) => ({
    url: item.url,
    alt: `${stageVersionDisplayTitle(version)}${item.label}`,
    caption: `${stageVersionDisplayTitle(version)} ${item.label}`,
  }));
  const currentIndex = Math.max(0, frames.findIndex((item) => item.role === frame.role));
  const currentItem = gallery[currentIndex];
  if (!currentItem) {
    openImagePreview(frame.url, `${stageVersionDisplayTitle(version)}${frame.label}`);
    return;
  }
  imagePreview.captureImagePreviewTrigger();
  imagePreviewState.open = true;
  imagePreviewState.gallery = gallery;
  imagePreview.applyImagePreviewItem(currentItem, currentIndex);
  imagePreview.focusImagePreviewOverlay();
}

function handleImagePreviewKeydown(event: KeyboardEvent) {
  if (characterSummaryPreviewState.open && event.key === "Escape") {
    event.preventDefault();
    closeCharacterSummaryPreview();
    return;
  }
  if (!imagePreviewState.open) return;
  if (event.key === "Escape") { event.preventDefault(); closeImagePreview(); return; }
  if (event.key === "ArrowLeft") { event.preventDefault(); switchImagePreviewFrame(-1); return; }
  if (event.key === "ArrowRight") { event.preventDefault(); switchImagePreviewFrame(1); }
}

function selectedKeyframeVersion(slot: WorkflowClipSlot) {
  return slot.keyframeVersions.find((version) => version.selected) ?? null;
}

function selectedKeyframeFrameVersion(slot: WorkflowClipSlot, frameRole: string) {
  const selectionKey = frameRole === "first" ? "selectedFirstFrame" : "selectedLastFrame";
  return slot.keyframeVersions.find((version) => Boolean(version.outputSummary?.[selectionKey])) ?? selectedKeyframeVersion(slot);
}

function selectedKeyframePreviewFrames(slot: WorkflowClipSlot) {
  const frames: PreviewFrame[] = [];
  const firstVersion = selectedKeyframeFrameVersion(slot, "first");
  const firstFrame = firstVersion ? keyframePreviewFrames(firstVersion, slot).find((frame) => frame.role === "first") : null;
  if (firstFrame) {
    frames.push(firstFrame);
  }
  const lastVersion = selectedKeyframeFrameVersion(slot, "last");
  const lastFrame = lastVersion ? keyframePreviewFrames(lastVersion, slot).find((frame) => frame.role === "last") : null;
  if (lastFrame && (!firstFrame || lastFrame.url !== firstFrame.url || slot.clipIndex === 1)) {
    frames.push(lastFrame);
  }
  return frames;
}


async function closeCreateReview() {
  createComposerVisible.value = false;
  createComposerMenu.value = "";
  selectedWorkflow.value = null;
  if (selectedWorkflowId.value) {
    await router.push("/workflows");
  }
}

function syncWorkflowSettingsDraft(workflow: WorkflowDetail) {
  const minDurationSeconds = workflow.minDurationSeconds === null || workflow.minDurationSeconds === undefined
    ? STORYBOARD_MANUAL_DURATION_MIN_SECONDS
    : workflow.minDurationSeconds;
  const maxDurationSeconds = workflow.maxDurationSeconds === null || workflow.maxDurationSeconds === undefined
    ? STORYBOARD_MANUAL_DURATION_MAX_SECONDS
    : workflow.maxDurationSeconds;
  const durationMode = workflow.durationMode === "manual" ? "manual" : "auto";
  workflowSettingsDraft.aspectRatio = workflow.aspectRatio || "9:16";
  workflowSettingsDraft.stylePreset = workflow.stylePreset || "";
  workflowSettingsDraft.textAnalysisModel = workflow.textAnalysisModel || "";
  workflowSettingsDraft.imageModel = workflow.imageModel || "";
  workflowSettingsDraft.videoModel = workflow.videoModel || "";
  workflowSettingsDraft.videoSize = workflow.videoSize || "";
  workflowSettingsDraft.keyframeSeed = workflow.keyframeSeed === null || workflow.keyframeSeed === undefined ? "" : String(workflow.keyframeSeed);
  workflowSettingsDraft.videoSeed = workflow.videoSeed === null || workflow.videoSeed === undefined ? "" : String(workflow.videoSeed);
  workflowSettingsDraft.durationMode = durationMode;
  workflowSettingsDraft.minDurationSeconds = String(minDurationSeconds);
  workflowSettingsDraft.maxDurationSeconds = String(maxDurationSeconds);
  syncVideoSizeSelection(workflowSettingsDraft, workflow.videoSize);
}

function applyWorkflowDrafts(workflow: WorkflowDetail | null) {
  if (!workflow) {
    workflowSettingsOpen.value = false;
    return;
  }
  syncWorkflowSettingsDraft(workflow);
  for (const version of workflow.storyboardVersions) {
    storyboardAdjustmentDrafts[version.id] ??= "";
  }
  previewStoryboardVersionId.value =
    workflow.storyboardVersions.find((version) => version.id === previewStoryboardVersionId.value)?.id
    ?? workflow.storyboardVersions.find((version) => version.selected)?.id
    ?? workflow.storyboardVersions[0]?.id
    ?? "";
  for (const sheet of workflow.characterSheets ?? []) {
    const sheetKey = characterSheetKey(sheet);
    const versions = characterSheetVersions(sheet);
    previewCharacterSheetVersionIds[sheetKey] =
      versions.find((version) => version.id === previewCharacterSheetVersionIds[sheetKey])?.id
      ?? versions.find((version) => version.selected)?.id
      ?? versions[0]?.id
      ?? "";
  }
  for (const slot of workflow.clipSlots ?? []) {
    previewKeyframeVersionIds[slot.clipIndex] =
      slot.keyframeVersions.find((version) => version.id === previewKeyframeVersionIds[slot.clipIndex])?.id
      ?? slot.keyframeVersions.find((version) => version.selected)?.id
      ?? slot.keyframeVersions[0]?.id
      ?? "";
    previewVideoVersionIds[slot.clipIndex] =
      slot.videoVersions.find((version) => version.id === previewVideoVersionIds[slot.clipIndex])?.id
      ?? slot.videoVersions.find((version) => version.selected)?.id
      ?? slot.videoVersions[0]?.id
      ?? "";
  }
}

function openWorkflow(workflowId: string, preferredStage?: string | null) {
  createComposerVisible.value = false;
  const nextStage = normalizeWorkflowCanvasStage(preferredStage) ?? normalizeWorkflowDetailStage(route.query.stage) ?? activeCreateStage.value;
  activeCanvasStage.value = nextStage;
  if (nextStage === "final") {
    void router.push(`/workflows/${workflowId}`);
    return;
  }
  void router.push({
    path: `/workflows/${workflowId}`,
    query: { stage: nextStage },
  });
}

function switchWorkflowStage(stage: DetailRouteStageKey) {
  activeCreateStage.value = stage;
  activeCanvasStage.value = stage;
  if (!selectedWorkflowId.value) {
    return;
  }
  const currentRouteStage = normalizeWorkflowDetailStage(route.query.stage);
  if (currentRouteStage === stage) {
    return;
  }
  void router.replace({
    path: route.path,
    query: {
      ...route.query,
      stage,
    },
  });
}

async function loadWorkflowDetail(workflowId: string) {
  loadingDetail.value = true;
  try {
    selectedWorkflow.value = await fetchWorkflow(workflowId);
    const routeStage = normalizeWorkflowDetailStage(route.query.stage);
    const resolvedStage = routeStage ?? workflowCanvasStageFromCurrent(selectedWorkflow.value);
    activeCreateStage.value = resolvedStage === "final" ? "video" : resolvedStage;
    activeCanvasStage.value = resolvedStage;
    if (resolvedStage !== "final" && routeStage !== resolvedStage) {
      await router.replace({
        path: route.path,
        query: {
          ...route.query,
          stage: resolvedStage,
        },
      });
    }
    applyWorkflowDrafts(selectedWorkflow.value);
    previewStoryboardVersionId.value =
      selectedWorkflow.value.storyboardVersions.find((version) => version.selected)?.id
      ?? selectedWorkflow.value.storyboardVersions[0]?.id
      ?? "";
    if (selectedWorkflow.value.clipSlots.length) {
      const currentClipExists = selectedWorkflow.value.clipSlots.some((slot) => slot.clipIndex === selectedCanvasClipIndex.value);
      if (!currentClipExists) {
        selectedCanvasClipIndex.value = selectedWorkflow.value.clipSlots[0].clipIndex;
      }
    } else {
      selectedCanvasClipIndex.value = null;
    }
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "工作流详情加载失败");
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
  const fixedDurationSeconds = storyboardDurationMode.value === "manual" ? normalizedStoryboardManualDurationSeconds.value : null;
  return {
    title: createForm.title.trim(),
    transcriptText: createForm.transcriptText.trim() || null,
    aspectRatio: createForm.aspectRatio as "9:16" | "16:9",
    stylePreset: createForm.stylePreset || null,
    textAnalysisModel: createForm.textAnalysisModel,
    imageModel: createForm.imageModel,
    videoModel: createForm.videoModel,
    videoSize: createForm.videoSize || null,
    keyframeSeed: createForm.keyframeSeed === "" ? null : Number(createForm.keyframeSeed),
    videoSeed: createForm.videoSeed === "" ? null : Number(createForm.videoSeed),
    durationMode: storyboardDurationMode.value,
    minDurationSeconds: fixedDurationSeconds,
    maxDurationSeconds: fixedDurationSeconds,
  };
}

function buildWorkflowSettingsPayload(): UpdateWorkflowSettingsRequest {
  return {
    aspectRatio: workflowSettingsDraft.aspectRatio,
    stylePreset: workflowSettingsDraft.stylePreset,
    textAnalysisModel: workflowSettingsDraft.textAnalysisModel,
    imageModel: workflowSettingsDraft.imageModel,
    videoModel: workflowSettingsDraft.videoModel,
    videoSize: workflowSettingsDraft.videoSize,
    keyframeSeed: optionalInteger(workflowSettingsDraft.keyframeSeed),
    videoSeed: optionalInteger(workflowSettingsDraft.videoSeed),
    durationMode: workflowSettingsDraft.durationMode,
    minDurationSeconds: workflowSettingsDraft.durationMode === "auto" ? null : optionalInteger(workflowSettingsDraft.minDurationSeconds),
    maxDurationSeconds: workflowSettingsDraft.durationMode === "auto" ? null : optionalInteger(workflowSettingsDraft.maxDurationSeconds),
  };
}

async function handleCreateWorkflow() {
  if (storyboardDurationMode.value === "manual" && storyboardManualDurationValidationMessage.value) {
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后创建画布",
    message: "阶段工作流会保存到你的账号下，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    return;
  }
  creatingWorkflow.value = true;
  createStatusText.value = "正在创建画布...";
  try {
    const workflow = await createWorkflow(buildCreatePayload());
    createForm.title = "";
    createForm.transcriptText = "";
    createForm.keyframeSeed = "";
    createForm.videoSeed = "";
    storyboardDurationMode.value = "auto";
    storyboardManualDurationSeconds.value = "8";
    createComposerMenu.value = "";
    createStatusText.value = "画布创建完成，正在进入阶段工作流。";
    createComposerVisible.value = false;
    await loadWorkflows();
    openWorkflow(workflow.id, workflow.currentStage);
  } catch (error) {
    const message = formatApiErrorMessage(error, "创建工作流失败");
    createStatusText.value = message;
  } finally {
    creatingWorkflow.value = false;
  }
}

function resetTransientStageState() {
  closeCharacterAssetPicker();
  workflowSettingsOpen.value = false;
}

async function runAndRefresh(actionKey: string, runner: () => Promise<WorkflowDetail>) {
  const authenticated = await requireAuth({
    title: "登录后操作工作流",
    message: "工作流操作会修改你的个人数据，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续操作工作流。");
    return false;
  }
  busyActionKey.value = actionKey;
  try {
    selectedWorkflow.value = await runner();
    applyWorkflowDrafts(selectedWorkflow.value);
    await loadWorkflows();
    return true;
  } catch (error) {
    messageApi.error(formatApiErrorMessage(error, "操作失败"));
    return false;
  } finally {
    busyActionKey.value = "";
  }
}

async function handleUpdateWorkflowSettings() {
  if (!selectedWorkflowId.value || workflowSettingsValidationMessage.value) {
    return;
  }
  const succeeded = await runAndRefresh("workflow-settings", () => updateWorkflowSettings(selectedWorkflowId.value, buildWorkflowSettingsPayload()));
  if (succeeded) {
    workflowSettingsOpen.value = false;
  }
}

async function handleGenerateStoryboard() {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh("storyboard", () => generateStoryboard(selectedWorkflowId.value));
}

async function handleAdjustStoryboard(versionId: string) {
  if (!selectedWorkflowId.value) {
    return;
  }
  const prompt = (storyboardAdjustmentDrafts[versionId] || "").trim();
  const succeeded = await runAndRefresh(`storyboard-adjust-${versionId}`, () => adjustStoryboard(selectedWorkflowId.value, versionId, prompt));
  if (succeeded) {
    storyboardAdjustmentDrafts[versionId] = "";
  }
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

async function handleGenerateMissingCharacterSheets() {
  if (!selectedWorkflowId.value) {
    return;
  }
  const pendingClipIndexes = missingCharacterSheets.value
    .map((sheet) => characterSheetClipIndex(sheet))
    .filter((clipIndex): clipIndex is number => clipIndex !== null);
  if (!pendingClipIndexes.length) {
    return;
  }
  busyActionKey.value = "character-missing";
  try {
    for (const clipIndex of pendingClipIndexes) {
      selectedWorkflow.value = await generateKeyframe(selectedWorkflowId.value, clipIndex);
      applyWorkflowDrafts(selectedWorkflow.value);
    }
    await loadWorkflows();
  } catch (error) {
    messageApi.error(formatApiErrorMessage(error, "角色三视图生成失败"));
  } finally {
    busyActionKey.value = "";
  }
}

async function handleGenerateKeyframeFrame(clipIndex: number, frameRole: string) {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh(`keyframe-${clipIndex}-${frameRole}`, () => generateKeyframeFrame(selectedWorkflowId.value, clipIndex, frameRole));
}

async function handleSelectKeyframe(clipIndex: number, versionId: string) {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh(versionId, () => selectKeyframe(selectedWorkflowId.value, clipIndex, versionId));
}

async function handleSelectKeyframeFrame(clipIndex: number, versionId: string, frameRole: string) {
  if (!selectedWorkflowId.value) {
    return;
  }
  await runAndRefresh(`${versionId}-${frameRole}`, () => selectKeyframeFrame(selectedWorkflowId.value, clipIndex, versionId, frameRole));
}

async function handleSelectCharacterSheetAsset(sheet: WorkflowCharacterSheet, assetId: string) {
  const clipIndex = characterSheetClipIndex(sheet);
  if (!selectedWorkflowId.value || clipIndex === null) {
    return;
  }
  busyActionKey.value = `character-sheet-asset-${clipIndex}`;
  try {
    await selectCharacterSheetAsset(selectedWorkflowId.value, clipIndex, assetId);
    closeCharacterAssetPicker();
    await reloadCurrentWorkflow();
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "角色三视图素材选择失败");
  } finally {
    busyActionKey.value = "";
  }
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

function stageTypeLabel(stageType: StageVersion["stageType"]) {
  switch (stageType) {
    case "storyboard":
      return "分镜";
    case "keyframe":
      return "关键帧";
    case "video":
      return "视频";
    default:
      return "版本";
  }
}

function deleteWorkflowConfirmMessage(workflow: WorkflowSummary) {
  return `删除后不可恢复，工作流《${workflow.title}》及其所有生成版本都会一并删除。确认继续吗？`;
}

function deleteVersionConfirmMessage(version: StageVersion) {
  const stageLabel = stageTypeLabel(version.stageType);
  if (version.stageType === "storyboard") {
    return `删除后不可恢复。删除该${stageLabel}版本时，与它关联的关键帧和视频版本也会一并删除。确认继续吗？`;
  }
  if (version.stageType === "keyframe") {
    return `删除后不可恢复。删除该${stageLabel}版本时，依赖它生成的视频版本也会一并删除。确认继续吗？`;
  }
  return `删除后不可恢复，确认删除这个${stageLabel}版本吗？`;
}

async function handleDeleteWorkflow(workflow: WorkflowSummary) {
  const authenticated = await requireAuth({
    title: "登录后删除工作流",
    message: "删除工作流会修改你的个人数据，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续删除工作流。");
    return;
  }
  if (!window.confirm(deleteWorkflowConfirmMessage(workflow))) {
    return;
  }
  const actionKey = `delete-workflow-${workflow.id}`;
  busyActionKey.value = actionKey;
  try {
    const result: WorkflowDeleteResult = await deleteWorkflow(workflow.id);
    if (result.deleted && selectedWorkflowId.value === workflow.id) {
      selectedWorkflow.value = null;
      await router.push("/workflows");
    }
    await loadWorkflows();
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "工作流删除失败");
  } finally {
    busyActionKey.value = "";
  }
}

async function handleDeleteStageVersion(version: StageVersion) {
  const authenticated = await requireAuth({
    title: "登录后删除版本",
    message: "删除版本会修改你的工作流数据，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续删除版本。");
    return;
  }
  if (!selectedWorkflowId.value || !window.confirm(deleteVersionConfirmMessage(version))) {
    return;
  }
  const actionKey = `delete-${version.id}`;
  busyActionKey.value = actionKey;
  try {
    selectedWorkflow.value = await deleteStageVersion(selectedWorkflowId.value, version.id);
    applyWorkflowDrafts(selectedWorkflow.value);
    await loadWorkflows();
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "版本删除失败");
  } finally {
    busyActionKey.value = "";
  }
}

async function handleReuseAsset(assetId: string, versionId: string) {
  if (!assetId) {
    return;
  }
  const authenticated = await requireAuth({
    title: "登录后复用素材",
    message: "复用素材会创建你的阶段工作流，请先登录或使用邀请码注册。",
  });
  if (!authenticated) {
    messageApi.warning("登录后可继续复用素材。");
    return;
  }
  busyActionKey.value = `reuse-${versionId}`;
  try {
    const workflow = await reuseMaterialAsset(assetId, { mode: "clone" });
    await loadWorkflows();
    openWorkflow(workflow.id, workflow.currentStage);
  } catch (error) {
    messageApi.error(error instanceof Error ? error.message : "素材复用失败");
  } finally {
    busyActionKey.value = "";
  }
}

function positionVersionMenu(event: ToggleEvent) {
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

function closeOpenWorkflowMenus(exceptTarget?: EventTarget | null) {
  const activeNode = exceptTarget instanceof Node ? exceptTarget : null;
  const menus = document.querySelectorAll<HTMLDetailsElement>(".workflow-more-menu[open]");
  menus.forEach((menu) => {
    if (activeNode && menu.contains(activeNode)) {
      return;
    }
    menu.open = false;
  });
  document.querySelectorAll<HTMLElement>(".workflow-more-menu__popover").forEach((popover) => {
    if (!popover.matches(":popover-open")) return;
    if (activeNode && popover.contains(activeNode)) return;
    popover.hidePopover();
  });
}

function handleWorkflowMenuPointerDown(event: PointerEvent) {
  closeOpenWorkflowMenus(event.target);
  const target = event.target instanceof Element ? event.target : null;
  if (target && !target.closest(".workflow-create-menu")) {
    createComposerMenu.value = "";
  }
}

function handleWorkflowMenuKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape") {
    return;
  }
  closeOpenWorkflowMenus(null);
}

watch(
  () => [createForm.videoModel, createForm.aspectRatio, catalogVideoSizeOptions.value] as const,
  () => {
    syncVideoSizeSelection(createForm, createForm.videoSize);
  }
);

watch(
  () => [workflowSettingsDraft.videoModel, workflowSettingsDraft.aspectRatio, catalogVideoSizeOptions.value] as const,
  () => {
    syncVideoSizeSelection(workflowSettingsDraft, workflowSettingsDraft.videoSize);
  }
);

watch(
  () => route.query.stage,
  (stage) => {
    if (!selectedWorkflowId.value) {
      return;
    }
    const resolvedStage = normalizeWorkflowDetailStage(stage);
    if (resolvedStage && resolvedStage !== activeCreateStage.value) {
      activeCreateStage.value = resolvedStage;
      activeCanvasStage.value = resolvedStage;
    }
  }
);

watch(
  () => route.query.create,
  (createFlag) => {
    if (String(createFlag || "") !== "1") {
      return;
    }
    startCreateWorkflow();
  },
  { immediate: true }
);

watch(
  () => selectedWorkflowId.value,
  (workflowId) => {
    if (!workflowId) {
      selectedWorkflow.value = null;
      resetTransientStageState();
      return;
    }
    resetTransientStageState();
    void loadWorkflowDetail(workflowId);
  },
  { immediate: true }
);

onMounted(async () => {
  document.addEventListener("pointerdown", handleWorkflowMenuPointerDown);
  document.addEventListener("keydown", handleWorkflowMenuKeydown);
  window.addEventListener("keydown", handleImagePreviewKeydown);
  await loadOptions();
  await loadWorkflows();
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", handleWorkflowMenuPointerDown);
  document.removeEventListener("keydown", handleWorkflowMenuKeydown);
  window.removeEventListener("keydown", handleImagePreviewKeydown);
});
</script>

<style scoped>
.workflow-canvas-view {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 0;
  height: 100%;
  min-height: 0;
  padding: 22px;
  color: var(--text-strong);
  overflow: hidden;
  background: #fff;
}

.workflow-project-drawer,
.workflow-inspector,
.workflow-stage-board,
.workflow-create-inspector,
.workflow-canvas-header,
.workflow-stage-pipeline,
.character-mini-card,
.clip-detail-card,
.storyboard-preview-card,
.final-result-card-v2,
.inspector-section {
  border: 1px solid rgba(15, 20, 25, 0.07);
  background: #fff;
  box-shadow: var(--shadow-soft);
}

.workflow-project-drawer {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  padding: 12px;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  overflow: visible;
}

.workflow-canvas-header,
.stage-board__head,
.inspector-section__head,
.clip-detail-card__head,
.workflow-create-title,
.video-version-card__head,
.final-result-card-v2__meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.workflow-canvas-header h2,
.stage-board__head h3,
.inspector-section__head h3,
.workflow-create-title h2,
.storyboard-preview-card h4,
.clip-detail-card h4,
.final-result-card-v2 h4 {
  margin: 0;
  color: var(--text-strong);
  letter-spacing: -0.02em;
}

.workflow-canvas-header {
  align-items: flex-start;
  gap: 18px;
  padding: 16px 18px;
}

.workflow-canvas-header__body {
  display: grid;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.workflow-canvas-header__body h2 {
  min-width: 0;
}

.workflow-canvas-header__summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.workflow-eyebrow {
  margin: 0 0 2px;
  color: var(--text-muted);
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.workflow-composer-submit {
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  cursor: pointer;
}

.workflow-search-box,
.workflow-field {
  display: grid;
  gap: 8px;
}

.workflow-search-box__control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: stretch;
  min-height: 54px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 20px;
  background: #fff;
  overflow: hidden;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.workflow-search-box__control:focus-within {
  border-color: rgba(124, 58, 237, 0.42);
  box-shadow:
    0 0 0 3px rgba(124, 58, 237, 0.1),
    0 10px 26px rgba(15, 20, 25, 0.06);
}

.workflow-search-box__field.field-input {
  min-width: 0;
  height: 100%;
  border: 0;
  border-radius: 0;
  padding: 0 1.15rem;
  background: transparent;
  box-shadow: none;
}

.workflow-search-box__field.field-input:focus {
  border-color: transparent;
  box-shadow: none;
}

.workflow-search-box__button {
  min-width: 88px;
  border: 0;
  border-left: 1px solid rgba(15, 20, 25, 0.08);
  padding: 0 1.2rem;
  background: linear-gradient(135deg, rgba(0, 196, 220, 0.12), rgba(36, 107, 254, 0.12));
  color: var(--text-strong);
  font-size: 0.92rem;
  font-weight: 700;
  cursor: pointer;
  transition:
    background 180ms ease,
    color 180ms ease;
}

.workflow-search-box__button:hover {
  background: linear-gradient(135deg, rgba(0, 196, 220, 0.2), rgba(36, 107, 254, 0.2));
}

.workflow-search-box__button:active {
  background: linear-gradient(135deg, rgba(0, 196, 220, 0.26), rgba(36, 107, 254, 0.26));
}

.workflow-search-box span,
.workflow-field span {
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 700;
}

.workflow-search-box {
  position: relative;
}

.workflow-search-box__icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  pointer-events: none;
  z-index: 2;
}

.workflow-search-box__field.field-input {
  min-width: 0;
  height: 100%;
  border: 0;
  border-radius: 0;
  padding: 0 1.15rem 0 40px;
  background: transparent;
  box-shadow: none;
  transition: border-color 180ms ease;
}

.workflow-search-box__field.field-input:focus {
  border-color: transparent;
  box-shadow: none;
}

.workflow-search-box__clear {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transition: opacity 180ms ease, transform 180ms ease;
}

.workflow-search-box__clear:hover {
  background: rgba(15, 20, 25, 0.08);
  opacity: 1;
  transform: translateY(-50%) scale(1.05);
}

.workflow-search-box__field.field-input:focus + .workflow-search-box__clear,
.workflow-search-box__field.field-input:not(:placeholder-shown) + .workflow-search-box__clear {
  opacity: 1;
  pointer-events: auto;
}

.workflow-search-box__control {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: stretch;
  min-height: 54px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 20px;
  background: #fff;
  overflow: hidden;
  transition:
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
  box-shadow: var(--shadow-soft);
}

.workflow-search-box__control:focus-within {
  border-color: rgba(124, 58, 237, 0.42);
  box-shadow:
    0 0 0 3px rgba(124, 58, 237, 0.1),
    0 10px 26px rgba(15, 20, 25, 0.06);
}

.workflow-project-list {
  display: grid;
  gap: 10px;
  min-height: 0;
  overflow: auto;
  padding-right: 2px;
}

.workflow-project-list {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: auto;
}

.workflow-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 150ms ease;
  position: relative;
}

.workflow-nav-item:hover {
  background: rgba(0, 0, 0, 0.04);
}

.workflow-nav-item-active {
  background: rgba(124, 58, 237, 0.08);
}

.workflow-nav-item__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.15);
  flex-shrink: 0;
  transition: background 150ms ease;
}

.workflow-nav-item__dot-active {
  background: var(--accent-cyan);
}

.workflow-nav-item__title {
  flex: 1;
  min-width: 0;
  font-size: 0.88rem;
  font-weight: 500;
  color: var(--text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workflow-nav-item-active .workflow-nav-item__title {
  font-weight: 700;
}

.workflow-nav-item__menu {
  opacity: 0;
  transition: opacity 150ms ease;
}

.workflow-nav-item:hover .workflow-nav-item__menu {
  opacity: 1;
}

.workflow-empty-state {
  display: grid;
  gap: 12px;
  padding: 40px 20px;
  text-align: center;
  color: var(--text-body);
}

.workflow-empty-state__icon {
  display: grid;
  place-items: center;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(124, 58, 237, 0.06);
  color: var(--accent-cyan);
  margin: 0 auto 4px;
}

.workflow-empty-state__text {
  margin: 0;
  font-size: 0.9rem;
  color: var(--text-strong);
}

.workflow-empty-state__hint {
  margin: 0;
  font-size: 0.8rem;
  color: var(--text-muted);
}

.workflow-summary__meta,
.readiness-strip,
.character-mini-card__actions,
.version-card__actions,
.rating-row,
.workflow-inspector-actions,
.character-asset-card__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
}

.workflow-summary__parameter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.workflow-summary__parameter-tags-header {
  min-width: 0;
  flex: 1;
  flex-wrap: nowrap;
  overflow-x: auto;
}

.workflow-canvas-header__settings-button {
  flex-shrink: 0;
}

.workflow-summary-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  max-width: 100%;
  padding: 6px 10px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 999px;
  background: #f8fafb;
}

.workflow-summary__meta-compact {
  flex-shrink: 0;
  justify-content: flex-end;
}

.workflow-summary__meta-compact .surface-chip {
  min-height: 30px;
  padding: 6px 12px;
}

.workflow-summary-tag__label {
  color: var(--text-muted);
  font-size: 0.68rem;
  font-weight: 700;
  white-space: nowrap;
}

.workflow-summary-tag__value {
  color: var(--text-strong);
  font-size: 0.74rem;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.workflow-header-settings {
  display: grid;
  gap: 14px;
  margin-top: 4px;
  padding: 18px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  border-radius: 20px;
  background: #f8fafb;
}

.workflow-header-settings__head h3 {
  margin: 0;
  color: var(--text-strong);
  letter-spacing: -0.02em;
}

.workflow-header-settings__form {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.workflow-header-settings__error {
  grid-column: 1 / -1;
  margin: 0;
}

.workflow-header-settings__actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.workflow-more-menu {
  position: relative;
  padding: 8px 8px 0 0;
}

.workflow-more-menu summary {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  color: var(--text-muted);
  font-size: 0.9rem;
  line-height: 1;
  cursor: pointer;
  list-style: none;
}

.workflow-more-menu summary::-webkit-details-marker {
  display: none;
}

.workflow-more-menu[open] summary,
.workflow-more-menu summary:hover {
  background: #eef2f4;
  color: var(--text-strong);
}

.workflow-more-menu__panel {
  box-shadow: var(--shadow-panel);
}

.workflow-more-menu__trigger {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--text-muted);
  font-size: 0.9rem;
  line-height: 1;
  cursor: pointer;
}

.workflow-more-menu__trigger:hover {
  background: #eef2f4;
  color: var(--text-strong);
}

.workflow-more-menu__popover {
  position: fixed;
  inset: unset;
  width: 150px;
  padding: 0;
  border: 0;
  border-radius: 12px;
  background: transparent;
  box-shadow: none;
  overflow: visible;
}

.workflow-more-menu__popover > button,
.workflow-more-menu__popover > a {
  display: flex;
  width: 100%;
  min-height: 34px;
  align-items: center;
  padding: 0 12px;
  border: 0;
  border-bottom: 1px solid rgba(15, 20, 25, 0.06);
  background: #fff;
  color: var(--text-strong);
  font-size: 0.8rem;
  text-align: left;
  cursor: pointer;
}

.workflow-more-menu__popover > button:first-child,
.workflow-more-menu__popover > a:first-child {
  border-radius: 12px 12px 0 0;
}

.workflow-more-menu__popover > button:last-child,
.workflow-more-menu__popover > a:last-child {
  border-bottom: 0;
  border-radius: 0 0 12px 12px;
}

.workflow-more-menu__popover:popover-open {
  box-shadow: var(--shadow-panel);
}

.workflow-menu-danger {
  color: var(--accent-danger) !important;
}

.workflow-canvas-main {
  display: flex;
  flex-direction: column;
  gap: 0;
  min-width: 0;
  min-height: 0;
  padding: 18px;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  overflow: auto;
}

.workflow-canvas-main > * + * {
  border-top: 1px solid rgba(15, 20, 25, 0.07);
}

.workflow-create-board,
.workflow-canvas-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.workflow-create-board {
  grid-template-columns: minmax(0, 1fr);
}

.workflow-create-shell {
  display: grid;
  gap: 22px;
  width: min(100%, 1120px);
  margin: 0 auto;
  padding: 26px 8px 40px;
}

.workflow-create-hero {
  display: grid;
  gap: 10px;
  justify-items: center;
  text-align: center;
  padding: 28px 24px 0;
}

.workflow-create-hero h2 {
  margin: 0;
  max-width: 12ch;
  font-size: clamp(2rem, 4.4vw, 3.1rem);
  line-height: 1.15;
  letter-spacing: -0.04em;
  color: var(--text-strong);
}

.workflow-create-hero p:last-child {
  margin: 0;
  max-width: 62ch;
  color: var(--text-body);
  line-height: 1.7;
}

.workflow-composer-card {
  position: relative;
  display: grid;
  gap: 16px;
  width: 100%;
  border-radius: 28px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  background: #fff;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.96) inset,
    0 1px 2px rgba(15, 20, 25, 0.03),
    0 12px 28px rgba(20, 28, 36, 0.04);
}

.workflow-composer-card-chat {
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
  gap: 18px;
  min-height: 360px;
  padding: 22px;
}

.workflow-composer-upload {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 10px;
  width: 92px;
  min-height: 120px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff, #f4f7f9);
  color: var(--text-muted);
  cursor: pointer;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7);
}

.workflow-composer-upload span {
  font-size: 1.8rem;
  line-height: 1;
  color: var(--text-body);
}

.workflow-composer-upload small {
  font-size: 0.74rem;
  font-weight: 800;
}

.workflow-hidden-input {
  display: none;
}

.workflow-composer-fields {
  display: grid;
  grid-column: 2;
  grid-row: 1;
  gap: 18px;
  min-width: 0;
}

.workflow-composer-title-field,
.workflow-composer-body-field {
  display: grid;
  gap: 8px;
}

.workflow-composer-title-field span,
.workflow-composer-body-field span {
  color: var(--text-muted);
  font-size: 0.74rem;
  font-weight: 800;
}

.workflow-composer-title-field input,
.workflow-composer-body-field textarea {
  width: 100%;
  appearance: none;
  -webkit-appearance: none;
  border: 0;
  outline: 0;
  background: transparent;
  box-shadow: none;
  color: var(--text-strong);
  resize: vertical;
}

.workflow-composer-title-field input:focus,
.workflow-composer-title-field input:focus-visible,
.workflow-composer-title-field input:invalid,
.workflow-composer-body-field textarea:focus,
.workflow-composer-body-field textarea:focus-visible,
.workflow-composer-body-field textarea:invalid {
  border: 0;
  outline: 0;
  box-shadow: none;
}

.workflow-composer-title-field input {
  font-size: 1.08rem;
  font-weight: 800;
}

.workflow-composer-title-field-chat input {
  padding: 0;
  font-size: 1.14rem;
}

.workflow-composer-body-field-chat textarea {
  min-height: 180px;
  padding: 0;
  font-size: 1rem;
}

.workflow-composer-body-field textarea {
  line-height: 1.7;
}

.workflow-composer-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
}

.workflow-composer-toolbar-chat {
  position: relative;
  grid-column: 1 / -1;
  padding-top: 0;
}

.tool-pill {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(15, 20, 25, 0.1);
  border-radius: 10px;
  background: #fff;
  color: var(--text-strong);
  font-size: 0.82rem;
  font-weight: 600;
  box-shadow: none;
}

.tool-pill-accent {
  color: var(--accent-cyan);
}

.tool-pill-interactive {
  position: relative;
  cursor: pointer;
  transition: border-color 150ms ease, background 150ms ease, color 150ms ease;
}

.tool-pill-interactive:hover {
  border-color: rgba(124, 58, 237, 0.3);
}

.tool-pill-active {
  border-color: rgba(124, 58, 237, 0.35);
  background: rgba(124, 58, 237, 0.06);
  color: var(--accent-cyan);
  box-shadow: none;
}

.workflow-create-menu {
  position: relative;
}

.workflow-create-popover {
  position: absolute;
  left: 0;
  top: calc(100% + 8px);
  z-index: 12;
  display: grid;
  gap: 10px;
  min-width: 300px;
  padding: 12px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.workflow-create-popover-grid {
  grid-template-columns: 1fr;
}

.workflow-create-popover-compact {
  min-width: 260px;
}

.workflow-create-popover__error {
  margin: 0;
}

.workflow-create-popover .workflow-field {
  gap: 6px;
}

.workflow-create-popover .workflow-field span {
  margin: 0 2px;
  color: #6b7280;
  font-size: 0.72rem;
  font-weight: 600;
}

.workflow-create-popover .field-input {
  min-height: 40px;
  border: 1px solid rgba(15, 20, 25, 0.1);
  border-radius: 8px;
  background: #fff;
  color: #111;
  box-shadow: none;
  font-size: 0.84rem;
  padding: 0 12px;
}

.workflow-create-popover .field-input:focus {
  border-color: rgba(124, 58, 237, 0.4);
  box-shadow: 0 0 0 2px rgba(124, 58, 237, 0.1);
}

.composer-required-count {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

.workflow-composer-footer {
  display: flex;
  grid-column: 1 / -1;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.workflow-composer-meta,
.workflow-composer-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.stage-board__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
}

.workflow-composer-meta {
  color: var(--text-muted);
  font-size: 0.82rem;
}

.workflow-composer-submit {
  width: 40px;
  height: 40px;
  background: var(--accent-cyan);
  color: #fff;
  font-size: 1.2rem;
  box-shadow: 0 12px 28px rgba(124, 58, 237, 0.24);
}

.workflow-composer-submit-inline {
  position: static;
}

.workflow-composer-error {
  grid-column: 1 / -1;
  margin: 0;
}

.workflow-composer-submit:disabled,
button:disabled {
  cursor: not-allowed;
  opacity: 0.54;
  box-shadow: none;
}

.workflow-canvas-header,
.workflow-stage-pipeline,
.workflow-stage-board,
.workflow-inspector,
.workflow-create-inspector {
  border-radius: 24px;
  padding: 18px;
}

.workflow-canvas-header,
.workflow-stage-pipeline,
.workflow-stage-board {
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.workflow-stage-pipeline {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  padding-left: 0;
  padding-right: 0;
}

.workflow-stage-step {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  min-height: 64px;
  padding: 10px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  border-radius: 18px;
  background: #f8fafb;
  color: var(--text-body);
  text-align: left;
  cursor: pointer;
}

.workflow-stage-step-active,
.workflow-stage-step:hover {
  border-color: rgba(124, 58, 237, 0.28);
  background: rgba(124, 58, 237, 0.08);
  color: var(--accent-cyan);
}

.workflow-stage-step__index {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #fff;
  color: currentColor;
  font-weight: 900;
}

.workflow-stage-step__text {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.workflow-stage-step__text strong {
  color: var(--text-strong);
}

.workflow-stage-step__text small,
.workflow-stage-step__count {
  color: var(--text-muted);
  font-size: 0.72rem;
}

.workflow-stage-step-ready .workflow-stage-step__count {
  color: var(--accent-cyan);
}

.workflow-stage-canvas {
  min-width: 0;
}

.workflow-stage-board {
  display: grid;
  gap: 16px;
  min-height: 620px;
  align-content: start;
  padding: 18px 0 0;
}

.storyboard-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  min-height: 0;
}

.storyboard-preview-card,
.clip-detail-card,
.character-strip,
.missing-clip-list {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 20px;
  background: #fff;
  border: 1px solid rgba(15, 20, 25, 0.07);
}

.storyboard-preview-card,
.clip-detail-card,
.missing-clip-list,
.final-result-card-v2 {
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.missing-clip-list {
  gap: 10px;
}

.missing-clip-list__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.storyboard-preview-card__head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.storyboard-preview-markdown,
.version-card__markdown {
  min-height: 420px;
  max-height: 62vh;
  overflow: auto;
  padding: 18px;
  border-radius: 18px;
  background: #f8fafb;
  color: var(--text-body);
  line-height: 1.75;
}

.storyboard-preview-markdown :deep(h1),
.storyboard-preview-markdown :deep(h2),
.storyboard-preview-markdown :deep(h3),
.storyboard-preview-markdown :deep(h4) {
  color: var(--text-strong);
}

.storyboard-preview-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.storyboard-preview-markdown :deep(th),
.storyboard-preview-markdown :deep(td) {
  padding: 8px 9px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  vertical-align: top;
}

.version-switcher {
  display: grid;
  gap: 10px;
}

.version-switcher__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.version-switcher__tabs {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  align-items: flex-start;
}

.version-switcher__tab {
  flex: 0 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-width: 180px;
  padding: 10px 12px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  border-radius: 16px;
  background: #f8fafb;
}

.version-switcher__tab-active {
  border-color: rgba(124, 58, 237, 0.28);
  background: rgba(124, 58, 237, 0.08);
}

.version-switcher__tab-main {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.version-switcher__tab-main strong {
  min-width: 0;
  color: var(--text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.version-switcher-compact .version-switcher__tabs {
  gap: 8px;
}

.version-switcher-compact .version-switcher__tab {
  min-width: 152px;
  padding: 8px 10px;
}

.character-strip__list,
.character-asset-grid,
.keyframe-thumb-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
  max-height: none;
  overflow: visible;
  align-content: start;
  align-items: start;
}

.keyframe-thumb-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.compact-version-card,
.video-version-card,
.keyframe-frame-card,
.keyframe-thumb-card,
.character-asset-card,
.missing-clip-card {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  border-radius: 16px;
  background: #f8fafb;
}

.keyframe-thumb-card {
  grid-template-rows: minmax(0, clamp(220px, 24vw, 340px)) auto;
}

.compact-version-card-active,
.video-version-card-active {
  border-color: rgba(124, 58, 237, 0.28);
  background: rgba(124, 58, 237, 0.08);
}

.video-version-card__title {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.video-version-card__title strong {
  min-width: 0;
}

.compact-version-card__main,
.missing-clip-card {
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.compact-version-card__main {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  width: 100%;
  padding: 0;
}

.missing-clip-card {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: auto;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  background: #f8fafb;
  color: var(--text-body);
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.missing-clip-card:hover {
  border-color: rgba(124, 58, 237, 0.28);
  background: rgba(124, 58, 237, 0.08);
}

.compact-version-card__badge,
.compact-version-card__status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}

.compact-version-card__badge {
  background: rgba(124, 58, 237, 0.1);
  color: var(--accent-cyan);
}

.compact-version-card__main strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compact-version-card__status {
  background: rgba(15, 20, 25, 0.06);
  color: var(--text-muted);
}

.keyframe-frame-card__failure strong,
.keyframe-frame-card__failure span {
  max-width: 100%;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.keyframe-frame-card__failure span {
  display: -webkit-box;
  overflow: auto;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 5;
}

.storyboard-adjust-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid rgba(15, 20, 25, 0.07);
}

.storyboard-adjust-panel__input {
  min-width: 0;
  min-height: 42px;
  padding: 0 14px;
  font-size: 0.88rem;
}

.storyboard-adjust-panel__button {
  min-width: 104px;
  min-height: 42px;
  padding: 0 18px;
  white-space: nowrap;
}

.video-version-panel {
  display: grid;
  gap: 14px;
}

.character-mini-card {
  display: grid;
  gap: 12px;
  padding: 14px;
  border-radius: 18px;
}

.character-mini-card__head {
  display: grid;
  gap: 4px;
}

.character-mini-card p,
.clip-detail-card p {
  margin: 6px 0 0;
}

.character-mini-card__summary {
  display: grid;
  gap: 8px;
  min-height: 108px;
  padding: 12px 14px;
  border: 1px solid rgba(124, 58, 237, 0.14);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(246, 250, 252, 0.98), rgba(239, 245, 248, 0.92));
  text-align: left;
  cursor: pointer;
}

.character-mini-card__summary:hover {
  border-color: rgba(124, 58, 237, 0.24);
  box-shadow: 0 10px 24px rgba(124, 58, 237, 0.08);
}

.character-mini-card__summary-label,
.character-mini-card__summary-hint {
  font-size: 0.72rem;
  font-weight: 800;
}

.character-mini-card__summary-label {
  color: var(--accent-cyan);
}

.character-mini-card__summary p {
  margin: 0;
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 4;
  line-height: 1.6;
}

.character-mini-card__summary-hint {
  color: var(--text-muted);
}

.character-mini-card__frames {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.character-mini-frame {
  position: relative;
  display: block;
  min-height: 96px;
  padding: 0;
  border: 0;
  border-radius: 14px;
  overflow: hidden;
  background: #eef2f4;
  cursor: zoom-in;
}

.character-mini-frame img {
  width: 100%;
  height: 100%;
  min-height: 96px;
  object-fit: cover;
}

.character-mini-frame span {
  position: absolute;
  left: 6px;
  bottom: 6px;
  min-height: 22px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: var(--text-strong);
  font-size: 0.7rem;
  font-weight: 800;
  line-height: 22px;
}

.character-asset-picker {
  grid-column: 1 / -1;
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  border-radius: 18px;
  background: #fff;
}

.character-asset-picker__head,
.character-asset-picker__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-end;
  justify-content: space-between;
}

.character-asset-card__preview {
  display: block;
  width: 100%;
  height: 148px;
  padding: 0;
  border: 0;
  border-radius: 14px;
  overflow: hidden;
  background: #eef2f4;
  cursor: zoom-in;
}

.character-asset-card__preview img,
.keyframe-thumb-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.keyframe-thumb-card__image {
  min-height: 0;
  border-radius: 12px;
}

.keyframe-frame-card__image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.clip-workbench {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr);
  gap: 12px;
}

.clip-timeline {
  display: grid;
  align-content: start;
  gap: 6px;
  max-height: 620px;
  overflow: auto;
}

.clip-timeline__item {
  display: grid;
  gap: 2px;
  min-height: 46px;
  padding: 8px 10px;
  border: 1px solid rgba(15, 20, 25, 0.07);
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.clip-timeline__item strong {
  font-size: 0.82rem;
  line-height: 1.25;
}

.clip-timeline__item-active,
.clip-timeline__item:hover {
  border-color: rgba(124, 58, 237, 0.28);
  background: rgba(124, 58, 237, 0.08);
}

.clip-timeline__item span {
  color: var(--text-muted);
  font-size: 0.68rem;
}

.keyframe-frame-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  align-items: start;
}

.keyframe-frame-grid-portrait {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.keyframe-frame-grid-landscape {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.character-sheet-preview-trigger {
  display: block;
  width: 100%;
  height: 260px;
  padding: 0;
  border: 0;
  border-radius: 16px;
  overflow: hidden;
  background: #eef2f4;
  cursor: zoom-in;
}

.keyframe-frame-card__preview {
  display: grid;
  place-items: center;
  height: clamp(260px, 32vw, 460px);
  min-height: 0;
}

.keyframe-frame-card__preview-portrait {
  height: clamp(260px, 32vw, 460px);
  min-height: 0;
  aspect-ratio: auto;
}

.keyframe-frame-card__preview-landscape {
  height: clamp(260px, 32vw, 460px);
  aspect-ratio: auto;
}

.keyframe-frame-card__head,
.keyframe-frame-card__actions,
.clip-card__selected-keyframes-head {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
}

.keyframe-frame-card__failure {
  display: grid;
  place-items: center;
  min-height: 180px;
  max-height: 220px;
  padding: 16px;
  border-radius: 14px;
  background: #fff4f6;
  color: var(--accent-danger);
  text-align: center;
  overflow: hidden;
}

.readiness-strip {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  min-height: 40px;
  padding: 0 16px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  border-radius: 999px;
  background: #f6f8fa;
  color: var(--text-body);
  font-weight: 700;
  white-space: nowrap;
}

.stage-board__readiness {
  flex: 0 0 auto;
  min-width: auto;
}

.video-version-card .version-card__video,
.final-result-card__video {
  width: 100%;
  height: clamp(260px, 32vw, 460px);
  border-radius: 16px;
  background: #eef2f4;
  object-fit: cover;
}

.final-result-card-v2 {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 16px;
  align-items: start;
}

.final-result-card-v2__meta {
  display: grid;
  flex-direction: column;
  align-content: start;
  gap: 14px;
}

.final-result-card-v2__summary,
.final-result-card-v2__actions {
  display: grid;
  gap: 10px;
}

.workflow-kv,
.inspector-kv-list,
.workflow-settings-stack {
  display: grid;
  gap: 10px;
}

.workflow-kv__row,
.inspector-kv-list div {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(15, 20, 25, 0.06);
}

.workflow-kv__row strong,
.inspector-kv-list strong {
  color: var(--text-strong);
  text-align: right;
}

.workflow-inspector {
  position: sticky;
  top: 0;
  display: grid;
  gap: 14px;
  max-height: calc(100vh - 150px);
  overflow: auto;
}

.inspector-section {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 20px;
}

.inspector-section__head {
  display: block;
}

.stage-toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.stage-toggle-chip,
.rating-pill {
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid rgba(15, 20, 25, 0.1);
  border-radius: 8px;
  background: #fff;
  color: var(--text-body);
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 150ms ease, background 150ms ease, color 150ms ease;
}

.stage-toggle-chip-active,
.rating-pill-active {
  border-color: rgba(124, 58, 237, 0.4);
  background: var(--accent-cyan);
  color: #fff;
}

.workflow-empty,
.workflow-error {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.65;
}

.workflow-error {
  color: var(--accent-danger);
}

.workflow-empty-large {
  display: grid;
  place-items: center;
  min-height: 240px;
  padding: 28px;
  text-align: center;
}

.workflow-empty-soft,
.workflow-empty-nested {
  padding: 18px;
  border-radius: 16px;
  background: #f8fafb;
}

.workflow-banner {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  padding: 16px;
  border-radius: 18px;
}

.workflow-banner-error {
  border-color: rgba(229, 72, 101, 0.2);
  background: #fff4f6;
}

.character-summary-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1190;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 20, 25, 0.34);
  backdrop-filter: blur(6px);
}

.character-summary-dialog {
  display: grid;
  gap: 14px;
  width: min(560px, calc(100vw - 40px));
  max-height: min(70vh, 640px);
  padding: 18px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: var(--shadow-panel);
}

.character-summary-dialog__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.character-summary-dialog__head h4 {
  margin: 0;
}

.character-summary-dialog__close {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid rgba(15, 20, 25, 0.08);
  border-radius: 999px;
  background: #fff;
  color: var(--text-body);
  font-weight: 700;
  cursor: pointer;
}

.character-summary-dialog__content {
  margin: 0;
  overflow: auto;
  color: var(--text-body);
  font-size: 0.9rem;
  line-height: 1.75;
  white-space: pre-wrap;
  word-break: break-word;
}

.image-preview-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 28px;
  background: rgba(15, 20, 25, 0.74);
  backdrop-filter: blur(12px);
}

.image-preview-full {
  display: block;
  max-width: min(92vw, 1280px);
  max-height: 82vh;
  object-fit: contain;
  border-radius: 18px;
  background: #eef2f4;
}

.image-preview-caption,
.image-preview-close {
  position: fixed;
  z-index: 1;
  color: #fff;
}

.image-preview-caption {
  left: 28px;
  top: 24px;
  display: grid;
  gap: 4px;
}

.image-preview-caption span {
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.82rem;
}

.image-preview-close {
  right: 28px;
  top: 24px;
  min-height: 36px;
  padding: 0 14px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  cursor: pointer;
}

@media (max-width: 1380px) {
  .workflow-canvas-view {
    grid-template-columns: 280px minmax(0, 1fr);
  }

  .workflow-header-settings__form {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .workflow-create-board,
  .workflow-canvas-grid,
  .storyboard-layout,
  .final-result-card-v2 {
    grid-template-columns: 1fr;
  }

  .workflow-inspector {
    position: static;
    max-height: none;
  }
}

@media (max-width: 1024px) {
  .workflow-canvas-view {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 100%;
    overflow: auto;
  }

  .workflow-canvas-view-detail .workflow-canvas-main {
    order: 1;
  }

  .workflow-canvas-view-detail .workflow-project-drawer {
    order: 2;
  }

  .workflow-project-drawer {
    border-right: 0;
    border-bottom: 1px solid rgba(15, 20, 25, 0.07);
    max-height: none;
  }

  .workflow-canvas-view-detail .workflow-project-drawer {
    border-top: 1px solid rgba(15, 20, 25, 0.07);
    border-bottom: 0;
  }

  .workflow-stage-pipeline {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .clip-workbench {
    grid-template-columns: 1fr;
  }

  .clip-timeline {
    grid-auto-flow: column;
    grid-auto-columns: minmax(132px, 0.6fr);
    grid-template-columns: none;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .workflow-header-settings__form {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .workflow-canvas-view {
    padding: 14px;
  }

  .workflow-stage-pipeline {
    grid-template-columns: 1fr;
  }

  .workflow-composer-card {
    padding: 18px;
  }

  .workflow-composer-card-chat {
    grid-template-columns: 1fr;
  }

  .workflow-composer-fields,
  .workflow-composer-toolbar-chat,
  .workflow-composer-footer,
  .workflow-composer-error {
    grid-column: 1;
  }

  .workflow-composer-upload {
    width: 100%;
    min-height: 72px;
    grid-auto-flow: column;
    justify-content: center;
  }

  .workflow-composer-submit {
    position: static;
    margin-left: auto;
  }

  .composer-required-count {
    width: 100%;
    margin-left: 0;
  }

  .workflow-composer-footer {
    flex-direction: column;
    align-items: stretch;
  }

  .workflow-composer-actions {
    justify-content: space-between;
  }

  .workflow-create-popover {
    left: 0;
    right: auto;
    min-width: min(324px, calc(100vw - 80px));
    max-width: calc(100vw - 80px);
  }

  .workflow-canvas-header,
  .stage-board__head,
  .storyboard-preview-card__head,
  .clip-detail-card__head,
  .keyframe-frame-card__head,
  .keyframe-frame-card__actions,
  .workflow-banner {
    flex-direction: column;
    align-items: stretch;
  }

  .workflow-canvas-header__summary {
    flex-direction: column;
    align-items: stretch;
  }

  .workflow-summary__parameter-tags-header {
    flex-wrap: wrap;
    overflow-x: visible;
  }

  .stage-board__meta {
    justify-content: flex-start;
  }

  .workflow-summary__meta-compact {
    justify-content: flex-start;
  }

  .version-switcher__tab,
  .storyboard-adjust-panel {
    grid-template-columns: 1fr;
  }

  .compact-version-card__main {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .compact-version-card__status {
    grid-column: 1 / -1;
    justify-self: start;
  }

  .version-switcher__tabs {
    gap: 8px;
  }

  .version-switcher__tab {
    min-width: 144px;
  }

  .keyframe-frame-grid,
  .keyframe-frame-grid-portrait,
  .keyframe-frame-grid-landscape {
    grid-template-columns: 1fr;
  }

  .keyframe-thumb-list {
    grid-template-columns: 1fr;
  }

  .storyboard-adjust-panel__button {
    width: 100%;
  }
}
</style>
