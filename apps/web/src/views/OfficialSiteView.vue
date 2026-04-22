<template>
  <main ref="scrollRoot" class="official-site" id="top">
    <div class="official-site__shell">
      <MarketingTopbar active-page="home" scroll-sections @section-request="scrollToSection" />

      <section class="hero-section reveal-on-scroll is-visible">
        <div class="hero-section__copy">
          <p class="hero-section__eyebrow">AI 短剧视频生产工作台</p>
          <h1 class="hero-section__title">
            <span class="hero-section__title-text">{{ typedHeadline }}</span>
            <span class="hero-section__caret" aria-hidden="true"></span>
          </h1>
          <p class="hero-section__slogan">把灵感煎成镜头</p>

          <div class="hero-section__actions">
            <RouterLink class="hero-button hero-button-primary" to="/generate">开始创作</RouterLink>
            <a class="hero-button hero-button-secondary" href="#solutions" @click.prevent="scrollToSection('solutions')">查看案例方案</a>
          </div>

          <p class="hero-strip__status">{{ showcaseStatusText }}</p>

          <div v-if="heroFrames.length" class="hero-strip" aria-label="案例预览">
            <article v-for="(frame, index) in heroFrames" :key="frame.id"
              class="hero-strip__frame reveal-on-scroll floating-panel" :style="{
                '--frame-scene': frame.scene,
                '--reveal-delay': `${120 + index * 70}ms`,
                '--float-delay': `${index * 0.9}s`
              }">
              <div class="hero-strip__visual">
                <video v-if="frame.previewUrl" class="showcase-media" :src="frame.previewUrl" autoplay loop muted
                  playsinline preload="metadata"></video>
                <div v-else class="showcase-placeholder showcase-placeholder-compact"
                  :class="`showcase-placeholder--${frame.placeholderMeta.layout}`" :style="frame.placeholderStyle">
                  <div class="showcase-placeholder__scene" aria-hidden="true">
                    <span class="showcase-placeholder__beam"></span>
                    <span class="showcase-placeholder__subject-shadow"></span>
                    <span class="showcase-placeholder__subject"></span>
                    <span class="showcase-placeholder__monitor"></span>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </div>
      </section>

      <div class="official-site__grid">
        <div class="official-site__main">
          <section class="content-section reveal-on-scroll" id="features">
            <div class="section-heading">
              <p>核心能力</p>
              <h2>不是零散演示，而是一套面向生产的内容模块。</h2>
            </div>

            <div class="feature-grid">
              <article v-for="(feature, index) in features" :key="feature.title" class="feature-card reveal-on-scroll"
                :style="{ '--reveal-delay': `${index * 90}ms` }">
                <div class="feature-card__icon">{{ feature.icon }}</div>
                <h3>{{ feature.title }}</h3>
                <p>{{ feature.description }}</p>
                <div class="feature-card__footer">
                  <span>{{ feature.meta }}</span>
                </div>
              </article>
            </div>
          </section>

          <section class="content-section reveal-on-scroll">
            <div class="section-heading">
              <p>模型展示</p>
              <h2>把多个提供方放进一条清晰可见的生成链路里。</h2>
            </div>

            <div class="showcase-card">
              <div class="showcase-card__map">
                <article v-for="(model, index) in showcaseModels" :key="model.key"
                  class="showcase-node reveal-on-scroll floating-panel" :class="model.className" :style="{
                    '--reveal-delay': `${100 + index * 70}ms`,
                    '--float-delay': `${index * 0.7}s`
                  }">
                  <div class="showcase-node__badge">{{ model.badge }}</div>
                  <strong>{{ model.name }}</strong>
                  <span>{{ model.vendor }}</span>
                </article>
              </div>

              <aside class="showcase-card__details reveal-on-scroll" style="--reveal-delay: 280ms">
                <p>链路详情</p>
                <pre>{{ showcaseDetailsJson }}</pre>
                <div class="showcase-card__endpoint">
                  <span>最新结果地址</span>
                  <code>{{ showcaseEndpointLabel }}</code>
                </div>
              </aside>
            </div>
          </section>

          <section class="content-section reveal-on-scroll" id="solutions">
            <div class="section-heading">
              <p>解决方案</p>
              <h2>针对短剧内容生产预设好结构、节奏与镜头风格。</h2>
            </div>

            <div class="solution-list">
              <article v-for="(solution, index) in solutions" :key="solution.title"
                class="solution-card reveal-on-scroll" :style="{
                  '--solution-scene': solution.scene,
                  '--reveal-delay': `${index * 90}ms`
                }">
                <div class="solution-card__visual">
                  <video v-if="solution.previewUrl" class="showcase-media" :src="solution.previewUrl" autoplay loop
                    muted playsinline preload="metadata"></video>
                  <div v-else class="showcase-placeholder showcase-placeholder-expanded"
                    :class="`showcase-placeholder--${solution.placeholderMeta.layout}`" :style="solution.placeholderStyle">
                    <div class="showcase-placeholder__scene" aria-hidden="true">
                      <span class="showcase-placeholder__beam"></span>
                      <span class="showcase-placeholder__subject-shadow"></span>
                      <span class="showcase-placeholder__subject"></span>
                      <span class="showcase-placeholder__monitor"></span>
                    </div>
                  </div>
                </div>
                <div class="solution-card__body">
                  <h3>{{ solution.title }}</h3>
                  <p>{{ solution.description }}</p>
                  <div class="solution-card__rating">
                    <span>评分</span>
                    <strong>{{ solution.rating }}</strong>
                  </div>
                </div>
              </article>
            </div>
          </section>
        </div>

        <aside class="official-site__side">
          <section class="side-card side-card-showcase reveal-on-scroll">
            <div class="side-media">
              <article v-for="(sample, index) in sideSamples" :key="sample.title"
                class="side-media__frame reveal-on-scroll floating-panel" :style="{
                  '--sample-scene': sample.scene,
                  '--reveal-delay': `${90 + index * 90}ms`,
                  '--float-delay': `${index * 0.8}s`
                }">
                <div class="side-media__visual">
                  <video v-if="sample.previewUrl" class="showcase-media" :src="sample.previewUrl" autoplay loop muted
                    playsinline preload="metadata"></video>
                  <div v-else class="showcase-placeholder showcase-placeholder-side"
                    :class="`showcase-placeholder--${sample.placeholderMeta.layout}`" :style="sample.placeholderStyle">
                    <div class="showcase-placeholder__scene" aria-hidden="true">
                      <span class="showcase-placeholder__beam"></span>
                      <span class="showcase-placeholder__subject-shadow"></span>
                      <span class="showcase-placeholder__subject"></span>
                      <span class="showcase-placeholder__monitor"></span>
                    </div>
                  </div>
                </div>
                <div class="side-media__meta">
                  <span>{{ sample.title }}</span>
                  <strong>{{ sample.score }}</strong>
                </div>
              </article>
            </div>

            <div class="side-json">
              <div class="side-json__card reveal-on-scroll" style="--reveal-delay: 180ms">
                <p>参数详情</p>
                <pre>{{ sideDetailsJson }}</pre>
              </div>
              <div class="side-json__card reveal-on-scroll" style="--reveal-delay: 260ms">
                <p>案例结果</p>
                <code>{{ showcaseEndpointLabel }}</code>
              </div>
            </div>
          </section>

          <section class="side-card admin-card reveal-on-scroll">
            <div class="admin-card__content">
              <div>
                <p class="section-heading__eyebrow">后台控制台</p>
                <h2>煎豆后台：完整掌控你的内容生产管线</h2>
              </div>

              <div class="admin-preview reveal-on-scroll floating-panel"
                style="--reveal-delay: 180ms; --float-delay: 0.8s">
                <div class="admin-preview__screen">
                  <span class="admin-preview__bar admin-preview__bar-short"></span>
                  <span class="admin-preview__bar"></span>
                  <span class="admin-preview__chart"></span>
                </div>
              </div>
            </div>

            <div class="admin-card__meta">
              <article v-for="(item, index) in adminItems" :key="item.title" class="reveal-on-scroll"
                :style="{ '--reveal-delay': `${140 + index * 90}ms` }">
                <h3>{{ item.title }}</h3>
                <p>{{ item.description }}</p>
              </article>
            </div>
          </section>

          <footer class="site-footer reveal-on-scroll" id="footer">
            <div class="site-footer__top">
              <div>
                <strong>煎豆</strong>
                <p>把灵感煎成镜头，把流程沉淀成产能。</p>
              </div>
              <img alt="" class="site-footer__logo" src="/brand/jiandou-mark.svg" aria-hidden="true" />
            </div>

            <div class="site-footer__links">
              <article v-for="(group, index) in footerGroups" :key="group.title" class="reveal-on-scroll"
                :style="{ '--reveal-delay': `${index * 80}ms` }">
                <h3>{{ group.title }}</h3>
                <a v-for="item in group.items" :key="item" href="#top" @click.prevent="scrollToSection('top')">{{ item
                }}</a>
              </article>
            </div>

            <div class="site-footer__bottom">
              <span>Copyright © 2026 JianDou</span>
              <span>为 AI 视频内容团队而建</span>
            </div>
          </footer>
        </aside>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import type { TaskShowcaseItem } from "@/types";
import { useTaskShowcase } from "@/composables/useTaskShowcase";
import MarketingTopbar from "@/components/marketing/MarketingTopbar.vue";
import {
  collectShowcaseModelNodes,
  formatShowcaseDuration,
  formatShowcaseRatingLabel,
  formatShowcaseTimeMeta,
  resolveShowcaseVisual,
  selectShowcasePrimaryModel,
} from "@/utils/showcase";

type ShowcasePlaceholderMeta = {
  layout: "left" | "right" | "center";
};

type ShowcasePlaceholderStyle = Record<string, string>;

const scrollRoot = ref<HTMLElement | null>(null);
const typedHeadline = ref("");
const fullHeadline = "从文本到视频\n一键直达";

let typingTimer: number | null = null;
let revealObserver: IntersectionObserver | null = null;
let reducedMotionQuery: MediaQueryList | null = null;
const {
  items: showcaseItems,
  loading: showcaseLoading,
  errorMessage: showcaseErrorMessage,
  generatedAt: showcaseGeneratedAt,
  totalCompletedTasks,
} = useTaskShowcase();

const mockShowcaseItems: TaskShowcaseItem[] = [
  {
    id: "mock-campus-romance-night-run",
    title: "校园重逢夜跑告白",
    status: "COMPLETED",
    createdAt: "2026-04-08T20:15:00+08:00",
    updatedAt: "2026-04-08T20:36:00+08:00",
    sourceFileName: "chapter_12_night_run.txt",
    aspectRatio: "9:16",
    minDurationSeconds: 42,
    maxDurationSeconds: 46,
    completedOutputCount: 3,
    taskSeed: 381204,
    effectRating: 8.9,
    description: "雨后操场、逆光路灯和贴近人物表情的近景切换，适合校园情绪向短剧片段。",
    previewUrl: null,
    downloadUrl: null,
    joinName: "night-run-final.mp4",
    models: {
      textAnalysisModel: "qwen-max",
      visionModel: "qwen-vl-max",
      imageModel: "seedream-3.0",
      videoModel: "seedance-pro"
    },
    media: {
      title: "夜跑告白",
      clipIndex: 1,
      durationSeconds: 44,
      width: 1080,
      height: 1920,
      hasAudio: true
    }
  },
  {
    id: "mock-city-suspense-elevator",
    title: "都市悬疑电梯停电",
    status: "COMPLETED",
    createdAt: "2026-04-10T22:04:00+08:00",
    updatedAt: "2026-04-10T22:29:00+08:00",
    sourceFileName: "ep03_elevator_blackout.txt",
    aspectRatio: "16:9",
    minDurationSeconds: 28,
    maxDurationSeconds: 32,
    completedOutputCount: 2,
    taskSeed: 902771,
    effectRating: 9.2,
    description: "封闭空间压迫感强，镜头语言偏克制，适合悬疑反转和停顿拉 tension 的场景。",
    previewUrl: null,
    downloadUrl: null,
    joinName: "elevator-cut-v2.mp4",
    models: {
      textAnalysisModel: "gpt-4.1-mini",
      visionModel: "qwen-vl-max",
      imageModel: "seedream-3.0",
      videoModel: "wanx2.1-video"
    },
    media: {
      title: "电梯停电",
      clipIndex: 2,
      durationSeconds: 30,
      width: 1920,
      height: 1080,
      hasAudio: true
    }
  },
  {
    id: "mock-republic-teahouse-confrontation",
    title: "民国茶楼正面对峙",
    status: "COMPLETED",
    createdAt: "2026-04-12T14:20:00+08:00",
    updatedAt: "2026-04-12T14:47:00+08:00",
    sourceFileName: "republic_ep07_teahouse.txt",
    aspectRatio: "21:9",
    minDurationSeconds: 36,
    maxDurationSeconds: 40,
    completedOutputCount: 2,
    taskSeed: 614338,
    effectRating: 8.6,
    description: "暖色室内光配合缓推镜头，更适合人物关系对峙和身份揭晓的情节。",
    previewUrl: null,
    downloadUrl: null,
    joinName: "teahouse-confrontation.mp4",
    models: {
      textAnalysisModel: "qwen-max",
      visionModel: "glm-4v",
      imageModel: "seedream-3.0",
      videoModel: "seedance-pro"
    },
    media: {
      title: "茶楼对峙",
      clipIndex: 4,
      durationSeconds: 38,
      width: 1920,
      height: 816,
      hasAudio: true
    }
  },
  {
    id: "mock-xianxia-cliff-farewell",
    title: "仙侠悬崖诀别",
    status: "COMPLETED",
    createdAt: "2026-04-15T18:42:00+08:00",
    updatedAt: "2026-04-15T19:08:00+08:00",
    sourceFileName: "xianxia_ep21_cliff_goodbye.txt",
    aspectRatio: "9:16",
    minDurationSeconds: 47,
    maxDurationSeconds: 52,
    completedOutputCount: 4,
    taskSeed: 127650,
    effectRating: 9.0,
    description: "高风速、长袍摆动和远景留白更明显，适合情绪拉满的诀别段落。",
    previewUrl: null,
    downloadUrl: null,
    joinName: "cliff-goodbye-master.mp4",
    models: {
      textAnalysisModel: "gpt-4.1-mini",
      visionModel: "qwen-vl-max",
      imageModel: "seedream-3.0",
      videoModel: "seedance-pro"
    },
    media: {
      title: "悬崖诀别",
      clipIndex: 5,
      durationSeconds: 49,
      width: 1080,
      height: 1920,
      hasAudio: true
    }
  },
  {
    id: "mock-livehouse-growth-montage",
    title: "Livehouse 成长蒙太奇",
    status: "COMPLETED",
    createdAt: "2026-04-17T11:08:00+08:00",
    updatedAt: "2026-04-17T11:31:00+08:00",
    sourceFileName: "music_growth_montage.txt",
    aspectRatio: "16:9",
    minDurationSeconds: 24,
    maxDurationSeconds: 27,
    completedOutputCount: 3,
    taskSeed: 445901,
    effectRating: 8.7,
    description: "鼓点切镜明显，适合练习、失败、上台三段式成长蒙太奇。",
    previewUrl: null,
    downloadUrl: null,
    joinName: "livehouse-growth-cut.mp4",
    models: {
      textAnalysisModel: "qwen-max",
      visionModel: "glm-4v",
      imageModel: "flux-kontext",
      videoModel: "wanx2.1-video"
    },
    media: {
      title: "成长蒙太奇",
      clipIndex: 3,
      durationSeconds: 26,
      width: 1920,
      height: 1080,
      hasAudio: true
    }
  },
  {
    id: "mock-corporate-comeback-boardroom",
    title: "职场复仇董事会翻盘",
    status: "COMPLETED",
    createdAt: "2026-04-18T09:36:00+08:00",
    updatedAt: "2026-04-18T10:02:00+08:00",
    sourceFileName: "boardroom_comeback_finale.txt",
    aspectRatio: "16:9",
    minDurationSeconds: 33,
    maxDurationSeconds: 37,
    completedOutputCount: 2,
    taskSeed: 778214,
    effectRating: 9.1,
    description: "会议室场景干净，人物站位清晰，适合权力关系翻转和结尾收束。",
    previewUrl: null,
    downloadUrl: null,
    joinName: "boardroom-comeback.mp4",
    models: {
      textAnalysisModel: "gpt-4.1-mini",
      visionModel: "qwen-vl-max",
      imageModel: "flux-kontext",
      videoModel: "seedance-pro"
    },
    media: {
      title: "董事会翻盘",
      clipIndex: 6,
      durationSeconds: 35,
      width: 1920,
      height: 1080,
      hasAudio: true
    }
  }
];

const showcasePlaceholderMetaMap: Record<string, ShowcasePlaceholderMeta> = {
  "mock-campus-romance-night-run": {
    layout: "left"
  },
  "mock-city-suspense-elevator": {
    layout: "right"
  },
  "mock-republic-teahouse-confrontation": {
    layout: "left"
  },
  "mock-xianxia-cliff-farewell": {
    layout: "center"
  },
  "mock-livehouse-growth-montage": {
    layout: "left"
  },
  "mock-corporate-comeback-boardroom": {
    layout: "right"
  }
};

const showcasePlaceholderStyleMap: Record<string, ShowcasePlaceholderStyle> = {
  "mock-campus-romance-night-run": {
    "--placeholder-glow": "radial-gradient(circle at 18% 22%, rgba(255, 196, 138, 0.32), transparent 30%), radial-gradient(circle at 82% 28%, rgba(118, 216, 255, 0.18), transparent 36%)",
    "--placeholder-beam": "linear-gradient(120deg, rgba(255,255,255,0) 12%, rgba(255,225,198,0.2) 42%, rgba(255,255,255,0) 68%)",
    "--placeholder-monitor": "linear-gradient(90deg, rgba(255, 166, 108, 0.18), rgba(112, 214, 255, 0.12))",
    "--placeholder-subject-left": "62%",
    "--placeholder-subject-bottom": "12px",
    "--placeholder-subject-width": "68px",
    "--placeholder-subject-height": "92px",
    "--placeholder-panel-left": "10%",
    "--placeholder-panel-width": "40%",
    "--placeholder-grid-opacity": "0.28"
  },
  "mock-city-suspense-elevator": {
    "--placeholder-glow": "radial-gradient(circle at 76% 14%, rgba(255, 86, 86, 0.24), transparent 26%), radial-gradient(circle at 22% 80%, rgba(81, 98, 136, 0.18), transparent 34%)",
    "--placeholder-beam": "linear-gradient(180deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.06) 30%, rgba(255,92,92,0.18) 56%, rgba(255,255,255,0) 88%)",
    "--placeholder-monitor": "linear-gradient(90deg, rgba(255, 86, 86, 0.22), rgba(255, 164, 164, 0.08))",
    "--placeholder-subject-left": "46%",
    "--placeholder-subject-bottom": "10px",
    "--placeholder-subject-width": "60px",
    "--placeholder-subject-height": "104px",
    "--placeholder-panel-left": "56%",
    "--placeholder-panel-width": "28%",
    "--placeholder-grid-opacity": "0.16"
  },
  "mock-republic-teahouse-confrontation": {
    "--placeholder-glow": "radial-gradient(circle at 24% 18%, rgba(255, 205, 143, 0.26), transparent 32%), radial-gradient(circle at 78% 72%, rgba(123, 66, 30, 0.18), transparent 34%)",
    "--placeholder-beam": "linear-gradient(105deg, rgba(255,255,255,0) 18%, rgba(255,216,160,0.18) 40%, rgba(255,255,255,0) 70%)",
    "--placeholder-monitor": "linear-gradient(90deg, rgba(255, 205, 143, 0.16), rgba(140, 74, 26, 0.14))",
    "--placeholder-subject-left": "58%",
    "--placeholder-subject-bottom": "10px",
    "--placeholder-subject-width": "74px",
    "--placeholder-subject-height": "98px",
    "--placeholder-panel-left": "12%",
    "--placeholder-panel-width": "42%",
    "--placeholder-grid-opacity": "0.24"
  },
  "mock-xianxia-cliff-farewell": {
    "--placeholder-glow": "radial-gradient(circle at 50% 10%, rgba(196, 228, 255, 0.22), transparent 24%), radial-gradient(circle at 52% 58%, rgba(160, 192, 255, 0.14), transparent 38%)",
    "--placeholder-beam": "linear-gradient(180deg, rgba(232,245,255,0.22) 0%, rgba(255,255,255,0) 42%, rgba(255,255,255,0) 100%)",
    "--placeholder-monitor": "linear-gradient(90deg, rgba(190, 220, 255, 0.12), rgba(130, 170, 255, 0.12))",
    "--placeholder-subject-left": "50%",
    "--placeholder-subject-bottom": "12px",
    "--placeholder-subject-width": "56px",
    "--placeholder-subject-height": "116px",
    "--placeholder-panel-left": "30%",
    "--placeholder-panel-width": "40%",
    "--placeholder-grid-opacity": "0.12"
  },
  "mock-livehouse-growth-montage": {
    "--placeholder-glow": "radial-gradient(circle at 18% 24%, rgba(255, 94, 166, 0.24), transparent 28%), radial-gradient(circle at 82% 22%, rgba(101, 220, 255, 0.18), transparent 34%)",
    "--placeholder-beam": "linear-gradient(90deg, rgba(255,255,255,0) 8%, rgba(255,94,166,0.16) 32%, rgba(101,220,255,0.18) 62%, rgba(255,255,255,0) 86%)",
    "--placeholder-monitor": "linear-gradient(90deg, rgba(255, 94, 166, 0.18), rgba(101, 220, 255, 0.14))",
    "--placeholder-subject-left": "18%",
    "--placeholder-subject-bottom": "10px",
    "--placeholder-subject-width": "78px",
    "--placeholder-subject-height": "98px",
    "--placeholder-panel-left": "56%",
    "--placeholder-panel-width": "24%",
    "--placeholder-grid-opacity": "0.22"
  },
  "mock-corporate-comeback-boardroom": {
    "--placeholder-glow": "radial-gradient(circle at 74% 16%, rgba(168, 214, 255, 0.18), transparent 24%), radial-gradient(circle at 22% 80%, rgba(122, 150, 190, 0.14), transparent 34%)",
    "--placeholder-beam": "linear-gradient(180deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0) 44%, rgba(255,255,255,0) 100%)",
    "--placeholder-monitor": "linear-gradient(90deg, rgba(164, 208, 255, 0.16), rgba(255, 255, 255, 0.08))",
    "--placeholder-subject-left": "64%",
    "--placeholder-subject-bottom": "11px",
    "--placeholder-subject-width": "66px",
    "--placeholder-subject-height": "94px",
    "--placeholder-panel-left": "12%",
    "--placeholder-panel-width": "46%",
    "--placeholder-grid-opacity": "0.18"
  }
};

function resolvePlaceholderMeta(item: TaskShowcaseItem, index: number): ShowcasePlaceholderMeta {
  const mappedMeta = showcasePlaceholderMetaMap[item.id];
  if (mappedMeta) {
    return mappedMeta;
  }
  return {
    layout: "left"
  };
}

function resolvePlaceholderStyle(item: TaskShowcaseItem): ShowcasePlaceholderStyle {
  return showcasePlaceholderStyleMap[item.id] ?? {
    "--placeholder-glow": "radial-gradient(circle at 20% 20%, rgba(174, 105, 255, 0.2), transparent 32%), radial-gradient(circle at 82% 20%, rgba(95, 216, 255, 0.16), transparent 34%)",
    "--placeholder-beam": "linear-gradient(120deg, rgba(255,255,255,0) 14%, rgba(255,255,255,0.14) 42%, rgba(255,255,255,0) 72%)",
    "--placeholder-monitor": "linear-gradient(90deg, rgba(174, 105, 255, 0.18), rgba(95, 216, 255, 0.12))",
    "--placeholder-subject-left": "58%",
    "--placeholder-subject-bottom": "10px",
    "--placeholder-subject-width": "68px",
    "--placeholder-subject-height": "96px",
    "--placeholder-panel-left": "12%",
    "--placeholder-panel-width": "42%",
    "--placeholder-grid-opacity": "0.22"
  };
}

const hasMockShowcase = computed(() => !showcaseItems.value.length);
const showcaseFeed = computed(() => hasMockShowcase.value ? mockShowcaseItems : showcaseItems.value);
const showcaseGeneratedAtLabel = computed(() => {
  if (showcaseGeneratedAt.value) {
    return showcaseGeneratedAt.value;
  }
  return "2026-04-18T10:02:00+08:00";
});
const showcaseTotalCompletedLabel = computed(() => {
  if (totalCompletedTasks.value > 0) {
    return totalCompletedTasks.value;
  }
  return 86;
});

const features = [
  {
    icon: "文生",
    title: "小说转视频",
    description: "把小说章节、脚本段落和创意梗概转换成可追踪的生成任务与镜头级提示词。",
    meta: "内容驱动"
  },
  {
    icon: "提示",
    title: "创意提示词 AI",
    description: "根据剧情自动扩写提示词、镜头语言和风格控制项，降低团队起步成本。",
    meta: "快速起稿"
  },
  {
    icon: "链路",
    title: "多模型编排",
    description: "把文本、图像和视频模型串成一条链路，并把编排逻辑开放给运营与管理员。",
    meta: "路由清晰"
  },
  {
    icon: "种子",
    title: "高分参数库",
    description: "沉淀高评分种子、常用参数和模板配置，让好结果可以被反复复用。",
    meta: "经验复用"
  }
];

const heroFrames = computed(() => {
  return showcaseFeed.value.slice(0, 4).map((item, index) => {
    const visual = resolveShowcaseVisual(item, index);
    return {
      ...item,
      ...visual,
      badge: selectShowcasePrimaryModel(item) || item.aspectRatio || "真实案例",
      placeholderMeta: resolvePlaceholderMeta(item, index),
      placeholderStyle: resolvePlaceholderStyle(item),
    };
  });
});

const showcaseModels = computed(() => collectShowcaseModelNodes(showcaseFeed.value));

const solutions = computed(() => {
  return showcaseFeed.value.slice(0, 3).map((item, index) => {
    const visual = resolveShowcaseVisual(item, index);
    return {
      ...item,
      ...visual,
      poster: item.aspectRatio || "真实案例",
      description: item.description || formatShowcaseTimeMeta(item),
      rating: formatShowcaseRatingLabel(item.effectRating),
      placeholderMeta: resolvePlaceholderMeta(item, index),
      placeholderStyle: resolvePlaceholderStyle(item),
    };
  });
});

const sideSamples = computed(() => {
  const sampledItems = showcaseFeed.value.length > 3
    ? showcaseFeed.value.slice(3, 5)
    : showcaseFeed.value.slice(0, 2);
  return sampledItems.map((item, index) => {
    const visual = resolveShowcaseVisual(item, index + 2);
    return {
      ...item,
      ...visual,
      score: formatShowcaseRatingLabel(item.effectRating),
      placeholderMeta: resolvePlaceholderMeta(item, index + 3),
      placeholderStyle: resolvePlaceholderStyle(item),
    };
  });
});

const showcaseStatusText = computed(() => {
  if (showcaseLoading.value) {
    return "正在同步真实案例...";
  }
  if (showcaseErrorMessage.value) {
    return hasMockShowcase.value
      ? "真实案例暂时不可用，当前展示精选示例案例"
      : showcaseErrorMessage.value;
  }
  if (!hasMockShowcase.value) {
    return `已同步 ${showcaseFeed.value.length} 条真实案例，累计完成 ${showcaseTotalCompletedLabel.value} 个任务`;
  }
  return `当前展示 ${showcaseFeed.value.length} 条精选示例案例，字段结构与真实任务一致`;
});

const showcaseDetailsJson = computed(() => {
  const ratings = showcaseFeed.value
    .map((item) => item.effectRating)
    .filter((item): item is number => typeof item === "number" && Number.isFinite(item));
  const aspectRatios = Array.from(new Set(showcaseFeed.value.map((item) => item.aspectRatio).filter(Boolean)));
  const generatedAt = showcaseGeneratedAtLabel.value
    ? new Date(showcaseGeneratedAtLabel.value).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })
    : "暂无";
  return JSON.stringify({
    案例数: showcaseFeed.value.length,
    已完成任务: showcaseTotalCompletedLabel.value,
    最高评分: ratings.length ? Math.max(...ratings).toFixed(1) : "暂无",
    常见画幅: aspectRatios.join(" / ") || "暂无",
    数据来源: hasMockShowcase.value ? "官网精选示例" : "真实任务",
    同步时间: generatedAt,
  }, null, 2);
});

const showcaseEndpointLabel = computed(() => {
  return showcaseFeed.value[0]?.downloadUrl
    || showcaseFeed.value[0]?.previewUrl
    || (hasMockShowcase.value ? "示例案例未附带媒体地址" : "暂无可公开预览地址");
});

const sideDetailsJson = computed(() => {
  const item = showcaseFeed.value[0];
  return JSON.stringify({
    标题: item?.title || "暂无",
    画幅: item?.aspectRatio || "暂无",
    时长: item ? formatShowcaseDuration(item) : "暂无",
    种子: typeof item?.taskSeed === "number" ? item.taskSeed : "未设置",
    主模型: item ? (selectShowcasePrimaryModel(item) || "暂无") : "暂无",
  }, null, 2);
});

const adminItems = [
  {
    title: "概览分析",
    description: "追踪提示词规模、任务完成率以及高质量结果的分布情况。"
  },
  {
    title: "批量任务",
    description: "一键提交、重试和管理整批内容生成任务，提高运营效率。"
  },
  {
    title: "系统连接",
    description: "集中配置供应商、接口地址与访问密钥，保持后台控制一致。"
  }
];

const footerGroups = [
  { title: "产品", items: ["功能概览", "模型能力", "联系我们"] },
  { title: "公司", items: ["品牌故事", "服务条款", "隐私政策", "合作咨询"] },
  { title: "资源", items: ["使用指南", "案例展示", "接口参考", "更新路线"] },
  { title: "社区", items: ["公众号", "视频号", "交流群", "GitHub"] }
];

function prefersReducedMotion() {
  return reducedMotionQuery?.matches ?? false;
}

function replaceHash(targetId: string) {
  if (typeof window === "undefined") {
    return;
  }

  const nextUrl = targetId === "top" ? window.location.pathname : `${window.location.pathname}#${targetId}`;
  window.history.replaceState(null, "", nextUrl);
}

function scrollToSection(targetId: string) {
  if (typeof document === "undefined") {
    return;
  }

  if (targetId === "top") {
    scrollRoot.value?.scrollTo({
      top: 0,
      behavior: prefersReducedMotion() ? "auto" : "smooth"
    });
    replaceHash(targetId);
    return;
  }

  const target = document.getElementById(targetId);
  if (!target) {
    return;
  }

  target.scrollIntoView({
    behavior: prefersReducedMotion() ? "auto" : "smooth",
    block: "start"
  });
  replaceHash(targetId);
}

function startTypingAnimation() {
  if (typingTimer) {
    window.clearInterval(typingTimer);
    typingTimer = null;
  }

  if (prefersReducedMotion()) {
    typedHeadline.value = fullHeadline;
    return;
  }

  typedHeadline.value = "";
  let currentIndex = 0;

  typingTimer = window.setInterval(() => {
    currentIndex += 1;
    typedHeadline.value = fullHeadline.slice(0, currentIndex);

    if (currentIndex >= fullHeadline.length && typingTimer) {
      window.clearInterval(typingTimer);
      typingTimer = null;
    }
  }, 90);
}

async function setupRevealAnimations() {
  await nextTick();

  const root = scrollRoot.value;
  if (!root) {
    return;
  }

  const revealNodes = Array.from(root.querySelectorAll<HTMLElement>(".reveal-on-scroll"));
  if (!revealNodes.length) {
    return;
  }

  if (prefersReducedMotion() || typeof IntersectionObserver === "undefined") {
    revealNodes.forEach((node) => node.classList.add("is-visible"));
    return;
  }

  revealObserver?.disconnect();
  revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealObserver?.unobserve(entry.target);
        }
      });
    },
    {
      root,
      threshold: 0.14,
      rootMargin: "0px 0px -10% 0px"
    }
  );

  revealNodes.forEach((node) => {
    if (node.classList.contains("is-visible")) {
      return;
    }
    revealObserver?.observe(node);
  });
}

onMounted(() => {
  reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  startTypingAnimation();
  void setupRevealAnimations();
  const hash = window.location.hash.replace(/^#/, "");
  if (hash) {
    setTimeout(() => {
      scrollToSection(hash);
    }, 0);
  }
});

onBeforeUnmount(() => {
  if (typingTimer) {
    window.clearInterval(typingTimer);
  }
  revealObserver?.disconnect();
});
</script>

<style scoped>
.official-site {
  position: relative;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  color: #2a2d3a;
  background:
    radial-gradient(circle at top left, rgba(184, 121, 255, 0.16), transparent 24%),
    radial-gradient(circle at top right, rgba(114, 228, 255, 0.14), transparent 22%),
    linear-gradient(180deg, #f5f4fb 0%, #f8f9fd 100%);
}

.official-site::before,
.official-site::after {
  content: "";
  position: fixed;
  inset: auto;
  pointer-events: none;
  z-index: 0;
}

.official-site::before {
  left: -140px;
  top: 180px;
  width: 520px;
  height: 520px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(184, 121, 255, 0.18), transparent 64%);
  filter: blur(40px);
  animation: drift-left 16s ease-in-out infinite;
}

.official-site::after {
  right: -120px;
  top: 360px;
  width: 500px;
  height: 500px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(114, 228, 255, 0.18), transparent 64%);
  filter: blur(40px);
  animation: drift-right 18s ease-in-out infinite;
}

.official-site__shell {
  position: relative;
  z-index: 1;
  width: min(1360px, calc(100% - 28px));
  margin: 0 auto;
  padding: 18px 0 28px;
}

.hero-section,
.content-section,
.side-card,
.site-footer {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(157, 138, 201, 0.18);
  background: rgba(255, 255, 255, 0.72);
  box-shadow:
    0 18px 60px rgba(104, 83, 134, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.76);
  backdrop-filter: blur(18px);
}

.hero-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 20px;
  border: 0;
  border-radius: 999px;
  font-size: 0.88rem;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    background 160ms ease;
}

.hero-button-primary {
  color: #fff;
  background: linear-gradient(135deg, #ae69ff, #6e59ff 42%, #59d6ff 100%);
  box-shadow: 0 12px 28px rgba(140, 105, 255, 0.28);
}

.hero-button:hover {
  transform: translateY(-1px);
}

.hero-section {
  margin-top: 18px;
  padding: 54px 56px 42px;
  border-radius: 34px;
}

.hero-section::before,
.hero-section::after,
.content-section::before,
.side-card::before {
  content: "";
  position: absolute;
  inset: auto;
  pointer-events: none;
}

.hero-section::before,
.content-section::before,
.side-card::before {
  left: -80px;
  bottom: -70px;
  width: 360px;
  height: 180px;
  background:
    radial-gradient(circle at 0 100%, rgba(184, 121, 255, 0.18), transparent 52%),
    repeating-radial-gradient(circle at 0 100%, rgba(174, 99, 255, 0.12) 0 1px, transparent 1px 9px);
  mask-image: linear-gradient(90deg, rgba(0, 0, 0, 0.75), transparent 88%);
  opacity: 0.7;
  animation: wave-shift 12s ease-in-out infinite;
}

.hero-section::after {
  right: -80px;
  top: 40px;
  width: 500px;
  height: 280px;
  background:
    radial-gradient(circle at 100% 50%, rgba(102, 220, 255, 0.14), transparent 54%),
    repeating-radial-gradient(circle at 100% 50%, rgba(120, 226, 255, 0.12) 0 1px, transparent 1px 10px);
  mask-image: linear-gradient(270deg, rgba(0, 0, 0, 0.75), transparent 84%);
  opacity: 0.75;
  animation: wave-shift 14s ease-in-out infinite reverse;
}

.hero-section__copy {
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
  text-align: center;
}

.hero-section__eyebrow,
.section-heading p,
.section-heading__eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #8a57e7;
}

.hero-section__title,
.section-heading h2,
.admin-card h2 {
  margin: 10px 0 0;
  font-family: "Plus Jakarta Sans", "Sora", "PingFang SC", sans-serif;
  letter-spacing: -0.03em;
  color: #2a2d3a;
}

.hero-section__title {
  display: inline-flex;
  align-items: flex-end;
  justify-content: center;
  gap: 6px;
  min-height: 2.1em;
  max-width: 13ch;
  font-size: clamp(3rem, 6vw, 4.9rem);
  line-height: 0.98;
}

.hero-section__slogan {
  margin: 14px 0 0;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: #5a6072;
}

.hero-section__title-text {
  white-space: pre-line;
  background: linear-gradient(135deg, #8d4fff 0%, #5fd8ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-section__caret {
  width: 0.08em;
  height: 0.9em;
  margin-bottom: 0.08em;
  border-radius: 999px;
  background: #7b67ff;
  animation: caret-blink 1s steps(1) infinite;
}

.hero-section__description {
  max-width: 860px;
  margin: 18px 0 0;
  font-size: 1rem;
  line-height: 1.8;
  color: #535868;
}

.hero-section__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 14px;
  margin-top: 28px;
}

.hero-button-secondary {
  color: #2a2d3a;
  background: rgba(255, 255, 255, 0.86);
  box-shadow:
    0 12px 24px rgba(85, 90, 120, 0.08),
    inset 0 0 0 1px rgba(157, 147, 196, 0.16);
}

.hero-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
  margin-top: 34px;
}

.hero-strip__status {
  margin: 18px 0 0;
  font-size: 0.88rem;
  color: #6c7284;
}

.hero-strip__frame {
  padding: 8px;
  border: 1px solid rgba(157, 138, 201, 0.16);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow:
    0 14px 28px rgba(96, 100, 131, 0.08),
    inset 0 0 0 1px rgba(153, 145, 197, 0.14);
}

.hero-strip__visual,
.solution-card__visual,
.side-media__visual {
  position: relative;
  min-height: 112px;
  border-radius: 16px;
  background: var(--frame-scene, var(--solution-scene, var(--sample-scene)));
  overflow: hidden;
  isolation: isolate;
}

.hero-strip__visual::before,
.solution-card__visual::before,
.side-media__visual::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 1;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(7, 10, 15, 0.26)),
    radial-gradient(circle at 50% 24%, rgba(255, 240, 220, 0.16), transparent 24%);
}

.showcase-placeholder {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 10px;
  padding: 14px;
  background:
    linear-gradient(180deg, rgba(6, 9, 15, 0.1), rgba(6, 9, 15, 0.42)),
    linear-gradient(120deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0));
}

.showcase-placeholder::before {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.06) 0, rgba(255, 255, 255, 0) 18%, rgba(255, 255, 255, 0) 82%, rgba(255, 255, 255, 0.04) 100%),
    repeating-linear-gradient(180deg, rgba(255, 255, 255, 0.05) 0 1px, transparent 1px 4px);
  opacity: 0.35;
  pointer-events: none;
}

.showcase-placeholder__scene {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  background: var(--placeholder-glow);
}

.showcase-placeholder__beam,
.showcase-placeholder__subject,
.showcase-placeholder__subject-shadow,
.showcase-placeholder__monitor {
  position: absolute;
}

.showcase-placeholder__beam {
  inset: 0;
  background: var(--placeholder-beam);
  mix-blend-mode: screen;
  opacity: 0.85;
}

.showcase-placeholder__subject-shadow {
  left: calc(var(--placeholder-subject-left) - 12px);
  bottom: calc(var(--placeholder-subject-bottom) - 6px);
  width: calc(var(--placeholder-subject-width) + 24px);
  height: 22px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(0, 0, 0, 0.28), transparent 68%);
  filter: blur(4px);
}

.showcase-placeholder__subject {
  left: calc(var(--placeholder-subject-left) - (var(--placeholder-subject-width) / 2));
  bottom: var(--placeholder-subject-bottom);
  width: var(--placeholder-subject-width);
  height: var(--placeholder-subject-height);
  border-radius: 38px 38px 14px 14px;
  background:
    radial-gradient(circle at 50% 16%, rgba(255, 242, 230, 0.74), transparent 18%),
    linear-gradient(180deg, rgba(248, 228, 210, 0.88), rgba(92, 82, 78, 0.92));
  box-shadow:
    0 18px 28px rgba(0, 0, 0, 0.18),
    inset 0 -18px 18px rgba(44, 39, 37, 0.32);
}

.showcase-placeholder__subject::before {
  content: "";
  position: absolute;
  left: 50%;
  top: -14px;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  transform: translateX(-50%);
  background:
    radial-gradient(circle at 50% 32%, rgba(255, 241, 228, 0.92), rgba(229, 198, 170, 0.88));
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.16);
}

.showcase-placeholder__monitor {
  left: var(--placeholder-panel-left);
  bottom: 14px;
  width: var(--placeholder-panel-width);
  height: 32px;
  border-radius: 12px;
  background: var(--placeholder-monitor);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.08),
    0 8px 18px rgba(0, 0, 0, 0.12);
}

.showcase-placeholder__monitor::before,
.showcase-placeholder__monitor::after {
  content: "";
  position: absolute;
  left: 12px;
  right: 12px;
  height: 2px;
  border-radius: 999px;
  background: rgba(255, 255, 255, var(--placeholder-grid-opacity, 0.22));
}

.showcase-placeholder__monitor::before {
  top: 10px;
}

.showcase-placeholder__monitor::after {
  top: 18px;
}

.showcase-placeholder--left {
  text-align: left;
}

.showcase-placeholder--right {
  text-align: right;
}

.showcase-placeholder--center {
  text-align: center;
}

.showcase-placeholder-compact {
  justify-content: flex-end;
}

.showcase-placeholder-expanded {
  padding: 18px;
}

.showcase-media {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

.official-site__grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 18px;
  margin-top: 18px;
}

.official-site__main,
.official-site__side {
  display: grid;
  gap: 18px;
  align-content: start;
}

.content-section,
.side-card,
.site-footer {
  padding: 24px;
  border-radius: 30px;
}

.section-heading {
  text-align: center;
}

.section-heading h2 {
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  line-height: 1.08;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  align-items: stretch;
  margin-top: 20px;
}

.feature-card,
.side-json__card {
  position: relative;
  overflow: hidden;
  padding: 18px;
  border: 1px solid rgba(157, 138, 201, 0.16);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow:
    0 14px 30px rgba(99, 102, 138, 0.08),
    inset 0 0 0 1px rgba(157, 147, 196, 0.16);
}

.feature-card {
  display: flex;
  flex-direction: column;
  min-height: 248px;
}

.feature-card__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(182, 111, 255, 0.18), rgba(97, 223, 255, 0.18));
  color: #7a53dc;
  font-size: 0.74rem;
  font-weight: 800;
}

.feature-card h3,
.solution-card h3,
.site-footer__links h3,
.admin-card__meta h3 {
  margin: 14px 0 0;
  font-family: "Manrope", "Inter", "PingFang SC", sans-serif;
  font-size: 1.12rem;
  font-weight: 800;
  color: #2a2d3a;
}

.feature-card p,
.solution-card p,
.admin-card__meta p,
.site-footer__top p {
  margin: 10px 0 0;
  color: #535868;
  line-height: 1.7;
}

.feature-card__footer {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  margin-top: auto;
  padding-top: 16px;
}

.feature-card__footer span {
  font-size: 0.76rem;
  color: #7c8194;
  font-weight: 700;
}

.showcase-card {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) 240px;
  gap: 18px;
  align-items: center;
  margin-top: 22px;
}

.showcase-card__map {
  position: relative;
  min-height: 300px;
}

.showcase-card__map::before {
  content: "";
  position: absolute;
  left: 26%;
  top: 28%;
  width: 48%;
  height: 44%;
  border: 2px solid rgba(112, 214, 255, 0.36);
  border-radius: 50%;
  filter: blur(0.2px);
  animation: slow-spin 20s linear infinite;
}

.showcase-card__map::after {
  content: "";
  position: absolute;
  left: 32%;
  top: 12%;
  width: 34%;
  height: 68%;
  border: 2px solid rgba(172, 122, 255, 0.3);
  border-radius: 50%;
  animation: slow-spin 26s linear infinite reverse;
}

.showcase-node {
  position: absolute;
  display: grid;
  justify-items: center;
  gap: 4px;
  width: 122px;
  padding: 12px 10px;
  border: 1px solid rgba(157, 138, 201, 0.16);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  box-shadow:
    0 14px 28px rgba(109, 115, 147, 0.1),
    inset 0 0 0 1px rgba(157, 147, 196, 0.16);
  text-align: center;
}

.showcase-node:nth-child(1) {
  left: 4%;
  top: 34%;
}

.showcase-node:nth-child(2) {
  left: 28%;
  top: 6%;
}

.showcase-node:nth-child(3) {
  right: 20%;
  top: 8%;
}

.showcase-node:nth-child(4) {
  left: 26%;
  bottom: 10%;
}

.showcase-node:nth-child(5) {
  right: 18%;
  bottom: 8%;
}

.showcase-node__badge {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: 50%;
  font-size: 1rem;
  font-weight: 900;
  color: #232838;
}

.showcase-node strong {
  font-size: 0.9rem;
}

.showcase-node span {
  font-size: 0.78rem;
  color: #777c8f;
}

.showcase-node-openai .showcase-node__badge {
  background: linear-gradient(135deg, rgba(204, 127, 255, 0.3), rgba(255, 255, 255, 0.94));
  box-shadow: 0 0 0 8px rgba(184, 121, 255, 0.12);
}

.showcase-node-vision .showcase-node__badge {
  background: linear-gradient(135deg, rgba(101, 220, 255, 0.3), rgba(255, 255, 255, 0.94));
  box-shadow: 0 0 0 8px rgba(101, 220, 255, 0.12);
}

.showcase-node-microsoft .showcase-node__badge {
  background: linear-gradient(135deg, rgba(255, 211, 110, 0.34), rgba(255, 255, 255, 0.94));
  box-shadow: 0 0 0 8px rgba(106, 164, 255, 0.12);
}

.showcase-node-frame .showcase-node__badge {
  background: linear-gradient(135deg, rgba(168, 118, 255, 0.26), rgba(255, 255, 255, 0.94));
  box-shadow: 0 0 0 8px rgba(168, 118, 255, 0.12);
}

.showcase-node-sora .showcase-node__badge {
  background: linear-gradient(135deg, rgba(125, 233, 255, 0.26), rgba(255, 255, 255, 0.94));
  box-shadow: 0 0 0 8px rgba(125, 233, 255, 0.12);
}

.showcase-card__details {
  padding: 18px;
  border: 1px solid rgba(157, 138, 201, 0.16);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow:
    0 14px 30px rgba(99, 102, 138, 0.08),
    inset 0 0 0 1px rgba(157, 147, 196, 0.16);
}

.showcase-card__details p,
.side-json__card p {
  margin: 0;
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #808599;
}

.showcase-card__details pre,
.side-json__card pre {
  margin: 12px 0 0;
  padding: 16px;
  border-radius: 18px;
  background: rgba(244, 245, 251, 0.88);
  color: #4f5466;
  font-size: 0.76rem;
  line-height: 1.7;
  overflow: auto;
}

.showcase-card__endpoint,
.side-json__card code {
  display: block;
  margin-top: 14px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(244, 245, 251, 0.88);
  color: #474d60;
  font-size: 0.76rem;
  word-break: break-all;
}

.showcase-card__endpoint span {
  display: block;
  margin-bottom: 8px;
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #808599;
}

.solution-list {
  display: grid;
  gap: 14px;
  margin-top: 20px;
}

.solution-card {
  display: grid;
  grid-template-columns: 250px minmax(0, 1fr);
  gap: 18px;
  padding: 12px;
  border: 1px solid rgba(157, 138, 201, 0.16);
  border-radius: 26px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow:
    0 14px 30px rgba(99, 102, 138, 0.08),
    inset 0 0 0 1px rgba(157, 147, 196, 0.16);
}

.solution-card__visual {
  min-height: 150px;
}

.solution-card__body {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.solution-card__rating {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.solution-card__rating span {
  font-size: 0.78rem;
  font-weight: 700;
  color: #818598;
}

.solution-card__rating strong {
  color: #d7a933;
  letter-spacing: 0.08em;
}

.side-card-showcase {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(190px, 0.95fr);
  gap: 14px;
}

.side-media {
  display: grid;
  gap: 12px;
}

.side-media__frame {
  overflow: hidden;
  padding: 10px;
  border: 1px solid rgba(157, 138, 201, 0.16);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow:
    0 14px 30px rgba(99, 102, 138, 0.08),
    inset 0 0 0 1px rgba(157, 147, 196, 0.16);
}

.side-media__visual {
  min-height: 116px;
}

.side-media__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
  color: #444b5d;
  font-size: 0.82rem;
  font-weight: 700;
}

.side-media__meta strong {
  color: #d7a933;
  letter-spacing: 0.08em;
}

.side-json {
  display: grid;
  gap: 12px;
}

.admin-card__content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: 20px;
  align-items: center;
}

.admin-preview {
  display: flex;
  justify-content: center;
}

.admin-preview__screen {
  position: relative;
  width: 100%;
  min-height: 170px;
  border-radius: 22px;
  background:
    linear-gradient(180deg, rgba(253, 254, 255, 0.96), rgba(241, 244, 250, 0.94)),
    #fff;
  box-shadow:
    0 18px 40px rgba(103, 97, 143, 0.16),
    inset 0 0 0 1px rgba(157, 147, 196, 0.16);
}

.admin-preview__screen::before {
  content: "";
  position: absolute;
  left: 16px;
  top: 16px;
  width: 90px;
  height: 10px;
  border-radius: 999px;
  background: #e4e6f0;
  box-shadow:
    0 20px 0 #eef0f7,
    0 40px 0 #eef0f7,
    0 60px 0 #eef0f7;
}

.admin-preview__bar,
.admin-preview__bar-short,
.admin-preview__chart {
  position: absolute;
  right: 16px;
  left: 132px;
  height: 18px;
  border-radius: 10px;
  background: linear-gradient(90deg, rgba(176, 105, 255, 0.22), rgba(89, 214, 255, 0.24));
}

.admin-preview__bar {
  top: 24px;
}

.admin-preview__bar-short {
  top: 56px;
  right: 72px;
}

.admin-preview__chart {
  top: 100px;
  bottom: 18px;
  height: auto;
  background:
    linear-gradient(180deg, rgba(176, 105, 255, 0.14), rgba(89, 214, 255, 0.08)),
    linear-gradient(90deg, transparent 0 10%, rgba(170, 178, 206, 0.16) 10% 11%, transparent 11% 24%, rgba(170, 178, 206, 0.16) 24% 25%, transparent 25% 38%, rgba(170, 178, 206, 0.16) 38% 39%, transparent 39% 52%, rgba(170, 178, 206, 0.16) 52% 53%, transparent 53%);
}

.admin-card__meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
  margin-top: 24px;
}

.site-footer {
  background:
    radial-gradient(circle at top right, rgba(95, 216, 255, 0.12), transparent 28%),
    radial-gradient(circle at bottom left, rgba(174, 105, 255, 0.14), transparent 30%),
    rgba(255, 255, 255, 0.78);
  color: #2a2d3a;
}

.site-footer__top,
.site-footer__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.site-footer__top strong {
  font-family: "Plus Jakarta Sans", "Sora", "PingFang SC", sans-serif;
  font-size: 1.4rem;
}

.site-footer__logo {
  width: 70px;
  height: 70px;
  filter: drop-shadow(0 12px 24px rgba(112, 96, 255, 0.14));
  animation: footer-pulse 4s ease-in-out infinite;
}

.site-footer__links {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 18px;
  margin-top: 28px;
}

.site-footer__links h3 {
  color: #2a2d3a;
  font-size: 0.92rem;
}

.site-footer__links a {
  display: block;
  margin-top: 10px;
  color: #666d80;
  font-size: 0.84rem;
}

.site-footer__bottom {
  margin-top: 28px;
  padding-top: 18px;
  border-top: 1px solid rgba(157, 138, 201, 0.14);
  color: #81879a;
  font-size: 0.78rem;
}

.reveal-on-scroll {
  opacity: 0;
  transform: translateY(28px) scale(0.985);
  transition:
    opacity 0.7s cubic-bezier(0.2, 0.8, 0.2, 1),
    transform 0.7s cubic-bezier(0.2, 0.8, 0.2, 1);
  transition-delay: var(--reveal-delay, 0ms);
  will-change: opacity, transform;
}

.reveal-on-scroll.is-visible {
  opacity: 1;
  transform: translateY(0) scale(1);
}

.reveal-on-scroll.is-visible.floating-panel {
  animation: float-up 7s ease-in-out infinite;
  animation-delay: var(--float-delay, 0s);
}

@keyframes caret-blink {

  0%,
  49% {
    opacity: 1;
  }

  50%,
  100% {
    opacity: 0;
  }
}

@keyframes float-up {

  0%,
  100% {
    transform: translateY(0);
  }

  50% {
    transform: translateY(-8px);
  }
}

@keyframes drift-left {

  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }

  50% {
    transform: translate3d(24px, -18px, 0);
  }
}

@keyframes drift-right {

  0%,
  100% {
    transform: translate3d(0, 0, 0);
  }

  50% {
    transform: translate3d(-20px, 22px, 0);
  }
}

@keyframes slow-spin {
  from {
    transform: rotate(0deg);
  }

  to {
    transform: rotate(360deg);
  }
}

@keyframes wave-shift {

  0%,
  100% {
    transform: translateX(0) translateY(0);
  }

  50% {
    transform: translateX(14px) translateY(-6px);
  }
}

@keyframes footer-pulse {

  0%,
  100% {
    transform: scale(1);
    opacity: 0.92;
  }

  50% {
    transform: scale(1.06);
    opacity: 1;
  }
}

@media (max-width: 1200px) {
  .feature-grid,
  .admin-card__meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .side-card-showcase,
  .admin-card__content,
  .showcase-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .hero-section {
    padding: 36px 20px 24px;
  }

  .hero-strip,
  .feature-grid,
  .site-footer__links,
  .admin-card__meta {
    grid-template-columns: 1fr;
  }

  .solution-card {
    grid-template-columns: 1fr;
  }

  .showcase-card__map {
    min-height: 500px;
  }

  .showcase-placeholder__headline,
  .showcase-placeholder__subline {
    max-width: 100%;
  }

  .showcase-node:nth-child(1) {
    left: 50%;
    top: 2%;
    transform: translateX(-50%);
  }

  .showcase-node:nth-child(2) {
    left: 10%;
    top: 28%;
  }

  .showcase-node:nth-child(3) {
    right: 10%;
    top: 28%;
  }

  .showcase-node:nth-child(4) {
    left: 10%;
    bottom: 14%;
  }

  .showcase-node:nth-child(5) {
    right: 10%;
    bottom: 14%;
  }

  .showcase-card__map::before {
    left: 14%;
    top: 22%;
    width: 72%;
    height: 48%;
  }

  .showcase-card__map::after {
    left: 26%;
    top: 12%;
    width: 48%;
    height: 68%;
  }
}

@media (max-width: 640px) {
  .official-site__shell {
    width: min(100%, calc(100% - 16px));
    padding-top: 8px;
  }

  .content-section,
  .side-card,
  .site-footer {
    padding: 18px;
  }

  .hero-section {
    border-radius: 26px;
  }

  .hero-section__title {
    max-width: 100%;
    min-height: 2.5em;
    font-size: clamp(2.5rem, 12vw, 3.4rem);
  }

  .showcase-placeholder,
  .showcase-placeholder-expanded {
    padding: 12px;
  }

  .showcase-placeholder__topline {
    flex-wrap: wrap;
  }

  .showcase-placeholder__headline {
    max-width: 100%;
  }

  .hero-button {
    width: 100%;
  }

  .site-footer__top,
  .site-footer__bottom {
    flex-direction: column;
    align-items: flex-start;
  }

}

@media (prefers-reduced-motion: reduce) {

  .official-site::before,
  .official-site::after,
  .hero-section::before,
  .hero-section::after,
  .showcase-card__map::before,
  .showcase-card__map::after,
  .site-footer__logo,
  .floating-panel,
  .hero-section__caret {
    animation: none !important;
  }

  .reveal-on-scroll {
    opacity: 1;
    transform: none;
    transition: none;
  }
}
</style>
