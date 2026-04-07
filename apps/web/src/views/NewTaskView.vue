<template>
  <section class="new-task-view grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
    <div class="surface-panel surface-panel-warm new-task-main p-6">
      <PageHeader
        eyebrow="创建任务"
        title="新任务"
        description="三步完成"
      />
      <div class="mt-3 flex items-center gap-3 text-sm text-slate-500">
        <HintBell title="创建说明" :text="creationHint" />
        <HintBell title="新手提示" :text="guidanceHint" />
      </div>

      <div class="mt-5 grid gap-3 sm:grid-cols-3">
        <div class="surface-tile px-4 py-3">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Step 1</p>
          <p class="mt-2 text-sm font-semibold text-slate-900">模式与模板</p>
        </div>
        <div class="surface-tile px-4 py-3">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Step 2</p>
          <p class="mt-2 text-sm font-semibold text-slate-900">素材与语义</p>
        </div>
        <div class="surface-tile px-4 py-3">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Step 3</p>
          <p class="mt-2 text-sm font-semibold text-slate-900">输出与提交</p>
        </div>
      </div>

      <div class="mb-6 mt-6 grid gap-3 xl:grid-cols-2">
        <button
          v-for="option in editingModeOptions"
          :key="option.value"
          type="button"
          class="group relative overflow-hidden rounded-[28px] border p-5 text-left transition duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-200/60 active:scale-[0.99]"
          :class="editingMode === option.value ? option.activeClass : option.inactiveClass"
          @click="setEditingMode(option.value)"
        >
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-xs uppercase tracking-[0.28em] text-slate-500">{{ option.kicker }}</p>
              <h3 class="mt-2 text-lg font-semibold text-slate-900">{{ option.label }}</h3>
            </div>
            <span class="surface-chip text-[11px] font-semibold">{{ editingMode === option.value ? "当前模式" : "切换至此" }}</span>
          </div>
          <p class="mt-3 text-sm leading-6 text-slate-600">{{ option.brief }}</p>
          <div class="mt-3 flex items-center gap-3">
            <HintBell title="模式说明" :text="option.hint" />
            <div class="flex flex-wrap gap-2 text-[11px] text-slate-600">
              <span v-for="tag in option.tags" :key="tag" class="surface-chip">{{ tag }}</span>
            </div>
          </div>
        </button>
      </div>

      <div class="mb-6 grid gap-3 xl:grid-cols-3">
        <button
          v-for="preset in visiblePresets"
          :key="preset.key"
          type="button"
          class="group relative overflow-hidden rounded-[26px] border p-4 text-left transition duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-200/60 active:scale-[0.99]"
          :class="selectedPresetKey === preset.key ? 'border-white/80 bg-[linear-gradient(180deg,rgba(255,251,242,0.92),rgba(240,247,255,0.76))] shadow-[0_20px_46px_rgba(122,144,177,0.14),inset_0_1px_0_rgba(255,255,255,0.92)]' : 'border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.78),rgba(255,255,255,0.54))] hover:-translate-y-0.5 hover:border-sky-200 hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(248,251,255,0.66))] hover:shadow-[0_18px_40px_rgba(121,144,177,0.12)]'"
          @click="applyPreset(preset)"
        >
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-xs uppercase tracking-[0.28em] text-slate-400">{{ presetBadge(preset) }}</p>
              <h3 class="mt-2 text-base font-semibold text-slate-900">{{ preset.name }}</h3>
            </div>
            <div class="flex flex-wrap justify-end gap-2">
              <span class="surface-chip text-[11px] font-semibold">{{ presetModeLabel(preset) }}</span>
              <span class="surface-chip text-[11px] font-semibold">{{ platformLabel(preset.platform) }}</span>
            </div>
          </div>
          <p class="mt-3 line-clamp-2 text-sm leading-6 text-slate-600">{{ preset.description }}</p>
          <div class="mt-4 flex flex-wrap gap-2 text-xs text-slate-600">
            <span class="surface-chip">{{ preset.aspectRatio }}</span>
            <span class="surface-chip">{{ preset.minDurationSeconds }}-{{ preset.maxDurationSeconds }} 秒</span>
            <span class="surface-chip">{{ preset.outputCount }} 条</span>
          </div>
        </button>
      </div>
      <div class="mb-6 flex items-center gap-2 text-xs text-slate-500">
        <span class="surface-chip">当前模板方向</span>
        <span>{{ presetModeHint }}</span>
      </div>

      <form class="grid gap-5" @submit.prevent="submitTask">
        <div class="flex items-center gap-3">
          <div class="surface-chip text-[11px] font-semibold">Step 2</div>
          <p class="text-sm font-semibold text-slate-900">素材与语义</p>
        </div>

        <label class="grid gap-2 text-sm text-slate-700">
          任务标题
          <input v-model="form.title" required class="field-input" placeholder="例如：第 12 集高能反转投放版" />
        </label>

        <div class="surface-tile grid gap-4 p-4">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div class="flex items-center gap-2">
                <p class="text-sm font-semibold text-slate-900">原始视频</p>
                <HintBell title="素材说明" :text="sourcePanelHint" />
              </div>
            </div>
            <div class="flex flex-wrap gap-2">
              <button type="button" class="btn-primary btn-sm" @click="videoFileInput?.click()">
                选择 / 追加视频
              </button>
              <span class="surface-chip text-[11px] font-semibold">{{ editingModeLabel }}</span>
            </div>
          </div>

          <input ref="videoFileInput" type="file" accept="video/*" multiple class="hidden" @change="onFileChange" />

          <div class="flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span class="surface-chip">{{ sourceFileCountLabel }}</span>
            <span class="surface-chip">{{ fileSummary }}</span>
            <span class="surface-chip">{{ editingModeStatusLabel }}</span>
          </div>

          <div v-if="sourceFiles.length" class="grid gap-3">
            <article
              v-for="item in sourceFiles"
              :key="item.id"
              class="surface-tile flex flex-wrap items-center justify-between gap-3 px-4 py-3"
              :class="item.isPrimary ? 'border-sky-200 bg-[linear-gradient(180deg,rgba(243,248,255,0.92),rgba(232,242,255,0.72))]' : ''"
            >
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <p class="truncate text-sm font-semibold text-slate-900">{{ item.file.name }}</p>
                  <span v-if="item.isPrimary" class="surface-chip text-[11px] font-semibold">主素材</span>
                </div>
                <p class="mt-1 text-xs text-slate-500">{{ formatFileSummary(item.file) }}</p>
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  class="btn-ghost btn-sm"
                  :disabled="item.isPrimary"
                  @click="setPrimarySourceFile(item.id)"
                >
                  设为主素材
                </button>
                <button type="button" class="btn-danger btn-sm" @click="removeSourceFile(item.id)">
                  移除
                </button>
              </div>
            </article>
          </div>
          <div v-else class="surface-tile flex items-center justify-between gap-3 border-dashed px-5 py-4 text-sm text-slate-500">
            <span>{{ editingMode === "mixcut" ? "先放入至少 2 条素材。" : "先选择 1 条主素材。" }}</span>
            <HintBell
              title="素材建议"
              :text="editingMode === 'mixcut' ? '混剪更适合 2 条及以上素材，方便做镜头对照和分镜推进。' : '短剧模式只保留 1 条主素材；如果要做多素材编排，请切换到混剪模式。'"
              align="left"
            />
          </div>

          <div class="surface-tile grid gap-3 p-4" :class="editingMode === 'mixcut' ? 'border-sky-200 bg-[linear-gradient(180deg,rgba(242,248,255,0.92),rgba(235,247,252,0.72))]' : 'border-rose-200 bg-[linear-gradient(180deg,rgba(255,246,248,0.92),rgba(246,244,255,0.72))]'">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p class="text-xs uppercase tracking-[0.24em] text-slate-400">{{ editingMode === 'mixcut' ? '混剪语义' : '短剧语义' }}</p>
                <p class="mt-2 text-sm font-semibold text-slate-900">{{ editingMode === 'mixcut' ? '题材 / 风格 / 分镜编排' : '高燃卡点 / 对白完整 / 情绪推进' }}</p>
              </div>
              <div class="flex items-center gap-2">
                <HintBell :title="editingMode === 'mixcut' ? '混剪语义' : '短剧语义'" :text="editingMode === 'mixcut' ? mixcutModeHint : dramaModeHint" />
                <span class="surface-chip text-[11px] font-semibold">{{ editingMode === 'mixcut' ? "分镜脚本模式" : "剧情卡点模式" }}</span>
              </div>
            </div>
            <div class="flex flex-wrap gap-2">
              <span v-for="tag in editingMode === 'mixcut' ? mixcutModeTags : dramaModeTags" :key="tag" class="surface-chip">{{ tag }}</span>
            </div>
          </div>
        </div>

        <div class="mt-2 flex items-center gap-3">
          <div class="surface-chip text-[11px] font-semibold">Step 3</div>
          <p class="text-sm font-semibold text-slate-900">设置输出</p>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-700">
            投放平台
            <select v-model="form.platform" class="field-select">
              <option value="douyin">抖音</option>
              <option value="kuaishou">快手</option>
              <option value="xiaohongshu">小红书</option>
              <option value="wechat">视频号</option>
            </select>
          </label>
          <label class="grid gap-2 text-sm text-slate-700">
            画幅比例
            <select v-model="form.aspectRatio" class="field-select">
              <option value="9:16">竖版 9:16</option>
              <option value="16:9">横版 16:9</option>
            </select>
          </label>
        </div>

        <div v-if="editingMode === 'mixcut'" class="surface-tile grid gap-4 p-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-700">
            混剪题材
            <select v-model="form.mixcutContentType" class="field-select">
              <option v-for="item in mixcutContentTypeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
            <div class="mt-1 flex items-center gap-2">
              <HintBell title="题材说明" :text="selectedMixcutContentTypeHint" />
            </div>
          </label>
          <label class="grid gap-2 text-sm text-slate-700">
            混剪风格
            <select v-model="form.mixcutStylePreset" class="field-select">
              <option v-for="item in currentMixcutStyleOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
            <div class="mt-1 flex items-center gap-2">
              <HintBell title="风格说明" :text="selectedMixcutStyleHint" />
            </div>
          </label>
        </div>
        <div v-else class="surface-tile grid gap-4 p-4 sm:grid-cols-2">
          <div class="grid gap-2 text-sm text-slate-700">
            <p>短剧剪辑重点</p>
            <div class="flex flex-wrap gap-2 text-xs text-slate-600">
              <span class="surface-chip">对白完整</span>
              <span class="surface-chip">高燃卡点</span>
              <span class="surface-chip">反转收尾</span>
            </div>
            <HintBell title="短剧说明" :text="dramaModeHint" />
          </div>
          <div class="grid gap-2 text-sm text-slate-700">
            <p>提示词策略</p>
            <div class="flex flex-wrap gap-2 text-xs text-slate-600">
              <span class="surface-chip">{{ editingModePromptChipLabel }}</span>
              <span class="surface-chip">优先保留关键对白</span>
              <span class="surface-chip">结尾留悬念</span>
            </div>
            <HintBell title="节奏说明" text="这一模式不强调题材切换，而是优先处理冲突、信息量和拉停节奏。" />
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-3">
          <label class="grid gap-2 text-sm text-slate-700">
            最小时长（秒）
            <input v-model.number="form.minDurationSeconds" type="number" min="5" max="120" class="field-input" />
          </label>
          <label class="grid gap-2 text-sm text-slate-700">
            最大时长（秒）
            <input v-model.number="form.maxDurationSeconds" type="number" min="5" max="120" class="field-input" />
          </label>
          <label class="grid gap-2 text-sm text-slate-700">
            产出数量
            <input v-model.number="form.outputCount" type="number" min="1" max="10" class="field-input" />
          </label>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-700">
            片头模板
            <select v-model="form.introTemplate" class="field-select">
              <option v-for="item in introTemplateOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
            <div class="mt-1 flex items-center gap-2">
              <HintBell title="片头说明" :text="selectedIntroTemplateHint" />
            </div>
          </label>
          <label class="grid gap-2 text-sm text-slate-700">
            片尾模板
            <select v-model="form.outroTemplate" class="field-select">
              <option v-for="item in outroTemplateOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
            <div class="mt-1 flex items-center gap-2">
              <HintBell title="片尾说明" :text="selectedOutroTemplateHint" />
            </div>
          </label>
        </div>

          <div class="surface-tile p-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div class="flex items-center gap-2">
                  <p class="text-sm font-semibold text-slate-900">提示词</p>
                  <HintBell title="提示词说明" text="可以手动写，也可以先让模型起一版。当前模式会自动补上对应约束。" />
                </div>
              </div>
              <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="btn-primary btn-sm"
                :disabled="generatingPrompt"
                @click="handleGeneratePrompt"
              >
                {{ generatingPrompt ? "生成中..." : "AI 生成" }}
              </button>
              <button type="button" class="btn-ghost btn-sm" @click="restorePresetPrompt">
                恢复模板建议
              </button>
            </div>
          </div>
          <textarea v-model="form.creativePrompt" rows="5" class="field-textarea mt-4" placeholder="例如：开头直接进冲突，保留关键对白，结尾停在反转前一拍。"></textarea>
          <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span class="surface-chip">{{ promptSourceLabel }}</span>
            <span class="surface-chip">{{ mixcutPromptChipLabel }}</span>
          </div>
        </div>

        <label class="grid gap-2 text-sm text-slate-700">
          字幕 / 台词（可选）
          <input ref="transcriptFileInput" type="file" accept=".srt,.vtt,.txt" class="hidden" @change="handleTranscriptFileChange" />
          <textarea
            v-model="form.transcriptText"
            rows="8"
            class="field-textarea font-mono text-sm"
            placeholder="粘贴 SRT / VTT 或台词文本。带时间戳会更稳。"
          ></textarea>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="btn-secondary btn-sm"
              @click="transcriptFileInput?.click()"
            >
              导入字幕文件
            </button>
            <HintBell title="字幕说明" :text="transcriptStats.summary" />
          </div>
        </label>

          <div class="flex flex-wrap items-center gap-4">
          <button
            :disabled="submitting || !isFormReady"
            class="btn-primary"
            type="submit"
          >
            {{ submitButtonLabel }}
          </button>
          <p class="text-sm text-slate-600">{{ statusText }}</p>
        </div>
      </form>
    </div>

    <aside class="new-task-aside space-y-4">
      <div class="surface-panel surface-panel-warm p-6">
        <PageHeader
          :eyebrow="editingMode === 'mixcut' ? 'Preview' : 'Preview'"
          :title="editingMode === 'mixcut' ? '编排预演' : '剧情预演'"
          description="一眼确认"
        />

        <div class="grid gap-3">
          <div class="surface-tile-strong grid gap-4 p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p class="text-xs uppercase tracking-[0.24em] text-slate-400">{{ editingMode === "mixcut" ? "当前混剪配置" : "当前短剧配置" }}</p>
                <p class="mt-2 text-lg font-semibold text-slate-900">{{ editingMode === "mixcut" ? mixcutStrategyLabel : "高燃卡点 / 对白完整" }}</p>
              </div>
              <span class="surface-chip text-[11px] font-semibold">{{ editingModeLabel }}</span>
            </div>
            <div class="grid gap-2 text-sm text-slate-600">
              <div class="flex flex-wrap items-center gap-2">
                <span v-if="editingMode === 'mixcut'" class="surface-chip">题材 · {{ selectedMixcutContentTypeLabel }}</span>
                <span v-if="editingMode === 'mixcut'" class="surface-chip">风格 · {{ selectedMixcutStyleLabel }}</span>
                <span class="surface-chip">{{ editingMode === "mixcut" ? `转场 · ${mixcutTransitionLabel}` : "对白完整 / 高燃卡点" }}</span>
              </div>
              <div class="flex flex-wrap gap-2">
                <HintBell :title="editingMode === 'mixcut' ? '题材说明' : '短剧说明'" :text="editingMode === 'mixcut' ? selectedMixcutContentTypeHint : dramaModeHint" />
                <HintBell :title="editingMode === 'mixcut' ? '风格说明' : '节奏说明'" :text="editingMode === 'mixcut' ? selectedMixcutStyleHint : '优先保留对白和关键冲突，再通过片头片尾拉停。'" />
              </div>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <div class="surface-tile p-4">
              <div class="flex items-center justify-between gap-3">
                <p class="text-xs uppercase tracking-[0.24em] text-slate-400">片头模板</p>
                <HintBell title="片头说明" :text="selectedIntroTemplateHint" />
              </div>
              <p class="mt-2 text-sm font-semibold text-slate-900">{{ selectedIntroTemplateLabel }}</p>
            </div>
            <div class="surface-tile p-4">
              <div class="flex items-center justify-between gap-3">
                <p class="text-xs uppercase tracking-[0.24em] text-slate-400">片尾模板</p>
                <HintBell title="片尾说明" :text="selectedOutroTemplateHint" />
              </div>
              <p class="mt-2 text-sm font-semibold text-slate-900">{{ selectedOutroTemplateLabel }}</p>
            </div>
          </div>

          <div class="surface-tile p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">{{ editingMode === "mixcut" ? "分镜预演" : "短剧预演" }}</p>
              <div class="flex items-center gap-2">
                <span class="surface-chip text-[11px] font-semibold">{{ editingMode === "mixcut" ? mixcutTransitionLabel : "高燃卡点" }}</span>
                <HintBell
                  :title="editingMode === 'mixcut' ? '分镜提示' : '节奏提示'"
                  :text="editingMode === 'mixcut' ? '按开场、推进、收束检查镜头结构是否完整。' : '重点确认冲突起势、对白完整和结尾悬念。'"
                />
              </div>
            </div>
            <div class="storyboard-track mt-4">
              <article class="storyboard-segment surface-tile p-4">
                <p class="text-[11px] uppercase tracking-[0.26em] text-slate-500">{{ editingMode === "mixcut" ? "分镜开场" : "高燃起势" }}</p>
                <p class="mt-2 text-sm font-semibold text-slate-900">{{ editingMode === "mixcut" ? selectedIntroTemplateLabel : "对白 / 冲突起势" }}</p>
              </article>
              <article class="storyboard-segment surface-tile p-4">
                <p class="text-[11px] uppercase tracking-[0.26em] text-slate-500">{{ editingMode === "mixcut" ? "推进轨道" : "卡点轨道" }}</p>
                <p class="mt-2 text-sm font-semibold text-slate-900">{{ editingMode === "mixcut" ? `${selectedMixcutContentTypeLabel} / ${selectedMixcutStyleLabel}` : "高燃卡点 / 情绪推进" }}</p>
              </article>
              <article class="storyboard-segment surface-tile p-4">
                <p class="text-[11px] uppercase tracking-[0.26em] text-slate-500">{{ editingMode === "mixcut" ? "收束轨道" : "悬念收尾" }}</p>
                <p class="mt-2 text-sm font-semibold text-slate-900">{{ editingMode === "mixcut" ? selectedOutroTemplateLabel : "悬念 / 反转" }}</p>
              </article>
            </div>
          </div>
        </div>
      </div>

      <div class="surface-panel p-6">
        <PageHeader
          eyebrow="参数"
          title="参数"
          description="关键项"
        />

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="surface-tile p-4">
            <div class="flex items-center justify-between gap-3">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">当前模板</p>
              <HintBell title="模板说明" :text="activePreset?.description || '当前为手动配置。'" />
            </div>
            <p class="mt-2 text-sm font-semibold text-slate-900">{{ activePreset?.name || "自定义" }}</p>
          </div>
          <div class="surface-tile p-4">
            <div class="flex items-center justify-between gap-3">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">来源</p>
              <HintBell title="来源说明" :text="cloneFromHint" />
            </div>
            <p class="mt-2 text-sm font-semibold text-slate-900">{{ sourceHint }}</p>
          </div>
        </div>

        <div class="mt-4 grid gap-2 text-sm text-slate-600">
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>平台</span>
            <span class="font-medium text-slate-900">{{ platformLabel(form.platform) }}</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>画幅 / 时长</span>
            <span class="font-medium text-slate-900">{{ form.aspectRatio }} / {{ form.minDurationSeconds }}-{{ form.maxDurationSeconds }} 秒</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>产出数量</span>
            <span class="font-medium text-slate-900">{{ form.outputCount }} 条</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>素材数量</span>
            <span class="font-medium text-slate-900">{{ sourceFileCount }} 条</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>剪辑模式</span>
            <span class="font-medium text-slate-900">{{ editingModeLabel }}</span>
          </div>
          <div v-if="editingMode === 'mixcut'" class="surface-tile flex items-center justify-between px-4 py-3">
            <span>混剪题材 / 风格</span>
            <span class="font-medium text-slate-900">{{ mixcutStrategyLabel }}</span>
          </div>
          <div v-else class="surface-tile flex items-center justify-between px-4 py-3">
            <span>短剧语义</span>
            <span class="font-medium text-slate-900">高燃卡点 / 对白完整</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>语义素材</span>
            <span class="font-medium text-slate-900">{{ transcriptModeLabel }}</span>
          </div>
          <div class="surface-tile px-4 py-3">
            <div class="flex items-center justify-between gap-3">
              <p class="text-xs uppercase tracking-[0.22em] text-slate-400">输入质量</p>
              <HintBell title="输入质量" :text="transcriptStats.hint" />
            </div>
            <p class="mt-2 text-sm font-medium text-slate-900">{{ transcriptStats.quality }}</p>
          </div>
          <div class="surface-tile px-4 py-3">
            <div class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <p class="text-xs uppercase tracking-[0.22em] text-slate-400">提交校验</p>
                <HintBell title="校验说明" :items="validationHintItems" />
              </div>
              <span class="surface-chip text-[11px] font-semibold">{{ isFormReady ? "可提交" : "待修正" }}</span>
            </div>
            <ul class="mt-3 grid gap-2 text-xs">
              <li
                v-for="item in validationChecklist"
                :key="item.key"
                class="surface-tile flex items-center justify-between gap-3 px-3 py-2"
              >
                <p class="font-medium text-slate-900">{{ item.label }}</p>
                <span :class="item.passed ? 'text-emerald-500' : 'text-rose-500'" class="shrink-0 font-semibold">
                  {{ item.passed ? "通过" : "待修正" }}
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="surface-panel p-6">
        <PageHeader
          eyebrow="预览"
          title="视频"
          description="主素材"
        />
        <div v-if="primaryPreviewUrl" class="surface-tile overflow-hidden">
          <video :src="primaryPreviewUrl" controls class="aspect-video w-full bg-black object-cover"></video>
          <div class="border-t border-white/50 p-4 text-sm text-slate-600">
            <p class="font-medium text-slate-900">{{ fileName }}</p>
            <p class="mt-1">{{ fileSummary }}</p>
          </div>
        </div>
        <div v-else class="surface-tile border-dashed p-8 text-center text-sm text-slate-500">
          选中素材后在这里预览。
        </div>
      </div>

      <div class="surface-panel p-4 flex items-center justify-between">
        <div>
          <p class="text-xs uppercase tracking-[0.3em] text-slate-500">操作提示</p>
          <h3 class="text-lg font-semibold text-slate-900">提交前</h3>
        </div>
        <HintBell title="操作建议" :items="['短剧尽量给时间戳字幕', '混剪建议至少 2 条素材', '提示词生成后再补一句重点', '片头直接进冲突，片尾留悬念']" />
      </div>
    </aside>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { cloneTask, createTask, fetchPresets, generateCreativePrompt, uploadVideo } from "@/api/tasks";
import HintBell from "@/components/HintBell.vue";
import PageHeader from "@/components/PageHeader.vue";
import type { CreateTaskRequest, EditingMode, TaskCloneDraft, TaskPreset } from "@/types";

const router = useRouter();
const route = useRoute();

const introTemplateOptions = [
  { value: "none", label: "不加片头", hint: "直接进入剧情，不做额外铺垫。" },
  { value: "cold_open", label: "冷开场直切", hint: "开头直接落在当前冲突现场，适合追更和高压剧情。" },
  { value: "flash_hook", label: "爆点闪切片头", hint: "先给爆点画面再回剧情，更适合首刷拉停。" },
  { value: "pressure_build", label: "情绪压迫片头", hint: "先压氛围和情绪，再推进到关键对白。" },
] as const;

const outroTemplateOptions = [
  { value: "none", label: "不加片尾", hint: "直接结束，不额外补尾。"},
  { value: "suspense_hold", label: "悬念停顿片尾", hint: "停在一句没说完或表情反转前，制造停留。"},
  { value: "follow_hook", label: "追更钩子片尾", hint: "适合连续剧切条，结尾留下下一集欲望。"},
  { value: "question_freeze", label: "反问定格片尾", hint: "停在质问、反讽或答案未揭晓的时刻。"},
] as const;

const mixcutContentTypeOptions = [
  { value: "generic", label: "通用混剪", hint: "适合还没明确题材时，优先做节奏推进和镜头对照。" },
  { value: "drama", label: "剧情混剪", hint: "更关注冲突、对白、反转和情绪递进。" },
] as const;

const editingModeOptions = [
  {
    value: "drama",
    kicker: "Drama Cut",
    label: "短剧剪辑",
    brief: "高燃卡点 × 对白完整，节奏紧凑。",
    hint:
      "围绕高燃卡点、对白完整和情绪落点做投放切条，强调剧情连续性，不强调题材风格切换。",
    tags: ["高燃卡点", "对白完整", "反转落点"],
    activeClass:
      "border-white/80 bg-[linear-gradient(180deg,rgba(255,244,247,0.96),rgba(240,246,255,0.76))] shadow-[0_20px_46px_rgba(121,144,177,0.14),inset_0_1px_0_rgba(255,255,255,0.92)]",
    inactiveClass:
      "border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.78),rgba(255,255,255,0.54))] hover:-translate-y-0.5 hover:border-rose-200 hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(249,250,255,0.66))] hover:shadow-[0_18px_40px_rgba(121,144,177,0.12)]",
  },
  {
    value: "mixcut",
    kicker: "Mixcut",
    label: "混剪",
    brief: "多素材+风格脚本，偏镜头节奏与软质叙事。",
    hint:
      "围绕题材、风格和分镜脚本编排多素材，强调镜头结构、静帧插叙和导演感排布，让输出像导演剪辑。",
    tags: ["题材", "风格", "分镜编排"],
    activeClass:
      "border-white/80 bg-[linear-gradient(180deg,rgba(242,248,255,0.96),rgba(236,250,246,0.78))] shadow-[0_20px_46px_rgba(121,144,177,0.14),inset_0_1px_0_rgba(255,255,255,0.92)]",
    inactiveClass:
      "border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.78),rgba(255,255,255,0.54))] hover:-translate-y-0.5 hover:border-sky-200 hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.9),rgba(244,250,255,0.66))] hover:shadow-[0_18px_40px_rgba(121,144,177,0.12)]",
  },
] as const;

const mixcutStyleOptions = {
  generic: [
    { value: "director", label: "导演感推进", hint: "适合通用混剪，突出镜头对照和节奏推进。" },
    { value: "music_sync", label: "音乐卡点", hint: "强化节奏点和快切感，更适合强节奏 BGM。" },
  ],
  drama: [
    { value: "director", label: "导演感推进", hint: "适合冲突递进、人物关系对照和高点收束。" },
    { value: "music_sync", label: "音乐卡点", hint: "适合更强节奏的剧情快切和爆点推进。" },
  ],
} as const;

const creationHint =
  "先选模式，再放素材，最后定输出。AI 可以先起一版提示词。";
const guidanceHint = [
  "短剧：先保对白完整，再卡爆点。",
  "混剪：至少 2 条素材，更容易做分镜。",
  "主素材可随时切换。",
  "长台词尽量不要切断。",
  "AI 生成后再补一句重点会更稳。",
].join("\n");
const dramaPromptSeed =
  "请从短剧视频中挑选高燃卡点、反转瞬间和情绪爆点进行切条，保持关键对白完整、动作连贯，结尾留悬念。";
const dramaPromptSuffix =
  "短剧补充：优先保留对白完整度和冲突推进，避免把句子中段或连续动作切断，结尾尽量卡在情绪反转或关系未落地的位置。";
const mixcutPromptSeed =
  "请从多个视频素材中挑选高燃卡点、反转瞬间和导演感镜头进行混剪，优先形成分镜脚本和镜头编排。";
const mixcutPromptSuffix =
  "混剪补充：优先跨多个素材挑选镜头，按照题材、风格和分镜脚本组织开场、推进和收束，允许适度插叙和静帧快闪。";

interface SourceFileDraft {
  id: string;
  file: File;
  previewUrl: string;
  isPrimary: boolean;
}

interface CreateValidationItem {
  key: string;
  label: string;
  hint: string;
  passed: boolean;
}

const fallbackPresets: TaskPreset[] = [
  {
    key: "douyin_banger",
    name: "抖音爆款版",
    description: "高节奏、高冲突，适合竖屏投放和首刷停留优化。",
    defaultTitle: "抖音爆款版",
    editingMode: "drama",
    platform: "douyin",
    aspectRatio: "9:16",
    minDurationSeconds: 15,
    maxDurationSeconds: 30,
    outputCount: 3,
    introTemplate: "flash_hook",
    outroTemplate: "suspense_hold",
    creativePrompt: "开头直接给最强冲突画面，优先保留对峙、反转和情绪爆点，结尾停在最想继续看的一拍。"
  },
  {
    key: "feed_balanced",
    name: "关系推进版",
    description: "更强调人物关系和剧情递进，适合转化与追更双目标。",
    defaultTitle: "关系推进版",
    editingMode: "drama",
    platform: "wechat",
    aspectRatio: "9:16",
    minDurationSeconds: 20,
    maxDurationSeconds: 35,
    outputCount: 4,
    introTemplate: "pressure_build",
    outroTemplate: "question_freeze",
    creativePrompt: "保留关系推进和情绪变化，关键对白必须完整，结尾停在一句反问或未揭开的真相前。"
  },
  {
    key: "long_cut",
    name: "追更连载版",
    description: "适合剧集连续切条，强调冲突升级和下一条追更欲望。",
    defaultTitle: "追更连载版",
    editingMode: "drama",
    platform: "kuaishou",
    aspectRatio: "9:16",
    minDurationSeconds: 20,
    maxDurationSeconds: 40,
    outputCount: 3,
    introTemplate: "cold_open",
    outroTemplate: "follow_hook",
    creativePrompt: "优先保留冲突升级、角色关系变化和关键反转，最后一拍一定要留出追更钩子。"
  },
  {
    key: "music_sync_mixcut",
    name: "音乐卡点混剪",
    description: "适合节奏感强的多素材混剪，优先对白闪快切、鼓点对齐和爆点推进。",
    defaultTitle: "音乐卡点混剪版",
    editingMode: "mixcut",
    platform: "douyin",
    aspectRatio: "9:16",
    minDurationSeconds: 15,
    maxDurationSeconds: 28,
    outputCount: 4,
    introTemplate: "flash_hook",
    outroTemplate: "suspense_hold",
    creativePrompt: "优先按鼓点和爆点组织多素材镜头，开头直接给最强节奏点，中段强化快切和反差，结尾停在最后一次强拍后的一瞬。",
    mixcutContentType: "generic",
    mixcutStylePreset: "music_sync"
  },
  {
    key: "drama_conflict_mixcut",
    name: "剧情冲突混剪",
    description: "适合多段剧情素材联合编排，强调人物对照、冲突递进和情绪收束。",
    defaultTitle: "剧情冲突混剪版",
    editingMode: "mixcut",
    platform: "kuaishou",
    aspectRatio: "9:16",
    minDurationSeconds: 18,
    maxDurationSeconds: 36,
    outputCount: 3,
    introTemplate: "cold_open",
    outroTemplate: "follow_hook",
    creativePrompt: "请把多段剧情素材组织成一条冲突递进明确的混剪，优先保留人物对峙、情绪升级和反转前夜，结尾留出追更钩子。",
    mixcutContentType: "drama",
    mixcutStylePreset: "director"
  },
];

const availablePresets = ref<TaskPreset[]>(fallbackPresets);
const selectedPresetKey = ref<string>(fallbackPresets[0].key);
const sourceFiles = ref<SourceFileDraft[]>([]);
const submitting = ref(false);
const generatingPrompt = ref(false);
const statusText = ref("等待上传视频");
const promptSource = ref("模板建议");
const editingMode = ref<EditingMode>("drama");
const cloneSource = ref<TaskCloneDraft | null>(null);
const videoFileInput = ref<HTMLInputElement | null>(null);
const transcriptFileInput = ref<HTMLInputElement | null>(null);

const form = ref<CreateTaskRequest>({
  title: "抖音爆款版",
  sourceAssetId: "",
  sourceFileName: "",
  sourceAssetIds: [],
  sourceFileNames: [],
  platform: fallbackPresets[0].platform,
  aspectRatio: fallbackPresets[0].aspectRatio,
  minDurationSeconds: fallbackPresets[0].minDurationSeconds,
  maxDurationSeconds: fallbackPresets[0].maxDurationSeconds,
  outputCount: fallbackPresets[0].outputCount,
  introTemplate: fallbackPresets[0].introTemplate,
  outroTemplate: fallbackPresets[0].outroTemplate,
  creativePrompt: fallbackPresets[0].creativePrompt,
  transcriptText: "",
  editingMode: "drama",
  mixcutEnabled: false,
  mixcutContentType: "generic",
  mixcutStylePreset: "director",
});

const primarySourceFile = computed(() => sourceFiles.value.find((item) => item.isPrimary) ?? sourceFiles.value[0] ?? null);
const sourceFileCount = computed(() => sourceFiles.value.length);
const sourceFileCountLabel = computed(() => (sourceFileCount.value ? `已选 ${sourceFileCount.value} 条素材` : "尚未选择素材"));
const fileName = computed(() => {
  if (!sourceFileCount.value) {
    return "未选择文件";
  }
  if (sourceFileCount.value === 1) {
    return primarySourceFile.value?.file.name ?? "未选择文件";
  }
  return `${primarySourceFile.value?.file.name ?? "主素材"} 等 ${sourceFileCount.value} 条素材`;
});
const fileSummary = computed(() => {
  if (!sourceFileCount.value) {
    return "可先上传素材。";
  }

  const totalSize = sourceFiles.value.reduce((sum, item) => sum + item.file.size, 0);
  const totalSizeMb = (totalSize / 1024 / 1024).toFixed(1);
  const primaryName = primarySourceFile.value?.file.name ?? "未指定";
  return `${sourceFileCount.value} 条素材 · ${totalSizeMb} MB · 主素材 ${primaryName}`;
});
const primaryPreviewUrl = computed(() => primarySourceFile.value?.previewUrl ?? "");

const activePreset = computed(() => visiblePresets.value.find((preset) => preset.key === selectedPresetKey.value) ?? null);
const mixcutEnabled = computed(() => editingMode.value === "mixcut");
const editingModeLabel = computed(() => (editingMode.value === "mixcut" ? "混剪模式" : "短剧剪辑模式"));
const editingModeStatusLabel = computed(() =>
  editingMode.value === "mixcut"
    ? "题材 / 风格 / 分镜"
    : "高燃卡点 / 对白完整"
);
const editingModePromptChipLabel = computed(() =>
  editingMode.value === "mixcut" ? "已追加混剪提示词" : "已追加短剧提示词"
);
const sourcePanelHint = computed(() =>
  editingMode.value === "mixcut"
    ? "支持一次放入多条视频，系统会按题材、风格和分镜来整理输入。"
    : "短剧模式只保留一条主视频，重点围绕高燃卡点和对白完整。"
);
const dramaModeHint = computed(() =>
  "更看重高燃卡点、对白完整和情绪落点。"
);
const mixcutModeHint = computed(() =>
  "更看重题材、风格和镜头编排。"
);
const dramaModeTags = ["对白完整", "高燃卡点", "反转收尾"];
const mixcutModeTags = ["题材驱动", "风格驱动", "分镜编排"];
const selectedIntroTemplateHint = computed(() => introTemplateOptions.find((item) => item.value === form.value.introTemplate)?.hint ?? "根据剧情节奏决定进入方式。");
const selectedOutroTemplateHint = computed(() => outroTemplateOptions.find((item) => item.value === form.value.outroTemplate)?.hint ?? "根据投放目标决定结尾落点。");
const selectedIntroTemplateLabel = computed(() => introTemplateOptions.find((item) => item.value === form.value.introTemplate)?.label ?? "不加片头");
const selectedOutroTemplateLabel = computed(() => outroTemplateOptions.find((item) => item.value === form.value.outroTemplate)?.label ?? "不加片尾");
const currentMixcutStyleOptions = computed(() => {
  const contentType = (form.value.mixcutContentType || "generic") as keyof typeof mixcutStyleOptions;
  return mixcutStyleOptions[contentType] ?? mixcutStyleOptions.generic;
});
const selectedMixcutContentTypeLabel = computed(
  () => mixcutContentTypeOptions.find((item) => item.value === form.value.mixcutContentType)?.label ?? "通用混剪"
);
const selectedMixcutContentTypeHint = computed(
  () => mixcutContentTypeOptions.find((item) => item.value === form.value.mixcutContentType)?.hint ?? "根据素材题材决定混剪策略。"
);
const selectedMixcutStyleLabel = computed(
  () => currentMixcutStyleOptions.value.find((item) => item.value === form.value.mixcutStylePreset)?.label ?? "导演感推进"
);
const selectedMixcutStyleHint = computed(
  () => currentMixcutStyleOptions.value.find((item) => item.value === form.value.mixcutStylePreset)?.hint ?? "根据镜头节奏选择更适合的混剪方式。"
);
const promptSourceLabel = computed(() => `提示词来源：${promptSource.value}`);
const mixcutPromptChipLabel = computed(() => editingModePromptChipLabel.value);
const mixcutStrategyLabel = computed(() => {
  if (!mixcutEnabled.value) {
    return "短剧剪辑";
  }
  const contentType = selectedMixcutContentTypeLabel.value;
  const style = selectedMixcutStyleLabel.value;
  return `${contentType} / ${style}`;
});
const currentPromptSeed = computed(() => (mixcutEnabled.value ? mixcutPromptSeed : dramaPromptSeed));
const currentPromptSuffix = computed(() => (mixcutEnabled.value ? mixcutPromptSuffix : dramaPromptSuffix));
const mixcutTransitionLabel = computed(() => {
  if (form.value.mixcutStylePreset === "music_sync") {
    return "白闪转场";
  }
  return "硬切转场";
});
const visiblePresets = computed(() => {
  const mode = editingMode.value;
  const presets = availablePresets.value.filter((preset) => resolvePresetMode(preset) === mode);
  return presets.length ? presets : availablePresets.value;
});
const hiddenPresetCount = computed(() => Math.max(0, availablePresets.value.length - visiblePresets.value.length));
const presetModeHint = computed(() => {
  if (!hiddenPresetCount.value) {
    return "预设已按当前模式完整展示。";
  }
  return `已按${editingMode.value === "mixcut" ? "混剪" : "短剧"}模式筛选，另有 ${hiddenPresetCount.value} 个其它模式预设。`;
});
const validationChecklist = computed<CreateValidationItem[]>(() => {
  const titleValid = Boolean(form.value.title.trim());
  const sourceCountValid =
    sourceFileCount.value >= 1 &&
    (mixcutEnabled.value ? sourceFileCount.value >= 2 : sourceFileCount.value === 1);
  const durationValid = form.value.minDurationSeconds <= form.value.maxDurationSeconds;
  const outputCountValid = form.value.outputCount >= 1 && form.value.outputCount <= 10;

  return [
    {
      key: "title",
      label: "任务标题",
      hint: "需填写非空标题",
      passed: titleValid,
    },
    {
      key: "sources",
      label: "素材数量",
      hint: mixcutEnabled.value ? "混剪至少 2 条素材" : "短剧仅允许 1 条主素材",
      passed: sourceCountValid,
    },
    {
      key: "duration",
      label: "时长区间",
      hint: "最小时长不能大于最大时长",
      passed: durationValid,
    },
    {
      key: "output",
      label: "产出数量",
      hint: "需在 1-10 条之间",
      passed: outputCountValid,
    },
  ];
});
const isFormReady = computed(() => validationChecklist.value.every((item) => item.passed));
const submitButtonLabel = computed(() => {
  if (submitting.value) {
    return "提交中...";
  }
  return isFormReady.value ? "开始生成" : "请先修正参数";
});

const sourceHint = computed(() => {
  if (cloneSource.value) {
    return `来自任务：${cloneSource.value.title}`;
  }
  return "当前为新任务";
});

const cloneFromHint = computed(() => {
  if (cloneSource.value) {
    return "已带入历史参数，提交前记得重新上传原视频。";
  }
  return "点预设卡片可快速带入一套参数。";
});

const transcriptModeLabel = computed(() => {
  const text = form.value.transcriptText?.trim() ?? "";
  if (!text) {
    return "未提供";
  }
  return /-->/.test(text) ? "带时间戳字幕" : "纯文本语义";
});

const transcriptStats = computed(() => {
  const text = form.value.transcriptText?.trim() ?? "";
  if (!text) {
    return {
      summary: "未提供语义输入",
      quality: "基础模式",
      hint: "当前主要依据提示词、素材元信息和候选片段做规划。"
    };
  }

  const lineCount = text.split(/\r?\n/).filter(Boolean).length;
  const hasTiming = /-->/.test(text);
  if (hasTiming) {
    return {
      summary: `${lineCount} 行字幕/台词`,
      quality: "语义切点模式",
      hint: "模型会优先参考字幕时间边界决定切点。"
    };
  }

  return {
    summary: `${lineCount} 行纯文本`,
    quality: "语义弱引导模式",
    hint: "有语义，但没有时间戳，切点稳定性会弱一些。"
  };
});

const validationHintItems = computed(() =>
  validationChecklist.value.map((item) => `${item.label}：${item.hint}`)
);

function normalizeQueryValue(value: unknown) {
  if (Array.isArray(value)) {
    return value[0] == null ? "" : String(value[0]);
  }
  return value == null ? "" : String(value);
}

function platformLabel(platform: string) {
  switch (platform) {
    case "douyin":
      return "抖音";
    case "kuaishou":
      return "快手";
    case "xiaohongshu":
      return "小红书";
    case "wechat":
      return "视频号";
    default:
      return platform;
  }
}

function resolvePresetMode(preset: TaskPreset): EditingMode {
  return preset.editingMode === "mixcut" ? "mixcut" : "drama";
}

function presetModeLabel(preset: TaskPreset) {
  return resolvePresetMode(preset) === "mixcut" ? "混剪" : "短剧";
}

function presetBadge(preset: TaskPreset) {
  if (resolvePresetMode(preset) === "mixcut") {
    return "多素材分镜";
  }
  switch (preset.platform) {
    case "douyin":
      return "首刷拉停";
    case "wechat":
      return "关系推进";
    case "kuaishou":
      return "追更钩子";
    case "xiaohongshu":
      return "横版精剪";
    default:
      return "预设";
  }
}

function getFileKey(file: File) {
  return `${file.name}:${file.size}:${file.lastModified}`;
}

function formatFileSummary(file: File) {
  const sizeMb = (file.size / 1024 / 1024).toFixed(1);
  return `${sizeMb} MB · ${file.type || "video/*"}`;
}

function stripModePrompt(prompt: string) {
  const text = (prompt || "").trim();
  const suffixes = [mixcutPromptSuffix, dramaPromptSuffix];
  for (const suffix of suffixes) {
    if (text.endsWith(suffix)) {
      return text.slice(0, -suffix.length).trim();
    }
  }
  return text;
}

function applyModePrompt(prompt: string) {
  const base = stripModePrompt((prompt || "").trim()) || currentPromptSeed.value;
  return mixcutEnabled.value ? `${base}\n\n${currentPromptSuffix.value}` : base;
}

function ensureMixcutStyleSelection() {
  const available = currentMixcutStyleOptions.value;
  if (!available.some((item) => item.value === form.value.mixcutStylePreset)) {
    form.value.mixcutStylePreset = available[0]?.value ?? "director";
  }
}

function syncCreativePromptWithMode(prompt: string) {
  form.value.creativePrompt = applyModePrompt(prompt);
}

function keepOnlyPrimarySourceFile() {
  if (sourceFiles.value.length <= 1) {
    return 0;
  }
  const primary = primarySourceFile.value ?? sourceFiles.value[0];
  if (!primary) {
    return 0;
  }
  const removed = sourceFiles.value.filter((item) => item.id !== primary.id);
  removed.forEach((item) => URL.revokeObjectURL(item.previewUrl));
  sourceFiles.value = [
    {
      ...primary,
      isPrimary: true,
    },
  ];
  form.value.sourceFileName = primary.file.name;
  form.value.sourceAssetIds = [primary.id];
  form.value.sourceFileNames = [primary.file.name];
  return removed.length;
}

function setEditingMode(mode: EditingMode) {
  if (mode === editingMode.value) {
    return;
  }
  let modeStatus = mode === "mixcut" ? "已切换到混剪模式" : "已切换到短剧剪辑模式";
  editingMode.value = mode;
  form.value.editingMode = mode;
  form.value.mixcutEnabled = mode === "mixcut";
  if (mode === "mixcut") {
    form.value.mixcutContentType = form.value.mixcutContentType || "generic";
    ensureMixcutStyleSelection();
  } else {
    const removedCount = keepOnlyPrimarySourceFile();
    if (removedCount > 0) {
      modeStatus = `已切换到短剧剪辑模式，并保留主素材，移除了 ${removedCount} 条辅助素材`;
    }
  }
  syncCreativePromptWithMode(form.value.creativePrompt || "");
  statusText.value = modeStatus;
}

function clearSourceFiles() {
  sourceFiles.value.forEach((item) => URL.revokeObjectURL(item.previewUrl));
  sourceFiles.value = [];
  if (videoFileInput.value) {
    videoFileInput.value.value = "";
  }
  form.value.sourceAssetId = "";
  form.value.sourceFileName = "";
  form.value.sourceAssetIds = [];
  form.value.sourceFileNames = [];
  statusText.value = "已清空素材列表";
}

function setPrimarySourceFile(id: string) {
  sourceFiles.value = sourceFiles.value.map((item) => ({
    ...item,
    isPrimary: item.id === id,
  }));
  const primary = primarySourceFile.value;
  if (primary) {
    form.value.sourceFileName = primary.file.name;
    statusText.value = `已设定主素材：${primary.file.name}`;
  }
}

function removeSourceFile(id: string) {
  const target = sourceFiles.value.find((item) => item.id === id);
  if (target) {
    URL.revokeObjectURL(target.previewUrl);
  }
  sourceFiles.value = sourceFiles.value.filter((item) => item.id !== id);
  if (!sourceFiles.value.length) {
    form.value.sourceFileName = "";
    form.value.sourceAssetId = "";
    form.value.sourceAssetIds = [];
    form.value.sourceFileNames = [];
    statusText.value = "素材已移除，等待重新选择";
    return;
  }
  if (!sourceFiles.value.some((item) => item.isPrimary)) {
    sourceFiles.value[0].isPrimary = true;
  }
  const primary = primarySourceFile.value;
  if (primary) {
    form.value.sourceFileName = primary.file.name;
  }
  statusText.value = `已移除素材：${target?.file.name || "未知文件"}`;
}

function applyPreset(preset: TaskPreset) {
  const presetMode = resolvePresetMode(preset);
  if (presetMode !== editingMode.value) {
    setEditingMode(presetMode);
  }
  selectedPresetKey.value = preset.key;
  form.value.platform = preset.platform;
  form.value.aspectRatio = preset.aspectRatio;
  form.value.minDurationSeconds = preset.minDurationSeconds;
  form.value.maxDurationSeconds = preset.maxDurationSeconds;
  form.value.outputCount = preset.outputCount;
  form.value.introTemplate = preset.introTemplate;
  form.value.outroTemplate = preset.outroTemplate;
  form.value.editingMode = editingMode.value;
  form.value.mixcutEnabled = mixcutEnabled.value;
  if (presetMode === "mixcut") {
    form.value.mixcutContentType = preset.mixcutContentType || form.value.mixcutContentType || "generic";
    form.value.mixcutStylePreset = preset.mixcutStylePreset || form.value.mixcutStylePreset || "director";
  }
  ensureMixcutStyleSelection();
  syncCreativePromptWithMode(preset.creativePrompt ?? "");
  promptSource.value = "模板建议";
  if (!cloneSource.value) {
    form.value.title = preset.defaultTitle;
  }
  statusText.value = `已应用模板：${preset.name}`;
}

function applyCloneSource(task: TaskCloneDraft) {
  clearSourceFiles();
  cloneSource.value = task;
  const cloneMode = task.editingMode || (task.mixcutEnabled ? "mixcut" : "drama");
  const matchedPreset = availablePresets.value.find(
    (preset) =>
      resolvePresetMode(preset) === cloneMode &&
      preset.platform === task.platform &&
      preset.aspectRatio === task.aspectRatio
  );
  selectedPresetKey.value = matchedPreset?.key ?? "custom";
  form.value.title = task.title;
  form.value.platform = task.platform;
  form.value.aspectRatio = task.aspectRatio;
  form.value.minDurationSeconds = task.minDurationSeconds;
  form.value.maxDurationSeconds = task.maxDurationSeconds;
  form.value.outputCount = task.outputCount;
  form.value.introTemplate = task.introTemplate;
  form.value.outroTemplate = task.outroTemplate;
  editingMode.value = cloneMode;
  form.value.editingMode = editingMode.value;
  form.value.mixcutEnabled = mixcutEnabled.value;
  form.value.mixcutContentType = task.mixcutContentType || "generic";
  form.value.mixcutStylePreset = task.mixcutStylePreset || "director";
  ensureMixcutStyleSelection();
  syncCreativePromptWithMode(task.creativePrompt ?? "");
  form.value.transcriptText = task.transcriptText ?? "";
  form.value.sourceFileName = task.sourceFileName;
  form.value.sourceFileNames = task.sourceFileNames ?? [task.sourceFileName];
  promptSource.value = "历史任务复制";
  statusText.value = `已从历史任务「${task.title}」复制参数`;
}

async function handleGeneratePrompt() {
  generatingPrompt.value = true;
  statusText.value = "正在调用大模型生成提示词...";
  try {
    const result = await generateCreativePrompt({
      title:
        form.value.title.trim() ||
        activePreset.value?.defaultTitle ||
        (editingMode.value === "mixcut" ? "混剪分镜编排" : "短剧高能切条"),
      platform: form.value.platform,
      aspectRatio: form.value.aspectRatio,
      minDurationSeconds: form.value.minDurationSeconds,
      maxDurationSeconds: form.value.maxDurationSeconds,
      outputCount: form.value.outputCount,
      introTemplate: form.value.introTemplate,
      outroTemplate: form.value.outroTemplate,
      transcriptText: form.value.transcriptText?.trim() || "",
      sourceFileNames: sourceFiles.value.map((item) => item.file.name),
      editingMode: editingMode.value,
      mixcutEnabled: mixcutEnabled.value,
      mixcutContentType: form.value.mixcutContentType,
      mixcutStylePreset: form.value.mixcutStylePreset,
    });
    syncCreativePromptWithMode(result.prompt);
    promptSource.value = result.source === "fallback" ? "本地建议" : `AI 生成（${result.source}）`;
    statusText.value = "提示词已生成，可继续手动修改。";
  } catch (error) {
    statusText.value = error instanceof Error ? error.message : "提示词生成失败";
  } finally {
    generatingPrompt.value = false;
  }
}

function restorePresetPrompt() {
  syncCreativePromptWithMode(activePreset.value?.creativePrompt ?? "");
  promptSource.value = "模板建议";
  statusText.value = "已恢复模板默认提示词";
}

async function loadPresets() {
  try {
    const remotePresets = (await fetchPresets()).map((preset) => ({
      ...preset,
      editingMode: resolvePresetMode(preset),
    }));
    if (remotePresets.length > 0) {
      availablePresets.value = remotePresets;
      if (!availablePresets.value.some((preset) => preset.key === selectedPresetKey.value)) {
        const fallbackPreset = availablePresets.value.find((preset) => resolvePresetMode(preset) === editingMode.value);
        selectedPresetKey.value = (fallbackPreset ?? availablePresets.value[0]).key;
      }
      if (cloneSource.value) {
        applyCloneSource(cloneSource.value);
      } else {
        const fallbackPreset = availablePresets.value.find((preset) => resolvePresetMode(preset) === editingMode.value);
        applyPreset(fallbackPreset ?? availablePresets.value[0]);
      }
    }
  } catch {
    availablePresets.value = fallbackPresets;
  }
}

async function loadCloneSource() {
  const cloneFrom = normalizeQueryValue(route.query.cloneFrom);
  if (!cloneFrom) {
    return;
  }

  try {
    const task = await cloneTask(cloneFrom);
    applyCloneSource(task);
  } catch {
    statusText.value = "未找到可复制的历史任务，已保留当前表单。";
  }
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const files = Array.from(target.files ?? []);
  target.value = "";
  if (!files.length) {
    return;
  }

  const existingKeys = new Set(sourceFiles.value.map((item) => item.id));
  const added = files
    .filter((file) => !existingKeys.has(getFileKey(file)))
    .map((file) => ({
      id: getFileKey(file),
      file,
      previewUrl: URL.createObjectURL(file),
      isPrimary: false,
    }));

  if (!added.length) {
    statusText.value = "已存在相同素材，未重复添加";
    return;
  }

  sourceFiles.value = [...sourceFiles.value, ...added];
  if (!sourceFiles.value.some((item) => item.isPrimary)) {
    sourceFiles.value[0].isPrimary = true;
  }
  const primary = primarySourceFile.value;
  if (primary) {
    form.value.sourceFileName = primary.file.name;
    if (!form.value.title.trim()) {
      form.value.title = primary.file.name.replace(/\.[^.]+$/, "");
    }
  }
  form.value.sourceAssetIds = sourceFiles.value.map((item) => item.id);
  form.value.sourceFileNames = sourceFiles.value.map((item) => item.file.name);
  if (editingMode.value === "drama" && sourceFiles.value.length > 1) {
    setEditingMode("mixcut");
    statusText.value = `已添加 ${added.length} 条素材，当前共 ${sourceFiles.value.length} 条；系统已自动切换到混剪模式`;
    return;
  }
  statusText.value = `已添加 ${added.length} 条素材，当前共 ${sourceFiles.value.length} 条`;
}

async function handleTranscriptFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  const selectedFile = target.files?.[0];
  if (!selectedFile) {
    return;
  }
  try {
    form.value.transcriptText = await selectedFile.text();
    statusText.value = `已导入字幕文件：${selectedFile.name}`;
  } catch {
    statusText.value = "字幕文件读取失败";
  } finally {
    target.value = "";
  }
}

async function submitTask() {
  if (!isFormReady.value) {
    const firstFailed = validationChecklist.value.find((item) => !item.passed);
    statusText.value = firstFailed ? `${firstFailed.label}未通过：${firstFailed.hint}` : "请先修正参数";
    return;
  }

  form.value.editingMode = editingMode.value;
  form.value.mixcutEnabled = mixcutEnabled.value;
  ensureMixcutStyleSelection();
  const normalizedPrompt = applyModePrompt(form.value.creativePrompt || "");
  const payload: CreateTaskRequest = {
    ...form.value,
    title: form.value.title.trim(),
    creativePrompt: normalizedPrompt,
    transcriptText: form.value.transcriptText?.trim() || "",
    editingMode: editingMode.value,
    mixcutEnabled: mixcutEnabled.value,
    mixcutContentType: form.value.mixcutContentType,
    mixcutStylePreset: form.value.mixcutStylePreset,
    sourceAssetIds: [],
    sourceFileNames: [],
  };

  if (!payload.title) {
    statusText.value = "请输入任务标题";
    return;
  }

  if (payload.minDurationSeconds > payload.maxDurationSeconds) {
    statusText.value = "最小时长不能大于最大时长";
    return;
  }

  submitting.value = true;

  try {
    statusText.value = sourceFiles.value.length > 1 ? "正在上传多素材..." : "正在上传视频...";
    const uploadResults = await Promise.all(sourceFiles.value.map((item) => uploadVideo(item.file)));
    const primaryFile = primarySourceFile.value ?? sourceFiles.value[0];
    const primaryUpload = uploadResults[sourceFiles.value.findIndex((item) => item.id === primaryFile?.id)] ?? uploadResults[0];
    form.value.sourceAssetId = primaryUpload.assetId;
    form.value.sourceFileName = primaryFile?.file.name ?? uploadResults[0].fileName;
    form.value.sourceAssetIds = uploadResults.map((item) => item.assetId);
    form.value.sourceFileNames = sourceFiles.value.map((item) => item.file.name);
    payload.sourceAssetId = primaryUpload.assetId;
    payload.sourceFileName = form.value.sourceFileName;
    payload.sourceAssetIds = uploadResults.map((item) => item.assetId);
    payload.sourceFileNames = sourceFiles.value.map((item) => item.file.name);

    statusText.value = "正在创建任务...";
    const task = await createTask(payload);
    await router.push(`/tasks/${task.id}`);
  } catch (error) {
    statusText.value = error instanceof Error ? error.message : "创建任务失败";
  } finally {
    submitting.value = false;
  }
}

watch(
  () => route.query.cloneFrom,
  async () => {
    const cloneFrom = normalizeQueryValue(route.query.cloneFrom);
    if (!cloneFrom) {
      cloneSource.value = null;
      const fallbackPreset = visiblePresets.value[0] ?? availablePresets.value[0];
      if (fallbackPreset) {
        applyPreset(fallbackPreset);
      }
      return;
    }
    cloneSource.value = null;
    await loadCloneSource();
  },
  { immediate: true }
);

watch(
  () => form.value.mixcutContentType,
  () => {
    ensureMixcutStyleSelection();
  }
);

onMounted(async () => {
  await loadPresets();
});

onBeforeUnmount(() => {
  sourceFiles.value.forEach((item) => URL.revokeObjectURL(item.previewUrl));
});
</script>

<style scoped>
.new-task-view :deep(.surface-panel) {
  border: 1px solid #dbe4ee;
  border-radius: 1.5rem;
  background: #ffffff;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.08);
}

.new-task-view :deep(.surface-panel-warm) {
  background: linear-gradient(180deg, #ffffff, #f8fafc 85%);
}

.new-task-view :deep(.surface-tile),
.new-task-view :deep(.surface-tile-strong) {
  border: 1px solid #dbe4ee;
  border-radius: 1rem;
  background: #f8fafc;
  box-shadow: none;
}

.new-task-view :deep(.surface-chip) {
  border-color: #cbd5e1;
  background: #f1f5f9;
  color: #334155;
}

.new-task-view :deep(.field-input),
.new-task-view :deep(.field-select),
.new-task-view :deep(.field-textarea) {
  border-color: #cbd5e1;
  background: #ffffff;
}

.new-task-view :deep(.field-input:focus),
.new-task-view :deep(.field-select:focus),
.new-task-view :deep(.field-textarea:focus) {
  border-color: #0891b2;
  box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.15);
}

.new-task-view :deep(.btn-primary) {
  background: linear-gradient(135deg, #0e7490, #0891b2);
}

.new-task-view :deep(.btn-primary:hover:not(:disabled)) {
  box-shadow: 0 10px 22px rgba(8, 145, 178, 0.26);
}

.new-task-view :deep(.storyboard-track) {
  gap: 0.75rem;
}
</style>
