<template>
  <section class="prompt-template-gallery" aria-label="提示词模板">
    <div class="prompt-template-gallery__head">
      <h2>灵感模板</h2>
      <span>{{ promptTemplates.length }} 种风格</span>
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
        <button type="button" class="jd-button jd-button--sm prompt-template-preview__apply" @click="applyTemplate(previewTemplate)">
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

interface PromptTemplate {
  id: string;
  title: string;
  tag: string;
  prompt: string;
  imageUrl: string;
}

const emit = defineEmits<{
  apply: [template: PromptTemplate];
}>();

const previewTemplate = ref<PromptTemplate | null>(null);

function templateImage(fileName: string) {
  return `/prompt-templates/${fileName}`;
}

const promptTemplates: PromptTemplate[] = [
  {
    id: "shojo-manga",
    title: "少女漫画风",
    tag: "大眼 / 网点 / 浪漫",
    imageUrl: templateImage("shojo-manga.webp"),
    prompt: "少女漫画风插画，[主体]，大而闪亮的眼睛，纤细干净线稿，柔和粉紫色调，花瓣和星光背景，细腻网点阴影，高光丰富，浪漫梦幻氛围，竖构图，精致封面感。",
  },
  {
    id: "cyberpunk",
    title: "赛博朋克风",
    tag: "霓虹 / 雨夜 / 高反差",
    imageUrl: templateImage("cyberpunk.webp"),
    prompt: "赛博朋克风格，[主体]，雨夜城市街头，霓虹招牌与蓝紫粉高反差光影，湿润地面反射，未来机械细节，烟雾和电路线缆，电影感低角度，锐利边缘光，高细节。",
  },
  {
    id: "guochao-ink",
    title: "国潮水墨风",
    tag: "留白 / 墨韵 / 东方",
    imageUrl: templateImage("guochao-ink.webp"),
    prompt: "国潮水墨插画，[主体]，宣纸肌理，浓淡墨晕染，大面积留白，金色细线点缀，东方纹样和云气，现代海报构图，克制高级色彩，传统与潮流融合。",
  },
  {
    id: "claymation",
    title: "黏土动画风",
    tag: "手作 / 软质 / 定格",
    imageUrl: templateImage("claymation.webp"),
    prompt: "黏土动画风格，[主体]，手捏黏土材质，圆润比例，轻微指纹和手作瑕疵，柔和棚拍灯光，微缩场景，定格动画质感，温暖可爱，浅景深，真实触感。",
  },
  {
    id: "blind-box-3d",
    title: "软萌 3D 盲盒风",
    tag: "Q版 / 软塑 / 潮玩",
    imageUrl: templateImage("blind-box-3d.webp"),
    prompt: "软萌 3D 盲盒潮玩风，[主体]，Q版大头小身比例，圆润软塑材质，干净棚拍背景，柔和环境光，精致玩具涂装，轻微磨砂质感，治愈可爱，商业级 3D 渲染。",
  },
  {
    id: "pixel-game",
    title: "像素游戏风",
    tag: "复古 / 方块 / 16-bit",
    imageUrl: templateImage("pixel-game.webp"),
    prompt: "复古像素游戏风，[主体]，16-bit pixel art，清晰方块边缘，有限调色板，等距视角，街机游戏氛围，细小高光点，低分辨率颗粒感，画面干净，角色和场景轮廓明确。",
  },
  {
    id: "watercolor-storybook",
    title: "水彩绘本风",
    tag: "纸感 / 透明 / 温柔",
    imageUrl: templateImage("watercolor-storybook.webp"),
    prompt: "水彩绘本风格，[主体]，透明水彩叠色，湿画法边缘，纸张纹理可见，低饱和温柔配色，手绘线条，轻盈留白，童话感构图，温暖自然光，适合插画书页面。",
  },
  {
    id: "y2k-sticker",
    title: "Y2K 闪光贴纸风",
    tag: "镭射 / 可爱 / 高光",
    imageUrl: templateImage("y2k-sticker.webp"),
    prompt: "Y2K 闪光贴纸风，[主体]，镭射渐变，高饱和粉蓝紫配色，果冻质感，粗白描边，星星爱心装饰，闪粉高光，贴纸切边，俏皮网络头像感，干净透明背景感。",
  },
  {
    id: "lofi-low-poly",
    title: "低多边形 3D 风",
    tag: "Lo-fi / 棱面 / 游戏",
    imageUrl: templateImage("lofi-low-poly.webp"),
    prompt: "低多边形 3D 风格，[主体]，low-poly 几何棱面，简化模型，块面材质，柔和单一主光，复古独立游戏画面，轻微颗粒，重点突出轮廓和故事感，不追求过度写实。",
  },
  {
    id: "anime-25d",
    title: "2.5D 动漫渲染",
    tag: "赛璐璐 / 3D / 角色",
    imageUrl: templateImage("anime-25d.webp"),
    prompt: "2.5D 动漫渲染风，[主体]，3D 体积结合赛璐璐上色，清晰黑色轮廓线，非真实感渲染，柔和渐变阴影，发丝和服装层次分明，干净背景，适合虚拟角色头像。",
  },
];

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

<style scoped>
.prompt-template-gallery {
  display: grid;
  gap: 12px;
  width: min(100%, 1180px);
  margin: 0 auto;
}

.prompt-template-gallery__head,
.prompt-template-card__meta {
  display: flex;
  align-items: center;
}

.prompt-template-gallery__head {
  justify-content: space-between;
  gap: 16px;
}

.prompt-template-gallery__head h2,
.prompt-template-preview__prompt h4 {
  margin: 0;
  letter-spacing: 0;
}

.prompt-template-gallery__head h2 {
  font-size: 1rem;
  font-weight: 800;
}

.prompt-template-gallery__head span {
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.prompt-template-gallery__rail {
  display: flex;
  gap: 10px;
  min-width: 0;
  overflow-x: auto;
  padding: 2px 2px 10px;
  scroll-snap-type: x proximity;
}

.prompt-template-gallery__rail::-webkit-scrollbar {
  height: 8px;
}

.prompt-template-gallery__rail::-webkit-scrollbar-thumb {
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.1);
}

.prompt-template-card {
  position: relative;
  flex: 0 0 auto;
  width: 132px;
  height: 178px;
  overflow: hidden;
  padding: 0;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #111827;
  color: #fff;
  cursor: pointer;
  scroll-snap-align: start;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.1);
}

.prompt-template-card img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 180ms ease;
}

.prompt-template-card:hover img {
  transform: scale(1.04);
}

.prompt-template-card__meta {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  padding: 36px 10px 10px;
  background: linear-gradient(180deg, transparent, rgba(0, 0, 0, 0.74));
}

.prompt-template-card__meta strong,
.prompt-template-card__meta small {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-template-card__meta strong {
  font-size: 0.8rem;
  font-weight: 850;
}

.prompt-template-card__meta small {
  color: rgba(255, 255, 255, 0.78);
  font-size: 0.72rem;
  font-weight: 750;
}

.prompt-template-preview__prompt button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 11px;
  border: 1px solid rgba(15, 23, 42, 0.1);
  border-radius: 8px;
  background: #fff;
  color: var(--text-strong);
  font-weight: 750;
  cursor: pointer;
}

.prompt-template-preview__apply {
  color: #0f766e !important;
}

.prompt-template-preview__prompt button {
  width: fit-content;
  border-color: rgba(20, 184, 166, 0.28);
  background: #0f766e;
  color: #fff;
}

.prompt-template-preview__body {
  display: grid;
  grid-template-columns: minmax(260px, 0.82fr) minmax(280px, 1fr);
  min-height: 0;
}

.prompt-template-preview__media {
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 0;
  background: transparent;
}

.prompt-template-preview__media img {
  display: block;
  width: 100%;
  height: auto;
  max-height: calc(86vh - 76px);
  background: transparent;
  object-fit: contain;
}

.prompt-template-preview__prompt {
  display: grid;
  align-content: start;
  gap: 14px;
  min-width: 0;
  overflow-y: auto;
  padding: 22px;
}

.prompt-template-preview__prompt h4 {
  font-size: 0.9rem;
  font-weight: 850;
}

.prompt-template-preview__prompt p {
  margin: 0;
  padding: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
  font-size: 0.94rem;
  font-weight: 600;
  line-height: 1.72;
  white-space: pre-wrap;
}

@media (max-width: 720px) {
  .prompt-template-card {
    width: 112px;
    height: 150px;
  }

  .prompt-template-preview__body {
    grid-template-columns: 1fr;
  }

  .prompt-template-preview__media {
    max-height: 42vh;
  }
}
</style>
