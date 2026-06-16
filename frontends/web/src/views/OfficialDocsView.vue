<template>
  <main ref="scrollRoot" class="docs-site">
    <MarketingTopbar active-page="docs" />

    <section class="docs-hero">
      <p>Documentation</p>
      <h1>部署、配置、开始生成。</h1>
      <div class="docs-hero__actions">
        <a class="button button-primary" href="#quick-start" @click.prevent="scrollToSection('quick-start')">快速开始</a>
        <a class="button button-secondary" href="https://github.com/imi4u36d/JianDou" target="_blank" rel="noreferrer">GitHub</a>
      </div>
    </section>

    <div class="docs-layout">
      <aside class="docs-sidebar">
        <nav aria-label="文档目录">
          <a
            v-for="item in docSections"
            :key="item.id"
            :href="`#${item.id}`"
            :class="{ 'is-active': activeSectionId === item.id }"
            @click.prevent="scrollToSection(item.id)"
          >
            <span>{{ item.index }}</span>
            {{ item.title }}
          </a>
        </nav>
      </aside>

      <article class="docs-content">
        <section id="overview" data-doc-section class="docs-section">
          <p class="section-kicker">Overview</p>
          <h2>开源免费的 AI 短剧工作流。</h2>
          <div class="value-grid">
            <article v-for="item in values" :key="item.title">
              <span>{{ item.badge }}</span>
              <strong>{{ item.title }}</strong>
              <p>{{ item.text }}</p>
            </article>
          </div>
        </section>

        <section id="quick-start" data-doc-section class="docs-section">
          <p class="section-kicker">Quick start</p>
          <h2>三步启动。</h2>
          <ol class="step-list">
            <li>复制环境变量。</li>
            <li>填入模型密钥。</li>
            <li>启动开发环境。</li>
          </ol>
          <pre class="code-block"><code>cp .env.dev.example .env.dev

cat &gt; config/model/providers.secrets.yml &lt;&lt;'EOF'
model:
  providers:
    deepseek:
      api_key: "你的 DeepSeek Key"
    seedream:
      api_key: "你的 Seedream Key"
    seedance:
      api_key: "你的 Seedance Key"
EOF

npm run compose:dev</code></pre>
          <div class="endpoint-grid">
            <article>
              <span>Web</span>
              <strong>http://127.0.0.1</strong>
            </article>
            <article>
              <span>Admin</span>
              <strong>http://127.0.0.1:5174</strong>
            </article>
            <article>
              <span>API</span>
              <strong>/api/v3/health</strong>
            </article>
          </div>
        </section>

        <section id="configuration" data-doc-section class="docs-section">
          <p class="section-kicker">Configuration</p>
          <h2>只改必要配置。</h2>
          <div class="config-list">
            <article v-for="item in configItems" :key="item.path">
              <code>{{ item.path }}</code>
              <p>{{ item.description }}</p>
            </article>
          </div>
          <pre class="code-block"><code>config/
  model/
    models.yml
    providers/
    providers.secrets.yml
  prompts/
    script.yml</code></pre>
        </section>

        <section id="workflow" data-doc-section class="docs-section">
          <p class="section-kicker">Workflow</p>
          <h2>从文本到成片。</h2>
          <div class="workflow-line">
            <article v-for="item in workflowItems" :key="item.title">
              <span>{{ item.index }}</span>
              <strong>{{ item.title }}</strong>
              <p>{{ item.text }}</p>
            </article>
          </div>
        </section>

        <section id="operations" data-doc-section class="docs-section">
          <p class="section-kicker">Operations</p>
          <h2>失败要能定位，结果要能复用。</h2>
          <div class="ops-grid">
            <article v-for="item in operations" :key="item.title">
              <strong>{{ item.title }}</strong>
              <span>{{ item.text }}</span>
            </article>
          </div>
        </section>

        <section id="faq" data-doc-section class="docs-section">
          <p class="section-kicker">FAQ</p>
          <h2>常见问题。</h2>
          <div class="faq-list">
            <article v-for="item in faqs" :key="item.question">
              <h3>{{ item.question }}</h3>
              <p>{{ item.answer }}</p>
            </article>
          </div>
        </section>
      </article>
    </div>
  </main>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import MarketingTopbar from "@/components/marketing/MarketingTopbar.vue";

const scrollRoot = ref<HTMLElement | null>(null);
const activeSectionId = ref("overview");
let sectionObserver: IntersectionObserver | null = null;
let reducedMotionQuery: MediaQueryList | null = null;

const docSections = [
  { id: "overview", index: "01", title: "概览" },
  { id: "quick-start", index: "02", title: "快速开始" },
  { id: "configuration", index: "03", title: "配置" },
  { id: "workflow", index: "04", title: "工作流" },
  { id: "operations", index: "05", title: "运维" },
  { id: "faq", index: "06", title: "FAQ" },
];

const values = [
  { badge: "Open", title: "开源", text: "代码和配置都可审计。" },
  { badge: "Free", title: "免费", text: "本地部署即可开始。" },
  { badge: "Fast", title: "高效", text: "阶段化生成和重试。" },
  { badge: "Stable", title: "一致", text: "角色、关键帧和 Seed 贯穿链路。" },
];

const configItems = [
  { path: ".env.dev", description: "开发环境变量。" },
  { path: "providers.secrets.yml", description: "模型 API Key。" },
  { path: "models.yml", description: "模型目录和能力。" },
  { path: "script.yml", description: "脚本与分镜提示词。" },
];

const workflowItems = [
  { index: "01", title: "文本", text: "上传 TXT 或粘贴正文。" },
  { index: "02", title: "分镜", text: "生成可编辑镜头脚本。" },
  { index: "03", title: "关键帧", text: "锁定首尾帧和角色锚点。" },
  { index: "04", title: "视频", text: "生成片段并合成结果。" },
];

const operations = [
  { title: "任务状态", text: "查看阶段、进度和耗时。" },
  { title: "错误原因", text: "定位到模型调用或工作流阶段。" },
  { title: "参数复用", text: "沉淀高分 Seed 和模型组合。" },
  { title: "后台管理", text: "管理用户、邀请码和运行配置。" },
];

const faqs = [
  { question: "缺少 api_key？", answer: "检查 provider 名称和 providers.secrets.yml。" },
  { question: "页面能开但任务失败？", answer: "先看 API 日志和 /api/v3/health。" },
  { question: "应该用 Docker 还是本地？", answer: "完整链路用 Docker，只改页面用本地。" },
  { question: "默认管理员在哪？", answer: "看 .env.dev 里的 bootstrap admin 配置。" },
];

function prefersReducedMotion() {
  return reducedMotionQuery?.matches ?? false;
}

function replaceHash(id: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.history.replaceState(null, "", `${window.location.pathname}#${id}`);
}

function scrollToSection(id: string, updateHash = true) {
  const target = document.getElementById(id);
  if (!target) {
    return;
  }
  target.scrollIntoView({
    behavior: prefersReducedMotion() ? "auto" : "smooth",
    block: "start",
  });
  activeSectionId.value = id;
  if (updateHash) {
    replaceHash(id);
  }
}

async function setupSectionObserver() {
  await nextTick();
  const root = scrollRoot.value;
  if (!root || prefersReducedMotion() || typeof IntersectionObserver === "undefined") {
    return;
  }
  const sections = Array.from(root.querySelectorAll<HTMLElement>("[data-doc-section]"));
  sectionObserver?.disconnect();
  sectionObserver = new IntersectionObserver(
    (entries) => {
      const nextSection = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio)[0]
        ?.target.getAttribute("id");
      if (nextSection) {
        activeSectionId.value = nextSection;
      }
    },
    { root, threshold: [0.24, 0.48], rootMargin: "-12% 0px -58% 0px" }
  );
  sections.forEach((section) => sectionObserver?.observe(section));
}

onMounted(async () => {
  reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  await setupSectionObserver();
  const hash = window.location.hash.replace(/^#/, "");
  if (hash) {
    setTimeout(() => scrollToSection(hash, false), 0);
  }
});

onBeforeUnmount(() => {
  sectionObserver?.disconnect();
});
</script>

<style scoped>
.docs-site {
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 16px max(18px, calc((100vw - 1180px) / 2)) 44px;
  color: #f6f3ea;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent 24%),
    radial-gradient(circle at 18% 10%, rgba(218, 176, 82, 0.14), transparent 22%),
    radial-gradient(circle at 84% 14%, rgba(42, 181, 164, 0.12), transparent 24%),
    #08090b;
}

.docs-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  padding: 96px 0 64px;
}

.docs-hero p,
.section-kicker {
  margin: 0;
  color: #c8b27a;
  font-size: 0.76rem;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.docs-hero h1,
.docs-section h2 {
  margin: 14px 0 0;
  max-width: 760px;
  color: #fffaf0;
  font-family: inherit;
  font-size: clamp(2.8rem, 6vw, 5.6rem);
  font-weight: 820;
  line-height: 0.98;
  letter-spacing: 0;
  overflow-wrap: anywhere;
}

.docs-hero__actions {
  display: flex;
  gap: 12px;
  flex: 0 0 auto;
}

.button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 18px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 8px;
  font-size: 0.92rem;
  font-weight: 800;
}

.button-primary {
  color: #11120f;
  background: #f2d37a;
  border-color: #f2d37a;
}

.button-secondary {
  color: #f7f0df;
  background: rgba(255, 255, 255, 0.06);
}

.docs-layout {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 28px;
  align-items: start;
}

.docs-sidebar {
  position: sticky;
  top: 96px;
}

.docs-sidebar nav {
  display: grid;
  gap: 6px;
  padding: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
}

.docs-sidebar a {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 0 10px;
  border-radius: 8px;
  color: #aaa69b;
  font-weight: 800;
}

.docs-sidebar a span {
  color: #6d6960;
  font-size: 0.72rem;
}

.docs-sidebar a.is-active {
  color: #fff8e7;
  background: rgba(242, 211, 122, 0.12);
}

.docs-sidebar a.is-active span {
  color: #f2d37a;
}

.docs-content {
  display: grid;
  gap: 18px;
}

.docs-section {
  scroll-margin-top: 94px;
  padding: 28px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.075), rgba(255, 255, 255, 0.035));
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.22);
}

.docs-section h2 {
  max-width: 680px;
  font-size: clamp(2rem, 4vw, 3.6rem);
}

.value-grid,
.endpoint-grid,
.workflow-line,
.ops-grid,
.faq-list {
  display: grid;
  gap: 12px;
  margin-top: 24px;
}

.value-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.endpoint-grid,
.workflow-line,
.ops-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.workflow-line,
.ops-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.value-grid article,
.endpoint-grid article,
.workflow-line article,
.ops-grid article,
.faq-list article,
.config-list article {
  min-height: 112px;
  padding: 18px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.045);
}

.value-grid span,
.endpoint-grid span,
.workflow-line span {
  color: #d6bd78;
  font-size: 0.74rem;
  font-weight: 900;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.value-grid strong,
.endpoint-grid strong,
.workflow-line strong,
.ops-grid strong,
.faq-list h3 {
  display: block;
  margin-top: 12px;
  color: #fff8e7;
  font-size: 1.05rem;
}

.value-grid p,
.workflow-line p,
.faq-list p,
.config-list p,
.ops-grid span {
  margin: 8px 0 0;
  color: #aca89d;
  line-height: 1.65;
}

.step-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin: 24px 0 0;
  padding: 0;
  list-style: none;
  counter-reset: steps;
}

.step-list li {
  counter-increment: steps;
  padding: 18px;
  border-radius: 12px;
  background: rgba(242, 211, 122, 0.1);
  color: #fff8e7;
  font-weight: 800;
}

.step-list li::before {
  content: counter(steps, decimal-leading-zero);
  display: block;
  margin-bottom: 18px;
  color: #f2d37a;
  font-size: 0.74rem;
}

.code-block {
  margin: 18px 0 0;
  padding: 18px;
  overflow: auto;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  background: rgba(0, 0, 0, 0.34);
  color: #e4ddce;
  font-size: 0.84rem;
  line-height: 1.7;
}

.config-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 24px;
}

.config-list code {
  color: #f2d37a;
  font-weight: 900;
}

@media (max-width: 980px) {
  .docs-hero,
  .docs-layout {
    display: grid;
  }

  .docs-layout,
  .value-grid,
  .endpoint-grid,
  .workflow-line,
  .ops-grid,
  .step-list,
  .config-list {
    grid-template-columns: 1fr;
  }

  .docs-sidebar {
    position: static;
  }

  .docs-sidebar nav {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .docs-site {
    padding-inline: 10px;
  }

  .docs-hero {
    padding: 48px 0 34px;
  }

  .docs-hero h1 {
    font-size: clamp(2.8rem, 15vw, 4.2rem);
  }

  .docs-section h2 {
    font-size: clamp(2rem, 11vw, 3rem);
  }

  .docs-hero__actions,
  .docs-sidebar nav {
    grid-template-columns: 1fr;
  }

  .docs-section {
    padding: 20px;
  }

  .button {
    width: 100%;
  }
}
</style>
