<template>
  <section class="grid gap-6 xl:grid-cols-[1.08fr_0.92fr]">
    <div class="surface-panel surface-panel-warm p-6">
      <PageHeader
        eyebrow="创建任务"
        title="新建剪辑任务"
        description="先选模式，再补素材和语义线索。当前页支持 AI 自动生成提示词和手动精修，但短剧剪辑与混剪会走完全不同的分支。"
      />

      <div class="mb-6 grid gap-3 xl:grid-cols-2">
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
              <p class="text-xs uppercase tracking-[0.28em] text-slate-400">{{ option.kicker }}</p>
              <h3 class="mt-2 text-lg font-semibold text-white">{{ option.label }}</h3>
            </div>
            <span class="surface-chip text-[11px] font-semibold">{{ editingMode === option.value ? "当前模式" : "切换至此" }}</span>
          </div>
          <p class="mt-3 text-sm leading-6 text-slate-300">{{ option.description }}</p>
          <div class="mt-4 flex flex-wrap gap-2 text-xs text-slate-300">
            <span v-for="tag in option.tags" :key="tag" class="surface-chip">{{ tag }}</span>
          </div>
        </button>
      </div>

      <div class="mb-6 grid gap-3 xl:grid-cols-3">
        <button
          v-for="preset in visiblePresets"
          :key="preset.key"
          type="button"
          class="group relative overflow-hidden rounded-[26px] border p-4 text-left transition duration-300 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-200/60 active:scale-[0.99]"
          :class="selectedPresetKey === preset.key ? 'border-amber-300/45 bg-[linear-gradient(180deg,rgba(245,158,11,0.18),rgba(59,130,246,0.08))] shadow-[0_20px_46px_rgba(245,158,11,0.16),inset_0_1px_0_rgba(255,255,255,0.08)]' : 'border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.025))] hover:-translate-y-0.5 hover:border-sky-300/28 hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.09),rgba(255,255,255,0.035))] hover:shadow-[0_18px_40px_rgba(0,0,0,0.2)]'"
          @click="applyPreset(preset)"
        >
          <div class="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-xs uppercase tracking-[0.28em] text-slate-400">{{ presetBadge(preset) }}</p>
              <h3 class="mt-2 text-base font-semibold text-white">{{ preset.name }}</h3>
            </div>
            <div class="flex flex-wrap justify-end gap-2">
              <span class="surface-chip text-[11px] font-semibold">{{ presetModeLabel(preset) }}</span>
              <span class="surface-chip text-[11px] font-semibold">{{ platformLabel(preset.platform) }}</span>
            </div>
          </div>
          <p class="mt-3 text-sm leading-6 text-slate-300">{{ preset.description }}</p>
          <div class="mt-4 flex flex-wrap gap-2 text-xs text-slate-300">
            <span class="surface-chip">{{ preset.aspectRatio }}</span>
            <span class="surface-chip">{{ preset.minDurationSeconds }}-{{ preset.maxDurationSeconds }} 秒</span>
            <span class="surface-chip">{{ preset.outputCount }} 条</span>
          </div>
        </button>
      </div>
      <p class="mb-6 text-xs text-slate-400">{{ presetModeHint }}</p>

      <form class="grid gap-5" @submit.prevent="submitTask">
        <label class="grid gap-2 text-sm text-slate-200">
          任务标题
          <input v-model="form.title" required class="field-input" placeholder="例如：第 12 集高能反转投放版" />
        </label>

        <div class="surface-tile grid gap-4 p-4">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-white">原始视频</p>
              <p class="mt-1 text-xs leading-5 text-slate-400">
                {{ sourcePanelHint }}
              </p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button type="button" class="btn-primary btn-sm" @click="videoFileInput?.click()">
                选择 / 追加视频
              </button>
              <span class="surface-chip text-[11px] font-semibold">{{ editingModeLabel }}</span>
            </div>
          </div>

          <input ref="videoFileInput" type="file" accept="video/*" multiple class="hidden" @change="onFileChange" />

          <div class="flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span class="surface-chip">{{ sourceFileCountLabel }}</span>
            <span class="surface-chip">{{ fileSummary }}</span>
            <span class="surface-chip">{{ editingModeStatusLabel }}</span>
          </div>

          <div v-if="sourceFiles.length" class="grid gap-3">
            <article
              v-for="item in sourceFiles"
              :key="item.id"
              class="surface-tile flex flex-wrap items-center justify-between gap-3 px-4 py-3"
              :class="item.isPrimary ? 'border-sky-300/30 bg-[linear-gradient(180deg,rgba(8,47,73,0.8),rgba(10,20,38,0.92))]' : ''"
            >
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <p class="truncate text-sm font-semibold text-white">{{ item.file.name }}</p>
                  <span v-if="item.isPrimary" class="surface-chip text-[11px] font-semibold text-sky-100">主素材</span>
                </div>
                <p class="mt-1 text-xs text-slate-400">{{ formatFileSummary(item.file) }}</p>
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
          <div v-else class="rounded-[22px] border border-dashed border-white/12 bg-slate-950/40 p-5 text-sm text-slate-400">
            暂未选择素材。{{ editingMode === "mixcut" ? "建议至少选择 2 条视频用于混剪，能显著提升分镜编排空间。" : "短剧模式只支持 1 条主视频；如需多素材编排请切换到混剪模式。" }}
          </div>

          <div class="surface-tile grid gap-3 p-4" :class="editingMode === 'mixcut' ? 'border-sky-300/20 bg-[linear-gradient(180deg,rgba(8,47,73,0.52),rgba(8,16,32,0.58))]' : 'border-rose-300/18 bg-[linear-gradient(180deg,rgba(88,28,135,0.15),rgba(8,16,32,0.52))]'">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p class="text-xs uppercase tracking-[0.24em] text-slate-400">{{ editingMode === 'mixcut' ? '混剪语义' : '短剧语义' }}</p>
                <p class="mt-2 text-sm font-semibold text-white">{{ editingMode === 'mixcut' ? '题材 / 风格 / 分镜编排' : '高燃卡点 / 对白完整 / 情绪推进' }}</p>
              </div>
              <span class="surface-chip text-[11px] font-semibold">{{ editingMode === 'mixcut' ? "分镜脚本模式" : "剧情卡点模式" }}</span>
            </div>
            <p class="text-sm leading-6 text-slate-300">{{ editingMode === 'mixcut' ? mixcutModeHint : dramaModeHint }}</p>
            <div class="flex flex-wrap gap-2">
              <span v-for="tag in editingMode === 'mixcut' ? mixcutModeTags : dramaModeTags" :key="tag" class="surface-chip">{{ tag }}</span>
            </div>
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-200">
            投放平台
            <select v-model="form.platform" class="field-select">
              <option value="douyin">抖音</option>
              <option value="kuaishou">快手</option>
              <option value="xiaohongshu">小红书</option>
              <option value="wechat">视频号</option>
            </select>
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            画幅比例
            <select v-model="form.aspectRatio" class="field-select">
              <option value="9:16">竖版 9:16</option>
              <option value="16:9">横版 16:9</option>
            </select>
          </label>
        </div>

        <div v-if="editingMode === 'mixcut'" class="surface-tile grid gap-4 p-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-200">
            混剪题材
            <select v-model="form.mixcutContentType" class="field-select">
              <option v-for="item in mixcutContentTypeOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
            <span class="text-xs text-slate-400">{{ selectedMixcutContentTypeHint }}</span>
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            混剪风格
            <select v-model="form.mixcutStylePreset" class="field-select">
              <option v-for="item in currentMixcutStyleOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
            <span class="text-xs text-slate-400">{{ selectedMixcutStyleHint }}</span>
          </label>
        </div>
        <div v-else class="surface-tile grid gap-4 p-4 sm:grid-cols-2">
          <div class="grid gap-2 text-sm text-slate-200">
            <p>短剧剪辑重点</p>
            <div class="flex flex-wrap gap-2 text-xs text-slate-300">
              <span class="surface-chip">对白完整</span>
              <span class="surface-chip">高燃卡点</span>
              <span class="surface-chip">反转收尾</span>
            </div>
            <p class="text-xs leading-5 text-slate-400">{{ dramaModeHint }}</p>
          </div>
          <div class="grid gap-2 text-sm text-slate-200">
            <p>提示词策略</p>
            <div class="flex flex-wrap gap-2 text-xs text-slate-300">
              <span class="surface-chip">{{ editingModePromptChipLabel }}</span>
              <span class="surface-chip">优先保留关键对白</span>
              <span class="surface-chip">结尾留悬念</span>
            </div>
            <p class="text-xs leading-5 text-slate-400">这一模式不强调题材风格切换，而是强调冲突、信息量和节奏钩子。</p>
          </div>
        </div>

        <div class="grid gap-4 sm:grid-cols-3">
          <label class="grid gap-2 text-sm text-slate-200">
            最小时长（秒）
            <input v-model.number="form.minDurationSeconds" type="number" min="5" max="120" class="field-input" />
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            最大时长（秒）
            <input v-model.number="form.maxDurationSeconds" type="number" min="5" max="120" class="field-input" />
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            产出数量
            <input v-model.number="form.outputCount" type="number" min="1" max="10" class="field-input" />
          </label>
        </div>

        <div class="grid gap-4 sm:grid-cols-2">
          <label class="grid gap-2 text-sm text-slate-200">
            片头模板
            <select v-model="form.introTemplate" class="field-select">
              <option v-for="item in introTemplateOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
            <span class="text-xs text-slate-400">{{ selectedIntroTemplateHint }}</span>
          </label>
          <label class="grid gap-2 text-sm text-slate-200">
            片尾模板
            <select v-model="form.outroTemplate" class="field-select">
              <option v-for="item in outroTemplateOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
            </select>
            <span class="text-xs text-slate-400">{{ selectedOutroTemplateHint }}</span>
          </label>
        </div>

          <div class="surface-tile p-4">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p class="text-sm font-semibold text-white">创意提示词</p>
                <p class="mt-1 text-xs leading-5 text-slate-400">
                可以直接手动写，也可以让大模型先给你起一版更像投放策划的中文提示词。当前模式会自动追加对应约束。
                </p>
              </div>
              <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="btn-primary btn-sm"
                :disabled="generatingPrompt"
                @click="handleGeneratePrompt"
              >
                {{ generatingPrompt ? "生成中..." : "AI 自动生成" }}
              </button>
              <button type="button" class="btn-ghost btn-sm" @click="restorePresetPrompt">
                恢复模板建议
              </button>
            </div>
          </div>
          <textarea v-model="form.creativePrompt" rows="5" class="field-textarea mt-4" placeholder="例如：开头直接给冲突场面，保留关键对白完整度，结尾停在反问或表情反转，适合首刷拉停。"></textarea>
          <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span class="surface-chip">{{ promptSourceLabel }}</span>
            <span class="surface-chip">{{ mixcutPromptChipLabel }}</span>
            <span>支持自动生成后继续手动改写。</span>
          </div>
        </div>

        <label class="grid gap-2 text-sm text-slate-200">
          字幕 / 台词文本（可选）
          <input ref="transcriptFileInput" type="file" accept=".srt,.vtt,.txt" class="hidden" @change="handleTranscriptFileChange" />
          <textarea
            v-model="form.transcriptText"
            rows="8"
            class="field-textarea font-mono text-sm"
            placeholder="建议粘贴 SRT / VTT 或带时间戳台词。没有时间戳时，模型只能优化语义，不能稳定决定切点。"
          ></textarea>
          <div class="flex flex-wrap items-center gap-2">
            <button
              type="button"
              class="btn-secondary btn-sm"
              @click="transcriptFileInput?.click()"
            >
              导入字幕文件
            </button>
            <span class="text-xs text-slate-400">{{ transcriptStats.summary }}</span>
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
          <p class="text-sm text-slate-300">{{ statusText }}</p>
        </div>
      </form>
    </div>

    <aside class="space-y-4">
      <div class="surface-panel surface-panel-warm p-6">
        <PageHeader
          :eyebrow="editingMode === 'mixcut' ? '混剪预演' : '短剧预演'"
          :title="editingMode === 'mixcut' ? '题材 / 风格 / 分镜脚本' : '卡点 / 对白 / 悬念收束'"
          :description="editingMode === 'mixcut' ? '提交前先确认这次任务会按什么题材、什么节奏和什么分镜脚本去切。' : '提交前先确认这次任务会围绕高燃卡点、对白完整和情绪落点去切。'"
        />

        <div class="grid gap-3">
          <div class="surface-tile-strong grid gap-4 p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p class="text-xs uppercase tracking-[0.24em] text-slate-400">{{ editingMode === "mixcut" ? "当前混剪配置" : "当前短剧配置" }}</p>
                <p class="mt-2 text-lg font-semibold text-white">{{ editingMode === "mixcut" ? mixcutStrategyLabel : "高燃卡点 / 对白完整" }}</p>
              </div>
              <span class="surface-chip text-[11px] font-semibold">{{ editingModeLabel }}</span>
            </div>
            <div class="grid gap-2 text-sm text-slate-300">
              <div class="flex flex-wrap items-center gap-2">
                <span v-if="editingMode === 'mixcut'" class="surface-chip">题材 · {{ selectedMixcutContentTypeLabel }}</span>
                <span v-if="editingMode === 'mixcut'" class="surface-chip">风格 · {{ selectedMixcutStyleLabel }}</span>
                <span class="surface-chip">{{ editingMode === "mixcut" ? `转场 · ${mixcutTransitionLabel}` : "对白完整 / 高燃卡点" }}</span>
              </div>
              <p class="leading-6 text-slate-300">{{ editingMode === "mixcut" ? selectedMixcutContentTypeHint : dramaModeHint }}</p>
              <p class="leading-6 text-slate-400">{{ editingMode === "mixcut" ? selectedMixcutStyleHint : "当前仍可先确认片头、片尾和默认模板，适合短剧剪辑的剧情节奏。" }}</p>
            </div>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <div class="surface-tile p-4">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">片头模板</p>
              <p class="mt-2 text-sm font-semibold text-white">{{ selectedIntroTemplateLabel }}</p>
              <p class="mt-2 text-xs leading-5 text-slate-400">{{ selectedIntroTemplateHint }}</p>
            </div>
            <div class="surface-tile p-4">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">片尾模板</p>
              <p class="mt-2 text-sm font-semibold text-white">{{ selectedOutroTemplateLabel }}</p>
              <p class="mt-2 text-xs leading-5 text-slate-400">{{ selectedOutroTemplateHint }}</p>
            </div>
          </div>

          <div class="surface-tile p-4">
            <div class="flex flex-wrap items-center justify-between gap-3">
              <p class="text-xs uppercase tracking-[0.24em] text-slate-400">{{ editingMode === "mixcut" ? "分镜预演" : "短剧预演" }}</p>
              <span class="surface-chip text-[11px] font-semibold">{{ editingMode === "mixcut" ? mixcutTransitionLabel : "高燃卡点" }}</span>
            </div>
            <div class="storyboard-track mt-4">
              <article class="storyboard-segment rounded-[24px] border border-white/8 bg-slate-950/50 p-4">
                <p class="text-[11px] uppercase tracking-[0.26em] text-slate-500">{{ editingMode === "mixcut" ? "分镜开场" : "高燃起势" }}</p>
                <p class="mt-2 text-sm font-semibold text-white">{{ editingMode === "mixcut" ? selectedIntroTemplateLabel : "对白 / 冲突起势" }}</p>
                <p class="mt-2 text-xs leading-5 text-slate-400">{{ editingMode === "mixcut" ? selectedIntroTemplateHint : dramaModeHint }}</p>
              </article>
              <article class="storyboard-segment rounded-[24px] border border-white/8 bg-slate-950/50 p-4">
                <p class="text-[11px] uppercase tracking-[0.26em] text-slate-500">{{ editingMode === "mixcut" ? "推进轨道" : "卡点轨道" }}</p>
                <p class="mt-2 text-sm font-semibold text-white">{{ editingMode === "mixcut" ? `${selectedMixcutContentTypeLabel} / ${selectedMixcutStyleLabel}` : "高燃卡点 / 情绪推进" }}</p>
                <p class="mt-2 text-xs leading-5 text-slate-400">{{ editingMode === "mixcut" ? selectedMixcutStyleHint : "短剧模式会围绕对白完整和爆点节奏组织提示词与切点。" }}</p>
              </article>
              <article class="storyboard-segment rounded-[24px] border border-white/8 bg-slate-950/50 p-4">
                <p class="text-[11px] uppercase tracking-[0.26em] text-slate-500">{{ editingMode === "mixcut" ? "收束轨道" : "悬念收尾" }}</p>
                <p class="mt-2 text-sm font-semibold text-white">{{ editingMode === "mixcut" ? selectedOutroTemplateLabel : "悬念 / 反转" }}</p>
                <p class="mt-2 text-xs leading-5 text-slate-400">{{ editingMode === "mixcut" ? selectedOutroTemplateHint : "短剧模式优先保留下一句欲望或反转收尾。" }}</p>
              </article>
            </div>
          </div>
        </div>
      </div>

      <div class="surface-panel p-6">
        <PageHeader
          eyebrow="参数摘要"
          title="参数摘要"
          description="当前模板、文件状态和提交参数会同步显示在这里，减少来回确认。"
        />

        <div class="grid gap-3 sm:grid-cols-2">
          <div class="surface-tile p-4">
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">当前模板</p>
            <p class="mt-2 text-sm font-semibold text-white">{{ activePreset?.name || "自定义" }}</p>
            <p class="mt-2 text-xs leading-5 text-slate-400">{{ activePreset?.description || "手动配置任务参数" }}</p>
          </div>
          <div class="surface-tile p-4">
            <p class="text-xs uppercase tracking-[0.24em] text-slate-400">来源</p>
            <p class="mt-2 text-sm font-semibold text-white">{{ sourceHint }}</p>
            <p class="mt-2 text-xs leading-5 text-slate-400">{{ cloneFromHint }}</p>
          </div>
        </div>

        <div class="mt-4 grid gap-2 text-sm text-slate-300">
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>平台</span>
            <span class="font-medium text-white">{{ platformLabel(form.platform) }}</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>画幅 / 时长</span>
            <span class="font-medium text-white">{{ form.aspectRatio }} / {{ form.minDurationSeconds }}-{{ form.maxDurationSeconds }} 秒</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>产出数量</span>
            <span class="font-medium text-white">{{ form.outputCount }} 条</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>素材数量</span>
            <span class="font-medium text-white">{{ sourceFileCount }} 条</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>剪辑模式</span>
            <span class="font-medium text-white">{{ editingModeLabel }}</span>
          </div>
          <div v-if="editingMode === 'mixcut'" class="surface-tile flex items-center justify-between px-4 py-3">
            <span>混剪题材 / 风格</span>
            <span class="font-medium text-white">{{ mixcutStrategyLabel }}</span>
          </div>
          <div v-else class="surface-tile flex items-center justify-between px-4 py-3">
            <span>短剧语义</span>
            <span class="font-medium text-white">高燃卡点 / 对白完整</span>
          </div>
          <div class="surface-tile flex items-center justify-between px-4 py-3">
            <span>语义素材</span>
            <span class="font-medium text-white">{{ transcriptModeLabel }}</span>
          </div>
          <div class="surface-tile px-4 py-3">
            <p class="text-xs uppercase tracking-[0.22em] text-slate-400">输入质量</p>
            <p class="mt-2 text-sm font-medium text-white">{{ transcriptStats.quality }}</p>
            <p class="mt-1 text-xs leading-5 text-slate-400">{{ transcriptStats.hint }}</p>
          </div>
          <div class="surface-tile px-4 py-3">
            <div class="flex items-center justify-between gap-3">
              <p class="text-xs uppercase tracking-[0.22em] text-slate-400">提交校验</p>
              <span class="surface-chip text-[11px] font-semibold">
                {{ isFormReady ? "可提交" : "待修正" }}
              </span>
            </div>
            <ul class="mt-3 grid gap-2 text-xs">
              <li
                v-for="item in validationChecklist"
                :key="item.key"
                class="flex items-start justify-between gap-3 rounded-2xl border border-white/8 bg-slate-950/40 px-3 py-2"
              >
                <div>
                  <p class="font-medium text-slate-200">{{ item.label }}</p>
                  <p class="mt-0.5 text-slate-500">{{ item.hint }}</p>
                </div>
                <span :class="item.passed ? 'text-emerald-300' : 'text-rose-300'" class="shrink-0 font-semibold">
                  {{ item.passed ? "通过" : "待修正" }}
                </span>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <div class="surface-panel p-6">
        <PageHeader
          eyebrow="素材预览"
          title="视频预览"
          description="上传后会在这里显示主素材预览，左侧列表可继续追加、切换或移除素材。"
        />
        <div v-if="primaryPreviewUrl" class="surface-tile overflow-hidden bg-slate-950/60">
          <video :src="primaryPreviewUrl" controls class="aspect-video w-full bg-black object-cover"></video>
          <div class="border-t border-white/10 p-4 text-sm text-slate-300">
            <p class="font-medium text-white">{{ fileName }}</p>
            <p class="mt-1">{{ fileSummary }}</p>
          </div>
        </div>
        <div v-else class="surface-tile border-dashed bg-slate-950/40 p-8 text-center text-sm text-slate-300">
          选择视频后可在这里预览文件。
        </div>
      </div>

      <div class="surface-panel p-6">
        <PageHeader
          eyebrow="操作建议"
          title="创建前建议"
          description="先把模式、素材数量和语义输入三个变量控制住。"
        />
        <ul class="grid gap-3 text-sm leading-6 text-slate-300">
          <li>短剧模式优先提供带时间戳字幕，卡点和对白完整度会更稳定。</li>
          <li>混剪模式适合多素材联动，系统会自动追加题材和分镜脚本约束。</li>
          <li>旅游素材建议进入混剪模式，再根据目标选择“城市漫游 / 风景大片 / 治愈慢游 / 公路旅拍”。</li>
          <li>短剧模式建议片头直接进冲突，片尾停在反问、表情反转或关系未落地的瞬间。</li>
          <li>混剪模式建议先想清楚脚本节奏，再决定静帧、插叙和运动镜头的配比。</li>
          <li>AI 生成提示词后，最好再手动补一句你最想要的节奏要求。</li>
        </ul>
      </div>
    </aside>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { cloneTask, createTask, fetchPresets, generateCreativePrompt, uploadVideo } from "@/api/tasks";
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
  { value: "travel", label: "旅游混剪", hint: "更关注景别、地点切换、氛围推进和卡点节奏。" },
  { value: "drama", label: "剧情混剪", hint: "更关注冲突、对白、反转和情绪递进。" },
] as const;

const editingModeOptions = [
  {
    value: "drama",
    kicker: "Drama Cut",
    label: "短剧剪辑",
    description: "围绕高燃卡点、对白完整和情绪落点做投放切条，强调剧情连续性，不强调题材风格切换。",
    tags: ["高燃卡点", "对白完整", "反转落点"],
    activeClass:
      "border-rose-300/40 bg-[linear-gradient(180deg,rgba(225,29,72,0.16),rgba(59,130,246,0.08))] shadow-[0_20px_46px_rgba(225,29,72,0.16),inset_0_1px_0_rgba(255,255,255,0.08)]",
    inactiveClass:
      "border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.025))] hover:-translate-y-0.5 hover:border-rose-300/24 hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.09),rgba(255,255,255,0.035))] hover:shadow-[0_18px_40px_rgba(0,0,0,0.2)]",
  },
  {
    value: "mixcut",
    kicker: "Mixcut",
    label: "混剪",
    description: "围绕题材、风格和分镜脚本编排多素材，强调镜头结构、静帧插叙和导演感排布。",
    tags: ["题材", "风格", "分镜编排"],
    activeClass:
      "border-sky-300/40 bg-[linear-gradient(180deg,rgba(56,189,248,0.16),rgba(16,185,129,0.08))] shadow-[0_20px_46px_rgba(56,189,248,0.14),inset_0_1px_0_rgba(255,255,255,0.08)]",
    inactiveClass:
      "border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.06),rgba(255,255,255,0.025))] hover:-translate-y-0.5 hover:border-sky-300/24 hover:bg-[linear-gradient(180deg,rgba(255,255,255,0.09),rgba(255,255,255,0.035))] hover:shadow-[0_18px_40px_rgba(0,0,0,0.2)]",
  },
] as const;

const mixcutStyleOptions = {
  generic: [
    { value: "director", label: "导演感推进", hint: "适合通用混剪，突出镜头对照和节奏推进。" },
    { value: "music_sync", label: "音乐卡点", hint: "强化节奏点和快切感，更适合强节奏 BGM。" },
  ],
  travel: [
    { value: "travel_citywalk", label: "城市漫游", hint: "适合街景、店铺、人流和 citywalk 氛围。" },
    { value: "travel_landscape", label: "风景大片", hint: "适合航拍、地标、景观和空间建立。" },
    { value: "travel_healing", label: "治愈慢游", hint: "适合慢节奏、柔和氛围和治愈感旅行片。" },
    { value: "travel_roadtrip", label: "公路旅拍", hint: "适合移动镜头、窗景、路况和出发感。" },
  ],
  drama: [
    { value: "director", label: "导演感推进", hint: "适合冲突递进、人物关系对照和高点收束。" },
    { value: "music_sync", label: "音乐卡点", hint: "适合更强节奏的剧情快切和爆点推进。" },
  ],
} as const;

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
    key: "travel_storyboard_mixcut",
    name: "旅行分镜混剪",
    description: "适合多段旅游素材的导演感混剪，强调镜头编排和地点氛围推进。",
    defaultTitle: "旅行分镜混剪版",
    editingMode: "mixcut",
    platform: "xiaohongshu",
    aspectRatio: "9:16",
    minDurationSeconds: 20,
    maxDurationSeconds: 45,
    outputCount: 3,
    introTemplate: "cold_open",
    outroTemplate: "suspense_hold",
    creativePrompt: "先设计分镜脚本，再组织多素材镜头；开场可用静帧快闪，主体用景别和地点切换推进，结尾留余韵。",
    mixcutContentType: "travel",
    mixcutStylePreset: "travel_landscape"
  }
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
    return "支持多选视频素材，建议选择 2-5 条作为混剪输入。";
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
    ? "混剪模式已选中，系统会围绕题材 / 风格 / 分镜编排工作"
    : "短剧剪辑模式已选中，系统会围绕高燃卡点 / 对白完整工作"
);
const editingModePromptChipLabel = computed(() =>
  editingMode.value === "mixcut" ? "已追加混剪提示词" : "已追加短剧提示词"
);
const sourcePanelHint = computed(() =>
  editingMode.value === "mixcut"
    ? "支持一次选择多个视频，混剪模式会围绕题材、风格和分镜脚本整理输入。"
    : "短剧模式只支持一个主视频，系统会围绕高燃卡点和对白完整整理输入。"
);
const dramaModeHint = computed(() =>
  "短剧模式更看重高燃卡点、对白完整、冲突升级和情绪落点。系统会优先围绕剧情推进来生成提示词与切点。"
);
const mixcutModeHint = computed(() =>
  "混剪模式更看重题材、风格、镜头编排和静帧插叙。系统会优先围绕多素材导演脚本来生成提示词与切点。"
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
  if (form.value.mixcutStylePreset === "music_sync" || form.value.mixcutStylePreset === "travel_citywalk") {
    return "白闪转场";
  }
  if (form.value.mixcutStylePreset === "travel_landscape" || form.value.mixcutStylePreset === "travel_healing" || form.value.mixcutStylePreset === "travel_roadtrip") {
    return "黑场过渡";
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
    return "已复制历史任务参数，请重新上传对应原视频后提交。";
  }
  return "点击预设卡片即可快速填充任务配置。";
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
      hint: "当前只会根据创意提示、元信息和候选片段做规划。"
    };
  }

  const lineCount = text.split(/\r?\n/).filter(Boolean).length;
  const hasTiming = /-->/.test(text);
  if (hasTiming) {
    return {
      summary: `${lineCount} 行字幕/台词`,
      quality: "语义切点模式",
      hint: "模型会优先参考字幕时间边界决定切点，适合短剧剧情剪辑。"
    };
  }

  return {
    summary: `${lineCount} 行纯文本`,
    quality: "语义弱引导模式",
    hint: "有语义，但没有时间戳，模型更适合优化标题和候选理由。"
  };
});

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
