<template>
  <main ref="scrollRoot" class="official-site" id="top" :style="themeStyle">
    <header class="site-nav">
      <a class="site-brand" href="#top" @click.prevent="scrollToSection('top')">
        <img alt="JianDou Logo" class="site-brand__mark" src="/brand/jiandou-mark.svg" />
        <strong>JianDou</strong>
      </a>

      <nav class="site-nav__links" aria-label="官网导航">
        <a v-for="item in navItems" :key="item.label" :class="{ 'is-active': activeNav === item.label }"
          :href="`#${item.target}`" @click.prevent="handleNavClick(item)">
          {{ item.label }}
        </a>
      </nav>

      <button class="site-nav__demo" type="button" @click="startWorkflow">
        <span>立即开始</span>
        <kbd>⌘K</kbd>
      </button>
    </header>

    <section class="hero-section reveal-on-scroll is-visible">
      <div class="hero-section__copy">
        <p class="eyebrow">AI VIDEO WORKFLOW PLATFORM</p>
        <h1>从分镜到成片，一条工作流完成。</h1>
        <p class="hero-section__lead">
          不只是输入一句提示词生成视频。JianDou 把故事拆成镜头、角色、场景、运镜、配音与合成节点，让团队在同一个画布里完成 AI 视频制作。
        </p>
        <div class="hero-section__actions">
          <button class="button button-primary" type="button" @click="startWorkflow">开始创建工作流</button>
          <button class="button button-secondary" type="button" @click="openModal('video')">观看 90 秒演示</button>
        </div>
      </div>

      <div class="project-board" aria-label="JianDou 工作流项目预览">
        <div class="project-board__header">
          <span>PROJECT /</span>
          <input v-model="briefTitle" aria-label="项目标题" />
          <button type="button" @click="copyProjectId">{{ projectId }} · 复制</button>
        </div>
        <div class="project-board__stages">
          <article v-for="(stage, index) in heroStages" :key="stage.title" :style="indexStyle(index)">
            <span>0{{ index + 1 }}</span>
            <h3>{{ stage.title }}</h3>
            <p>{{ stage.description }}</p>
          </article>
        </div>
      </div>
    </section>

    <section class="workflow-strip reveal-on-scroll" id="workflow">
      <article v-for="(step, index) in workflowSteps" :key="step.title" :style="indexStyle(index)">
        <span>{{ step.code }}</span>
        <div>
          <h2>{{ step.title }}</h2>
          <p>{{ step.description }}</p>
        </div>
        <strong v-if="index < workflowSteps.length - 1">→</strong>
      </article>
    </section>

    <p class="workflow-note reveal-on-scroll">
      传统 AI 视频工具只解决"生成一个片段"；JianDou 解决的是完整创作链路的可控、可复用、可协作。
    </p>

    <section class="capability-section reveal-on-scroll" id="capabilities">
      <div class="section-copy">
        <p class="eyebrow">WHY WORKFLOW</p>
        <h2>让 AI 视频可控，而不是碰运气。</h2>
        <p>
          每个镜头都是节点：能锁定角色，能回滚版本，能替换配音，也能把同一套分镜复用到不同平台比例。
        </p>
      </div>

      <div class="capability-grid">
        <article v-for="(card, index) in capabilityCards" :key="card.title" :style="indexStyle(index)">
          <span>0{{ index + 1 }}</span>
          <h3>{{ card.title }}</h3>
          <p>{{ card.description }}</p>
        </article>
      </div>
    </section>

    <section class="creator-desk reveal-on-scroll">
      <div class="section-copy">
        <p class="eyebrow">CREATOR DESK</p>
        <h2>一个画布管理整条片子。</h2>
        <p>像剪辑软件一样组织 AI 生成，但每个轨道背后都有可编辑的提示词、参考资产和生成记录。</p>
      </div>

      <div class="desk-surface">
        <aside class="scene-list">
          <span>SCENES</span>
          <button v-for="scene in sceneCards" :key="scene.name" type="button" :class="{ 'is-active': scene.active }">
            <strong>{{ scene.code }} · {{ scene.name }}</strong>
            <small>{{ scene.meta }}</small>
          </button>
        </aside>

        <section class="shot-preview">
          <div class="shot-preview__media">
            <span>SHOT 02 / CAMERA PUSH</span>
            <h3>女主转身，霓虹从脸侧扫过</h3>
            <button type="button" @click="showToast('已加入单镜重生成队列')">重生成此镜</button>
          </div>
          <div class="track-stack">
            <span v-for="track in tracks" :key="track">{{ track }}</span>
          </div>
        </section>

        <aside class="prompt-node">
          <span>PROMPT NODE</span>
          <h3>镜头生成参数</h3>
          <ul>
            <li v-for="param in promptParams" :key="param">{{ param }}</li>
          </ul>
          <button type="button" @click="showToast('镜头参数已保存为团队模板')">保存为模板</button>
        </aside>
      </div>
    </section>

    <section class="case-section reveal-on-scroll" id="cases">
      <div class="case-section__copy">
        <p class="eyebrow">CASE / MCN 短剧团队</p>
        <h2>从 3 天出样，压到 7.5 小时。</h2>
        <p>
          上海团队「映桥内容」用同一套角色资产和分镜模板，为 6 个投放渠道生成不同节奏版本，剪辑师只审核异常镜头。
        </p>
      </div>

      <div class="metric-grid">
        <article v-for="metric in metrics" :key="metric.value">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <p>{{ metric.detail }}</p>
        </article>
      </div>
    </section>

    <section class="template-section reveal-on-scroll">
      <div class="section-copy">
        <p class="eyebrow">TEMPLATES</p>
        <h2>从模板开始，但不被模板困住。</h2>
        <p>
          短剧预告、带货口播、游戏宣发、企业培训都可以保存成工作流模板：改脚本、换角色、换比例，镜头结构仍然保留。
        </p>
        <button class="button button-primary" type="button" @click="browseTemplates">浏览全部模板</button>
      </div>

      <div class="template-grid">
        <article v-for="template in templates" :key="template.title"
          :class="{ 'is-selected': selectedTemplate === template.title }" role="button" tabindex="0"
          @click="selectTemplate(template.title)" @keydown.enter.prevent="selectTemplate(template.title)">
          <h3>{{ template.title }}</h3>
          <p>{{ template.meta }}</p>
          <span>{{ template.tags }}</span>
        </article>
      </div>
    </section>

    <section class="empty-state reveal-on-scroll">
      <p class="eyebrow">EMPTY STATE</p>
      <h2>还没有生成失败的镜头</h2>
      <p>当某个镜头生成失败或审核未通过时，会在这里集中处理并支持单镜重抽。</p>
      <button type="button" @click="showToast('已打开失败镜头诊断面板')">查看诊断面板</button>
    </section>

    <section class="faq-section reveal-on-scroll" aria-label="常见问题">
      <article v-for="(faq, index) in faqs" :key="faq.question">
        <button type="button" @click="faqOpen = faqOpen === index ? -1 : index">
          <span>{{ faq.question }}</span>
          <strong>{{ faqOpen === index ? "−" : "+" }}</strong>
        </button>
        <p v-if="faqOpen === index">{{ faq.answer }}</p>
      </article>
    </section>

    <section class="final-cta reveal-on-scroll">
      <h2>把下一条视频做成可复用流程。</h2>
      <p>适合短剧团队、MCN、品牌内容部门与广告创意工作室。</p>
      <button class="button button-primary" type="button" @click="openModal('apply')">申请内测名额</button>
    </section>

    <footer class="site-footer reveal-on-scroll">
      <strong>JianDou</strong>
      <span>AI video workflow platform.</span>
      <span>Copyright © 2026 JianDou</span>
    </footer>

    <Transition name="toast">
      <div v-if="toast" class="site-toast" role="status">{{ toast }}</div>
    </Transition>

    <Transition name="modal">
      <div v-if="modal" class="site-modal" role="dialog" aria-modal="true" @click.self="closeModal">
        <div class="site-modal__panel">
          <p class="eyebrow">JIANDOU</p>
          <h2>{{ modalTitle }}</h2>
          <p>{{ modalDescription }}</p>
          <div class="site-modal__actions">
            <button class="button button-primary" type="button" @click="confirmModal">确认</button>
            <button class="button button-secondary" type="button" @click="closeModal">关闭</button>
          </div>
        </div>
      </div>
    </Transition>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

type ModalType = "demo" | "video" | "apply" | "start";

interface NavItem {
  label: string;
  target: string;
}

const themeStyle = {
  "--accent-color": "oklch(0.68 0.20 310)",
  "--secondary-color": "oklch(0.76 0.16 190)",
  "--site-radius": "24px",
} as Record<string, string>;

const scrollRoot = ref<HTMLElement | null>(null);
const modal = ref<ModalType | null>(null);
const activeNav = ref("工作流");
const selectedTemplate = ref("短剧高能预告");
const toast = ref("");
const faqOpen = ref(0);
const briefTitle = ref("雨夜重逢短剧预告");
const projectId = "JD-VID-7429";
let toastTimer: number | null = null;
let revealObserver: IntersectionObserver | null = null;
let reducedMotionQuery: MediaQueryList | null = null;
const router = useRouter();

const navItems: NavItem[] = [
  { label: "工作流", target: "workflow" },
  { label: "能力", target: "capabilities" },
  { label: "案例", target: "cases" },
];

const heroStages = [
  { title: "分镜脚本", description: "自动拆解场次、景别和台词节奏" },
  { title: "角色一致性", description: "锁定人物设定、服装和表演情绪" },
  { title: "镜头生成", description: "逐镜头生成，可重抽单个片段" },
  { title: "视频合成", description: "配音、字幕、转场与成片导出" },
];

const workflowSteps = [
  { code: "01", title: "故事输入", description: "一句话、剧本或商品卖点" },
  { code: "02", title: "AI 拆分镜", description: "景别、台词、动作自动结构化" },
  { code: "03", title: "镜头生成", description: "逐镜头生成，失败只重抽单镜" },
  { code: "04", title: "素材编排", description: "角色、场景、音频全部入轨" },
  { code: "05", title: "一键合成", description: "字幕、配音、转场、封面导出" },
];

const capabilityCards = [
  { title: "结构化分镜", description: "自动识别场次、景别、镜头时长和台词，为生成模型提供更稳定的上下文。" },
  { title: "角色一致性", description: "把角色设定、参考图、服装和情绪绑定到项目资产，跨镜头保持统一。" },
  { title: "节点式重生成", description: "哪一镜不满意就只重抽哪一镜，不必整条视频推倒重来。" },
  { title: "合成与交付", description: "字幕、配音、音乐、转场、封面和多比例导出在同一时间线完成。" },
];

const sceneCards = [
  { code: "S01", name: "雨夜重逢", meta: "4 镜头 · 已锁定", active: false },
  { code: "S02", name: "天台对峙", meta: "6 镜头 · 42 秒 · 待审片", active: true },
  { code: "S03", name: "回忆闪回", meta: "4 镜头 · 已锁定", active: false },
  { code: "S04", name: "城市航拍", meta: "4 镜头 · 已锁定", active: false },
];

const tracks = [
  "视频轨 · 6 个镜头",
  "角色轨 · 林夏 / 陈砚",
  "音频轨 · 旁白 + 环境雨声",
  "字幕轨 · 14 条中文对白",
];

const promptParams = [
  "景别：中近景",
  "运动：缓慢推进",
  "情绪：克制、紧张",
  "比例：9:16 / 16:9",
];

const metrics = [
  { value: "30m", label: "首版样片生成时间", detail: "▼ 3000% vs 手动剪辑" },
  { value: "43", label: "单项目可复用镜头节点", detail: "▲ 2.4x 版本产能" },
  { value: "90%", label: "角色跨镜一致性通过率", detail: "基于 2025 Q1 内测项目" },
  { value: "12:4", label: "横竖屏同步导出比例", detail: "覆盖抖音、视频号、小红书" },
];

const templates = [
  { title: "短剧高能预告", meta: "18 镜头 · 竖屏优先", tags: "剧情转折 / 情绪爆点" },
  { title: "电商商品种草", meta: "9 镜头 · 多平台导出", tags: "卖点拆解 / 口播合成" },
  { title: "游戏版本 PV", meta: "14 镜头 · 强节奏", tags: "角色展示 / 技能特写" },
  { title: "知识课切片", meta: "7 镜头 · 字幕强化", tags: "讲师口播 / 图文补充" },
  { title: "城市文旅短片", meta: "11 镜头 · 航拍质感", tags: "地标 / 路线 / 情绪音乐" },
  { title: "品牌概念片", meta: "16 镜头 · 横屏主片", tags: "旁白 / 氛围 / 片尾标版" },
];

const faqs = [
  { question: "可以只重生成单个镜头吗？", answer: "可以。每个镜头都是独立节点，重生成不会影响已锁定的角色资产、配音和字幕轨道。" },
  { question: "团队成员如何协作？", answer: "编剧、导演、剪辑和投放同学可以在同一个项目中评论、锁定版本、审核镜头。" },
  { question: "支持哪些视频比例？", answer: "目前支持 16:9、9:16、1:1，并可在同一工作流里同步导出多个渠道版本。" },
];

const modalTitle = computed(() => {
  if (modal.value === "video") {
    return "90 秒产品演示";
  }
  if (modal.value === "apply") {
    return "申请内测名额";
  }
  if (modal.value === "start") {
    return "新建视频工作流";
  }
  return "预约产品演示";
});

const modalDescription = computed(() => {
  if (modal.value === "video") {
    return "演示会展示如何把一个短剧梗概拆成 8 个镜头，并在同一时间线完成配音、字幕和多比例导出。";
  }
  if (modal.value === "apply") {
    return "留下团队类型后，我们会优先邀请短剧、MCN、品牌内容团队进入内测。";
  }
  if (modal.value === "start") {
    return "空白工作流已准备好：你可以导入剧本、选择模板，或从一句创意开始拆分镜。";
  }
  return "我们会根据你的内容类型，演示分镜生成、角色一致性和视频合成工作流。";
});

function indexStyle(index: number) {
  return { "--item-index": `${index}` };
}

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
    scrollRoot.value?.scrollTo({ top: 0, behavior: prefersReducedMotion() ? "auto" : "smooth" });
    replaceHash(targetId);
    return;
  }
  const target = document.getElementById(targetId);
  if (!target) {
    return;
  }
  target.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
  replaceHash(targetId);
}

function handleNavClick(item: NavItem) {
  activeNav.value = item.label;
  scrollToSection(item.target);
  showToast(`已定位到${item.label}模块`);
}

function showToast(message: string) {
  toast.value = message;
  if (toastTimer) {
    window.clearTimeout(toastTimer);
  }
  toastTimer = window.setTimeout(() => {
    toast.value = "";
    toastTimer = null;
  }, 2400);
}

async function copyProjectId() {
  try {
    await navigator.clipboard?.writeText(projectId);
  } catch {
    // Clipboard access is optional in non-secure local contexts.
  }
  showToast("项目编号已复制");
}

function openModal(nextModal: ModalType) {
  modal.value = nextModal;
}

function closeModal() {
  modal.value = null;
}

function confirmModal() {
  showToast("已记录请求，我们会尽快联系");
  closeModal();
}

function startWorkflow() {
  router.push("/workspace");
}

function browseTemplates() {
  activeNav.value = "模板";
  showToast(`当前选中模板：${selectedTemplate.value}`);
}

function selectTemplate(templateTitle: string) {
  selectedTemplate.value = templateTitle;
  showToast(`已选择「${templateTitle}」工作流模板`);
}

function handleKeydown(event: KeyboardEvent) {
  const key = event.key.toLowerCase();
  if ((event.metaKey || event.ctrlKey) && key === "k") {
    event.preventDefault();
    startWorkflow();
    return;
  }
  if (event.key === "Escape" && modal.value) {
    closeModal();
  }
}

async function setupRevealAnimations() {
  await nextTick();
  const root = scrollRoot.value;
  if (!root) {
    return;
  }
  const revealNodes = Array.from(root.querySelectorAll<HTMLElement>(".reveal-on-scroll"));
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
    { root, threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
  );
  revealNodes.forEach((node) => {
    if (!node.classList.contains("is-visible")) {
      revealObserver?.observe(node);
    }
  });
}

onMounted(() => {
  reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  window.addEventListener("keydown", handleKeydown);
  void setupRevealAnimations();
  const hash = window.location.hash.replace(/^#/, "");
  if (hash) {
    setTimeout(() => scrollToSection(hash), 0);
  }
});

onBeforeUnmount(() => {
  revealObserver?.disconnect();
  window.removeEventListener("keydown", handleKeydown);
  if (toastTimer) {
    window.clearTimeout(toastTimer);
  }
});
</script>

<style scoped>
.official-site {
  min-height: 100vh;
  height: 100vh;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 18px max(18px, calc((100vw - 1180px) / 2)) 42px;
  color: oklch(0.965 0.012 286);
  background:
    linear-gradient(120deg, oklch(0.145 0.035 286), oklch(0.19 0.045 286) 54%, oklch(0.14 0.033 246)),
    linear-gradient(180deg, oklch(1 0 0 / 0.07), transparent 32%);
  background-blend-mode: normal;
  font-family: "DM Sans", "Inter", "PingFang SC", system-ui, sans-serif;
  scrollbar-color: oklch(0.68 0.20 310 / 0.5) transparent;
}

.official-site::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(oklch(1 0 0 / 0.055) 1px, transparent 1px),
    linear-gradient(90deg, oklch(1 0 0 / 0.04) 1px, transparent 1px);
  background-size: 64px 64px;
  mask-image: linear-gradient(180deg, oklch(0 0 0 / 0.78), transparent 74%);
}

.site-nav {
  position: sticky;
  top: 18px;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-height: 62px;
  padding: 10px 12px 10px 16px;
  border: 1px solid oklch(0.92 0.02 286 / 0.14);
  border-radius: 999px;
  background: oklch(0.235 0.045 286 / 0.78);
  box-shadow: 0 22px 80px oklch(0 0 0 / 0.3);
  backdrop-filter: blur(22px);
}

.site-brand,
.site-nav__links,
.site-nav__demo,
.hero-section__actions,
.project-board__header,
.workflow-strip article,
.shot-preview__media,
.site-footer,
.site-modal__actions {
  display: flex;
  align-items: center;
}

.site-brand {
  gap: 10px;
  min-width: max-content;
  color: oklch(0.965 0.012 286);
  text-decoration: none;
}

.site-brand__mark {
  width: 30px;
  height: 30px;
}

.site-brand strong {
  font-size: 1rem;
}

.site-nav__links {
  gap: 6px;
  padding: 4px;
  border-radius: 999px;
  background: oklch(0.15 0.03 286 / 0.32);
}

.site-nav__links a {
  min-height: 40px;
  padding: 0 14px;
  border-radius: 999px;
  color: oklch(0.78 0.028 286);
  font-size: 0.9rem;
  font-weight: 700;
  text-decoration: none;
  transition: color 160ms ease, background 160ms ease;
}

.site-nav__links a:hover,
.site-nav__links a.is-active {
  color: oklch(0.965 0.012 286);
  background: oklch(0.285 0.052 286 / 0.76);
}

.site-nav__demo,
.button,
.project-board__header button,
.shot-preview__media button,
.prompt-node button,
.empty-state button,
.faq-section button {
  border: 1px solid oklch(0.92 0.02 286 / 0.14);
  color: oklch(0.965 0.012 286);
  background: transparent;
  font-family: inherit;
  font-weight: 800;
  cursor: pointer;
  transition:
    transform 160ms cubic-bezier(.2, .8, .2, 1),
    border-color 160ms ease,
    background 160ms ease,
    box-shadow 160ms ease;
}

.site-nav__demo {
  gap: 9px;
  min-height: 42px;
  padding: 0 14px;
  border-radius: 999px;
  background: oklch(0.235 0.045 286 / 0.78);
}

.site-nav__demo kbd {
  min-width: 34px;
  padding: 3px 7px;
  border-radius: 999px;
  background: oklch(1 0 0 / 0.08);
  color: oklch(0.78 0.028 286);
  font-size: 0.72rem;
  font-family: "JetBrains Mono", ui-monospace, monospace;
}

.button:hover,
.site-nav__demo:hover,
.project-board__header button:hover,
.shot-preview__media button:hover,
.prompt-node button:hover,
.empty-state button:hover {
  transform: translateY(-1px);
  border-color: oklch(0.76 0.16 190 / 0.55);
}

.hero-section {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(460px, 1.1fr);
  gap: 42px;
  align-items: center;
  min-height: min(760px, calc(100vh - 112px));
  padding: 74px 0 56px;
}

.hero-section__copy {
  max-width: 650px;
}

.eyebrow {
  margin: 0;
  color: oklch(0.76 0.16 190);
  font-size: 0.78rem;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

.hero-section h1,
.section-copy h2,
.case-section__copy h2,
.empty-state h2,
.final-cta h2,
.site-modal__panel h2 {
  margin: 14px 0 0;
  color: oklch(0.965 0.012 286);
  font-family: "Fraunces", "Noto Serif SC", serif;
  font-weight: 900;
}

.hero-section h1 {
  max-width: 760px;
  font-size: 5.75rem;
  line-height: 1.02;
}

.hero-section__lead,
.section-copy p,
.case-section__copy p,
.workflow-note,
.empty-state p,
.final-cta p,
.site-modal__panel p {
  color: oklch(0.78 0.028 286);
  line-height: 1.9;
}

.hero-section__lead {
  max-width: 610px;
  margin: 25px 0 0;
  font-size: 1.08rem;
}

.hero-section__actions {
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 31px;
}

.button {
  justify-content: center;
  min-height: 48px;
  padding: 0 20px;
  border-radius: 999px;
  font-size: 0.94rem;
}

.button-primary {
  border-color: transparent;
  color: white;
  background: var(--accent-color);
  box-shadow: 0 18px 42px oklch(0.68 0.20 310 / 0.22);
}

.button-secondary {
  background: oklch(0.235 0.045 286 / 0.6);
}

.project-board,
.capability-grid article,
.desk-surface,
.metric-grid article,
.template-grid article,
.empty-state,
.faq-section article,
.site-modal__panel {
  border: 1px solid oklch(0.92 0.02 286 / 0.14);
  background:
    linear-gradient(180deg, oklch(1 0 0 / 0.09), oklch(1 0 0 / 0.035)),
    oklch(0.235 0.045 286 / 0.78);
  box-shadow: 0 24px 80px oklch(0 0 0 / 0.28);
  backdrop-filter: blur(18px);
}

.project-board {
  overflow: hidden;
  border-radius: var(--site-radius);
}

.project-board__header {
  gap: 12px;
  min-height: 60px;
  padding: 0 18px;
  border-bottom: 1px solid oklch(0.92 0.02 286 / 0.14);
  color: oklch(0.78 0.028 286);
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 0.78rem;
}

.project-board__header input {
  width: 150px;
  min-width: 0;
  border: 0;
  border-bottom: 1px dashed var(--secondary-color);
  color: oklch(0.965 0.012 286);
  background: transparent;
  font: inherit;
  outline: none;
}

.project-board__header button {
  margin-left: auto;
  padding: 8px 11px;
  border-radius: 999px;
  font-size: 0.76rem;
}

.project-board__stages {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: oklch(0.92 0.02 286 / 0.12);
}

.project-board__stages article {
  min-height: 210px;
  padding: 22px;
  background:
    linear-gradient(140deg, oklch(0.31 0.06 286 / 0.8), oklch(0.22 0.045 286 / 0.95)),
    oklch(0.235 0.045 286);
}

.project-board__stages article:nth-child(2),
.project-board__stages article:nth-child(3) {
  background:
    linear-gradient(140deg, oklch(0.27 0.05 246 / 0.72), oklch(0.22 0.045 286 / 0.95)),
    oklch(0.235 0.045 286);
}

.project-board__stages span,
.capability-grid span,
.metric-grid span,
.template-grid span,
.workflow-strip span,
.prompt-node>span,
.scene-list>span,
.shot-preview__media>span {
  color: oklch(0.76 0.16 190);
  font-size: 0.75rem;
  font-weight: 900;
  letter-spacing: 0;
  text-transform: uppercase;
}

.project-board__stages h3,
.capability-grid h3,
.template-grid h3,
.prompt-node h3,
.shot-preview h3 {
  margin: 48px 0 0;
  color: oklch(0.965 0.012 286);
  font-size: 1.16rem;
}

.project-board__stages p,
.capability-grid p,
.metric-grid p,
.template-grid p,
.faq-section p,
.prompt-node li,
.scene-list small,
.track-stack span {
  color: oklch(0.78 0.028 286);
  line-height: 1.7;
}

.project-board__stages p {
  min-height: 54px;
  margin: 12px 0 0;
}

.workflow-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.workflow-strip article {
  position: relative;
  align-items: flex-start;
  gap: 14px;
  min-height: 168px;
  padding: 18px;
  border: 1px solid oklch(0.92 0.02 286 / 0.14);
  border-radius: 18px;
  background: oklch(0.235 0.045 286 / 0.62);
}

.workflow-strip h2 {
  margin: 0;
  color: oklch(0.965 0.012 286);
  font-size: 1.08rem;
}

.workflow-strip p {
  margin: 9px 0 0;
  color: oklch(0.78 0.028 286);
  line-height: 1.6;
}

.workflow-strip strong {
  position: absolute;
  right: 16px;
  bottom: 14px;
  color: var(--accent-color);
  font-size: 1.2rem;
}

.workflow-note {
  max-width: 880px;
  margin: 32px auto 0;
  text-align: center;
  font-size: 1.05rem;
}

.capability-section,
.creator-desk,
.case-section,
.template-section,
.empty-state,
.faq-section,
.final-cta,
.site-footer {
  margin-top: 96px;
}

.section-copy,
.case-section__copy {
  max-width: 760px;
}

.section-copy h2,
.case-section__copy h2,
.empty-state h2,
.final-cta h2,
.site-modal__panel h2 {
  font-size: 3.75rem;
  line-height: 1.05;
}

.section-copy p,
.case-section__copy p {
  margin: 18px 0 0;
  font-size: 1rem;
}

.capability-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 34px;
}

.capability-grid article {
  min-height: 300px;
  padding: 22px;
  border-radius: 18px;
}

.capability-grid h3 {
  margin-top: 92px;
}

.desk-surface {
  display: grid;
  grid-template-columns: minmax(180px, 0.72fr) minmax(360px, 1.45fr) minmax(230px, 0.83fr);
  gap: 14px;
  margin-top: 36px;
  padding: 16px;
  border-radius: var(--site-radius);
}

.scene-list,
.prompt-node,
.shot-preview {
  min-width: 0;
}

.scene-list {
  display: grid;
  align-content: start;
  gap: 10px;
}

.scene-list button {
  display: grid;
  gap: 6px;
  min-height: 76px;
  padding: 14px;
  border: 1px solid oklch(0.92 0.02 286 / 0.12);
  border-radius: 16px;
  color: inherit;
  background: oklch(1 0 0 / 0.05);
  text-align: left;
  cursor: default;
}

.scene-list button.is-active {
  border-color: oklch(0.76 0.16 190 / 0.55);
  background: oklch(0.76 0.16 190 / 0.1);
}

.scene-list strong {
  color: oklch(0.965 0.012 286);
  font-size: 0.95rem;
}

.shot-preview {
  display: grid;
  gap: 12px;
}

.shot-preview__media {
  position: relative;
  align-items: flex-end;
  min-height: 372px;
  overflow: hidden;
  padding: 22px;
  border-radius: 18px;
  background:
    linear-gradient(180deg, transparent 20%, oklch(0.09 0.03 286 / 0.78)),
    linear-gradient(135deg, oklch(0.42 0.1 310), oklch(0.2 0.08 220) 54%, oklch(0.56 0.16 190));
}

.shot-preview__media::before,
.shot-preview__media::after {
  content: "";
  position: absolute;
  background: oklch(0.96 0.02 80 / 0.86);
}

.shot-preview__media::before {
  left: 18%;
  bottom: 88px;
  width: 86px;
  height: 138px;
  border-radius: 44px 44px 18px 18px;
  box-shadow: 96px 16px 0 -18px oklch(0.82 0.06 52 / 0.65);
}

.shot-preview__media::after {
  right: 17%;
  top: 44px;
  width: 120px;
  height: 8px;
  transform: rotate(-16deg);
  box-shadow:
    -80px 58px 0 -1px oklch(0.76 0.16 190 / 0.5),
    -18px 118px 0 -2px oklch(0.68 0.2 310 / 0.52);
}

.shot-preview__media>span,
.shot-preview__media h3,
.shot-preview__media button {
  position: relative;
  z-index: 1;
}

.shot-preview__media h3 {
  max-width: 420px;
  margin: 10px 0 0;
  font-size: 1.42rem;
}

.shot-preview__media button {
  margin-left: auto;
  padding: 10px 13px;
  border-radius: 999px;
  background: oklch(0.235 0.045 286 / 0.78);
}

.track-stack {
  display: grid;
  gap: 8px;
}

.track-stack span {
  display: block;
  min-height: 38px;
  padding: 9px 12px;
  border-radius: 999px;
  background: oklch(1 0 0 / 0.06);
  font-size: 0.86rem;
}

.prompt-node {
  padding: 18px;
  border-radius: 18px;
  background: oklch(0.12 0.034 286 / 0.48);
}

.prompt-node h3 {
  margin-top: 12px;
}

.prompt-node ul {
  display: grid;
  gap: 10px;
  margin: 24px 0 0;
  padding: 0;
  list-style: none;
}

.prompt-node li {
  padding: 10px 12px;
  border-radius: 14px;
  background: oklch(1 0 0 / 0.06);
}

.prompt-node button {
  width: 100%;
  min-height: 44px;
  margin-top: 18px;
  border-radius: 14px;
  background: oklch(0.285 0.052 286 / 0.76);
}

.case-section {
  display: grid;
  grid-template-columns: minmax(0, 0.82fr) minmax(420px, 1.18fr);
  gap: 36px;
  align-items: end;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.metric-grid article {
  min-height: 178px;
  padding: 20px;
  border-radius: 18px;
}

.metric-grid strong {
  display: block;
  margin-top: 18px;
  color: oklch(0.965 0.012 286);
  font-family: "Fraunces", "Noto Serif SC", serif;
  font-size: 3.75rem;
  line-height: 0.95;
}

.metric-grid p {
  margin: 14px 0 0;
}

.template-section {
  display: grid;
  grid-template-columns: minmax(0, 0.78fr) minmax(480px, 1.22fr);
  gap: 34px;
  align-items: start;
}

.template-section .button {
  margin-top: 24px;
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.template-grid article {
  min-height: 138px;
  padding: 18px;
  border-radius: 18px;
  cursor: pointer;
}

.template-grid article:hover,
.template-grid article.is-selected {
  transform: translateY(-1px);
  border-color: var(--secondary-color);
  box-shadow:
    0 0 0 2px oklch(0.76 0.16 190 / 0.18),
    0 24px 80px oklch(0 0 0 / 0.28);
}

.template-grid h3 {
  margin: 0;
}

.template-grid p {
  margin: 12px 0 7px;
}

.empty-state {
  display: grid;
  justify-items: center;
  padding: 54px 22px;
  border-radius: var(--site-radius);
  text-align: center;
}

.empty-state h2 {
  font-size: 3.25rem;
}

.empty-state p {
  max-width: 580px;
  margin: 15px auto 0;
}

.empty-state button {
  min-height: 43px;
  margin-top: 22px;
  padding: 0 16px;
  border-radius: 999px;
  background: oklch(0.285 0.052 286 / 0.76);
}

.faq-section {
  display: grid;
  gap: 10px;
}

.faq-section article {
  overflow: hidden;
  border-radius: 18px;
}

.faq-section button {
  justify-content: space-between;
  width: 100%;
  min-height: 62px;
  padding: 0 18px;
  border: 0;
  text-align: left;
}

.faq-section button span {
  min-width: 0;
}

.faq-section button strong {
  color: var(--secondary-color);
  font-size: 1.4rem;
}

.faq-section p {
  margin: 0;
  padding: 0 18px 20px;
}

.final-cta {
  display: grid;
  justify-items: center;
  padding: 78px 22px;
  border: 1px solid oklch(0.92 0.02 286 / 0.14);
  border-radius: var(--site-radius);
  background:
    linear-gradient(135deg, oklch(0.68 0.20 310 / 0.2), oklch(0.76 0.16 190 / 0.11)),
    oklch(0.235 0.045 286 / 0.78);
  text-align: center;
}

.final-cta h2 {
  max-width: 780px;
  margin-top: 0;
}

.final-cta p {
  margin: 16px 0 0;
}

.final-cta .button {
  margin-top: 26px;
}

.site-footer {
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px;
  padding: 28px 0 8px;
  border-top: 1px solid oklch(0.92 0.02 286 / 0.14);
  color: oklch(0.78 0.028 286);
  font-size: 0.9rem;
}

.site-footer strong {
  color: oklch(0.965 0.012 286);
}

.site-toast {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 50;
  max-width: min(360px, calc(100vw - 32px));
  padding: 12px 16px;
  border: 1px solid oklch(0.92 0.02 286 / 0.14);
  border-radius: 999px;
  color: oklch(0.965 0.012 286);
  background: oklch(0.235 0.045 286 / 0.9);
  box-shadow: 0 18px 60px oklch(0 0 0 / 0.38);
  backdrop-filter: blur(18px);
}

.site-modal {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: 20px;
  background: oklch(0 0 0 / 0.58);
}

.site-modal__panel {
  width: min(520px, 100%);
  padding: 26px;
  border-radius: var(--site-radius);
}

.site-modal__panel h2 {
  font-size: 2.75rem;
}

.site-modal__panel p:not(.eyebrow) {
  margin: 16px 0 0;
}

.site-modal__actions {
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 24px;
}

.reveal-on-scroll {
  opacity: 0;
  transform: translateY(22px);
  transition:
    opacity 0.65s ease,
    transform 0.65s ease;
  transition-delay: calc(var(--item-index, 0) * 70ms);
}

.reveal-on-scroll.is-visible {
  opacity: 1;
  transform: translateY(0);
}

.toast-enter-active,
.toast-leave-active,
.modal-enter-active,
.modal-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(8px);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .site-modal__panel,
.modal-leave-to .site-modal__panel {
  transform: translateY(12px);
}

@media (max-width: 1080px) {

  .hero-section,
  .case-section,
  .template-section,
  .desk-surface {
    grid-template-columns: 1fr;
  }

  .hero-section {
    min-height: auto;
    padding-top: 56px;
  }

  .hero-section h1 {
    max-width: 780px;
    font-size: 4.85rem;
  }

  .section-copy h2,
  .case-section__copy h2,
  .empty-state h2,
  .final-cta h2,
  .site-modal__panel h2 {
    font-size: 3.25rem;
  }

  .workflow-strip,
  .capability-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .desk-surface {
    gap: 12px;
  }
}

@media (max-width: 760px) {
  .official-site {
    padding-inline: 10px;
  }

  .site-nav {
    display: grid;
    grid-template-columns: 1fr auto;
    border-radius: 20px;
  }

  .site-nav__links {
    grid-column: 1 / -1;
    order: 3;
    justify-content: stretch;
    overflow-x: auto;
  }

  .site-nav__links a {
    flex: 1;
    justify-content: center;
  }

  .site-nav__demo span {
    display: none;
  }

  .hero-section h1 {
    max-width: 360px;
    font-size: 3.58rem;
    line-height: 1.04;
  }

  .section-copy h2,
  .case-section__copy h2,
  .empty-state h2,
  .final-cta h2,
  .site-modal__panel h2 {
    font-size: 2.28rem;
  }

  .metric-grid strong {
    font-size: 3rem;
  }

  .project-board__header {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    min-height: auto;
    padding: 14px;
  }

  .project-board__header button {
    grid-column: 1 / -1;
    justify-self: start;
    margin-left: 0;
  }

  .project-board__stages,
  .workflow-strip,
  .capability-grid,
  .metric-grid,
  .template-grid {
    grid-template-columns: 1fr;
  }

  .workflow-strip article,
  .project-board__stages article,
  .capability-grid article {
    min-height: auto;
  }

  .project-board__stages h3,
  .capability-grid h3 {
    margin-top: 44px;
  }

  .shot-preview__media {
    min-height: 310px;
  }

  .site-modal__actions .button,
  .hero-section__actions .button,
  .final-cta .button {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {

  .reveal-on-scroll,
  .toast-enter-active,
  .toast-leave-active,
  .modal-enter-active,
  .modal-leave-active {
    transition: none;
  }

  .reveal-on-scroll {
    opacity: 1;
    transform: none;
  }
}
</style>
