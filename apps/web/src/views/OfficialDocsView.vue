<template>
  <main ref="scrollRoot" class="docs-site">
    <div class="docs-site__shell">
      <MarketingTopbar active-page="docs" />

      <div class="docs-layout">
        <aside class="docs-sidebar">
          <div class="docs-sidebar__panel">
            <p class="docs-sidebar__eyebrow">Documentation</p>
            <h1 class="docs-sidebar__title">章节导航</h1>

            <nav class="docs-sidebar__groups" aria-label="章节目录">
              <section v-for="group in sectionGroups" :key="group.title" class="docs-sidebar__group">
                <p>{{ group.title }}</p>
                <a
                  v-for="item in group.items"
                  :key="item.id"
                  :href="`#${item.id}`"
                  class="docs-sidebar__link"
                  :class="{ 'docs-sidebar__link-active': activeSectionId === item.id }"
                  @click.prevent="scrollToSection(item.id)"
                >
                  {{ item.title }}
                </a>
              </section>
            </nav>
          </div>
        </aside>

        <section class="docs-content">
          <article class="docs-article">
            <section class="docs-overview-strip">
              <div>
                <p class="docs-section__eyebrow">Documentation</p>
                <h2>使用文档</h2>
              </div>
              <div class="docs-overview-strip__actions">
                <a class="docs-button docs-button-primary" href="#quick-start" @click.prevent="scrollToSection('quick-start')">快速开始</a>
                <a
                  class="docs-button docs-button-secondary"
                  href="https://github.com/imi4u36d/JianDou/blob/main/docs/USER_GUIDE.md"
                  target="_blank"
                  rel="noreferrer"
                >
                  仓库文档
                </a>
              </div>
            </section>

            <section id="overview" data-doc-section class="docs-article__section">
              <p class="docs-section__eyebrow">Introduction</p>
              <h2>项目概览</h2>
              <p class="docs-section__lead">
                JianDou 当前由三部分组成：用户前台、独立后台和基于 Spring Boot 3 的后端服务。典型工作流是先配置模型与环境，再创建生成任务，随后在任务中心查看进度、产物和复用参数。
              </p>

              <div class="docs-callout">
                <strong>你会在这份文档里拿到什么</strong>
                <p>最短启动路径、API Key 配置方式、Docker 与本地启动命令、首次登录入口、创建第一个任务的步骤，以及常见故障定位方向。</p>
              </div>

              <div class="docs-grid docs-grid--cards">
                <article class="docs-card">
                  <h3>适合谁看</h3>
                  <p>首次部署项目的开发者、需要试跑生成链路的运营、需要接手环境和模型配置的管理员。</p>
                </article>
                <article class="docs-card">
                  <h3>最推荐的运行方式</h3>
                  <p>优先使用 Docker Compose 开发环境。前台、后台、Spring API 和 MySQL 会一起起来，路径最短，变量最少。</p>
                </article>
                <article class="docs-card">
                  <h3>核心前置条件</h3>
                  <p>真实的模型 API Key、正确的 `.env.dev` 或 `.env.prod`、以及可访问的 MySQL / Docker 环境。</p>
                </article>
              </div>
            </section>

            <section id="quick-start" data-doc-section class="docs-article__section">
              <p class="docs-section__eyebrow">Quick Start</p>
              <h2>快速开始</h2>
              <p class="docs-section__lead">如果你只想尽快把官网和工作台跑起来，按下面四步走就够了。</p>

              <ol class="docs-steps">
                <li>复制环境变量模板，生成 `.env.dev`。</li>
                <li>在 `config/model/providers.secrets.yml` 填入真实 API Key。</li>
                <li>执行 `npm run compose:dev` 启动整套开发环境。</li>
                <li>打开前台、后台和健康检查地址确认服务已就绪。</li>
              </ol>

              <pre class="docs-code"><code>cp .env.dev.example .env.dev
cp .env.prod.example .env.prod

cat &gt; config/model/providers.secrets.yml &lt;&lt;'EOF'
model:
  providers:
    qwen:
      api_key: "你的阿里云 DashScope Key"
    seedream:
      api_key: "你的 Seedream Key"
    seedance:
      api_key: "你的 Seedance Key"
EOF

npm run compose:dev</code></pre>

              <div class="docs-grid docs-grid--compact">
                <article class="docs-mini-card">
                  <span>前台</span>
                  <strong>http://127.0.0.1</strong>
                </article>
                <article class="docs-mini-card">
                  <span>后台</span>
                  <strong>http://127.0.0.1:5174</strong>
                </article>
                <article class="docs-mini-card">
                  <span>健康检查</span>
                  <strong>http://127.0.0.1/api/v2/health</strong>
                </article>
              </div>
            </section>

            <section id="api-key" data-doc-section class="docs-article__section">
              <p class="docs-section__eyebrow">Configuration</p>
              <h2>配置模型 API Key</h2>
              <p class="docs-section__lead">
                模型配置统一位于 `config/model/`。真实密钥最推荐写入 `config/model/providers.secrets.yml`，这样可以和公开的基础配置分离。
              </p>

              <div class="docs-grid docs-grid--cards">
                <article class="docs-card">
                  <h3>模型定义</h3>
                  <p>`config/model/models.yml` 定义当前站点可选的文本、视觉、图像和视频模型。</p>
                </article>
                <article class="docs-card">
                  <h3>Provider 基础配置</h3>
                  <p>`config/model/providers/*.yml` 定义各厂商 `base_url`、默认超时与能力参数，通常不需要改。</p>
                </article>
                <article class="docs-card">
                  <h3>真实密钥</h3>
                  <p>`config/model/providers.secrets.yml` 用于覆盖 `api_key`，也是后台配置落盘时优先写入的目标文件。</p>
                </article>
              </div>

              <pre class="docs-code"><code>model:
  providers:
    qwen:
      api_key: "你的阿里云 DashScope Key"
    ark:
      api_key: "你的火山引擎 Ark Key"
    seedream:
      api_key: "你的 Seedream Key"
    seedance:
      api_key: "你的 Seedance Key"
    openai:
      api_key: "你的 OpenAI Key"</code></pre>

              <div class="docs-note docs-note--warning">
                <strong>注意</strong>
                <p>如果你只启用部分模型，只填对应 provider 的 `api_key` 即可。未配置密钥的 provider 在实际调用时会失败。</p>
              </div>

              <ul class="docs-list">
                <li>`qwen`：文本模型与视觉理解模型。</li>
                <li>`seedream`：图像生成 / 关键帧相关模型。</li>
                <li>`seedance`：视频生成模型。</li>
                <li>`ark`：火山引擎通用接入。</li>
                <li>`openai`：OpenAI 兼容文本模型接入。</li>
              </ul>
            </section>

            <section id="run-project" data-doc-section class="docs-article__section">
              <p class="docs-section__eyebrow">Run</p>
              <h2>启动项目</h2>
              <p class="docs-section__lead">
                项目同时支持 Docker Compose 一键启动和本地开发模式启动。前者适合首次体验和标准化环境，后者适合单独调试前端或后端。
              </p>

              <h3>方式一：Docker Compose 开发环境</h3>
              <pre class="docs-code"><code>cp .env.dev.example .env.dev
npm run compose:dev

# 常用命令
npm run compose:dev:logs
npm run compose:dev:ps
npm run compose:dev:down</code></pre>

              <h3>方式二：Docker Compose 生产编排</h3>
              <pre class="docs-code"><code>cp .env.prod.example .env.prod
npm run compose:prod

# 常用命令
npm run compose:prod:logs
npm run compose:prod:ps
npm run compose:prod:down</code></pre>

              <h3>方式三：本地开发模式</h3>
              <pre class="docs-code"><code># 安装前端依赖
npm --prefix apps/web install
npm --prefix apps/admin install

# 启动 Web + Spring Boot API
npm run dev

# 单独启动后台
npm run admin:dev

# 单独启动后端
npm run api:dev</code></pre>

              <div class="docs-note">
                <strong>建议</strong>
                <p>如果你只改官网或文档页面，本地模式启动 `apps/web` 就足够；如果你要验证生成链路和登录流程，直接跑 Docker 开发环境更稳。</p>
              </div>
            </section>

            <section id="login-check" data-doc-section class="docs-article__section">
              <p class="docs-section__eyebrow">Verify</p>
              <h2>首次登录与环境检查</h2>
              <p class="docs-section__lead">
                环境起来后，先不要急着直接创建任务。先确认用户入口、后台入口和 API 健康检查都是通的，再核对默认管理员账号来源。
              </p>

              <div class="docs-grid docs-grid--cards">
                <article class="docs-card">
                  <h3>用户前台</h3>
                  <p>默认访问 `http://127.0.0.1`，用于查看官网、进入工作台、创建任务和管理结果。</p>
                </article>
                <article class="docs-card">
                  <h3>后台管理端</h3>
                  <p>默认访问 `http://127.0.0.1:5174`，用于配置系统、管理任务、用户和邀请码。</p>
                </article>
                <article class="docs-card">
                  <h3>API 健康检查</h3>
                  <p>访问 `http://127.0.0.1/api/v2/health`，确认后端已完成启动和依赖连接。</p>
                </article>
              </div>

              <ul class="docs-list">
                <li>默认管理员用户名来自 `JIANDOU_AUTH_BOOTSTRAP_INITIAL_ADMIN_USERNAME`。</li>
                <li>默认管理员密码来自 `.env.dev` 或 `.env.prod` 中的 `JIANDOU_AUTH_BOOTSTRAP_INITIAL_ADMIN_PASSWORD`。</li>
                <li>若使用本地模式，请同时确认前端代理目标仍指向 `http://127.0.0.1:8000`。</li>
              </ul>

              <div class="docs-note docs-note--danger">
                <strong>排查优先级</strong>
                <p>如果前台能开但接口报错，优先看 `api` 日志；如果接口通但页面空白，优先看 `web` 或 `admin` 构建日志。</p>
              </div>
            </section>

            <section id="first-task" data-doc-section class="docs-article__section">
              <p class="docs-section__eyebrow">Workflow</p>
              <h2>创建第一个生成任务</h2>
              <p class="docs-section__lead">
                当前核心业务入口是生成页。你可以在一个页面内完成模型选择、输出控制、TXT 上传、提示词生成和任务提交。
              </p>

              <ol class="docs-steps">
                <li>进入 `/generate` 或 `/tasks/new`。</li>
                <li>填写任务标题，选择画幅比例。</li>
                <li>依次选择文本、视觉、关键帧、视频四段模型。</li>
                <li>配置清晰度、输出数量、时长区间和 Seed。</li>
                <li>上传 TXT 文件或直接粘贴正文。</li>
                <li>点击“AI 生成提示词”补全全局创意提示词。</li>
                <li>提交任务后，在右侧即时进度卡查看阶段、状态和视频预览。</li>
              </ol>

              <div class="docs-grid docs-grid--cards">
                <article class="docs-card">
                  <h3>输入方式</h3>
                  <p>支持 TXT 上传，也支持直接在文本框中粘贴正文；若标题为空，系统会尝试用文件名回填任务标题。</p>
                </article>
                <article class="docs-card">
                  <h3>模型链路</h3>
                  <p>四段模型需要显式选择，不会默认帮你预选。这样可以避免错误地把任务打到未准备好的模型上。</p>
                </article>
                <article class="docs-card">
                  <h3>实时反馈</h3>
                  <p>提交后页面会轮询真实任务进度，显示阶段名称、百分比、Trace 数量、耗时和最新更新时间。</p>
                </article>
              </div>
            </section>

            <section id="task-management" data-doc-section class="docs-article__section">
              <p class="docs-section__eyebrow">Operations</p>
              <h2>任务管理与参数复用</h2>
              <p class="docs-section__lead">
                提交只是开始。JianDou 的任务页负责筛选、巡检、重试、暂停、继续、终止和删除，同时还能把高分 Seed 再喂回新任务。
              </p>

              <ul class="docs-list">
                <li>任务列表支持筛选、状态查看、详情展开和运维动作。</li>
                <li>任务详情会展示阶段进度、Trace、产物、模型信息和评分入口。</li>
                <li>高分 Seed 模块会自动汇总有评分且带 Seed 的历史任务，允许一键回填。</li>
                <li>阶段工作流页可查看版本、产物和复用关系，适合对比方案与沉淀流程。</li>
              </ul>

              <div class="docs-callout docs-callout--soft">
                <strong>为什么要复用 Seed</strong>
                <p>对短剧内容生产来说，Seed 不只是一个随机参数，它常常对应某种稳定的镜头气质。把高分 Seed 沉淀下来，比每次从零试错更有价值。</p>
              </div>
            </section>

            <section id="settings-models" data-doc-section class="docs-article__section">
              <p class="docs-section__eyebrow">Settings</p>
              <h2>设置与模型配置</h2>
              <p class="docs-section__lead">
                设置页和配置目录共同决定了站点的运行方式。页面层负责用户可见的选择项，配置文件负责系统级模型和环境能力。
              </p>

              <div class="docs-grid docs-grid--cards">
                <article class="docs-card">
                  <h3>设置页</h3>
                  <p>用于查看和调整工作台级别的模型、厂商分类和开发者模式选项。</p>
                </article>
                <article class="docs-card">
                  <h3>模型目录</h3>
                  <p>`config/model/models.yml` 控制站点当前能看到哪些模型、属于哪个 provider、支持哪些能力。</p>
                </article>
                <article class="docs-card">
                  <h3>运行时配置目录</h3>
                  <p>容器默认把 `./config` 挂载到 `/app/config`。如果你需要外置配置，可以通过 `JIANDOU_CONFIG_DIR` 指向新的配置目录。</p>
                </article>
              </div>

              <pre class="docs-code"><code>config/
  app/
    runtime.yml
    infrastructure.yml
  model/
    models.yml
    defaults.yml
    providers/
      aliyun.yml
      volcengine.yml
      openai.yml
    providers.secrets.yml
  prompts/
    core.yml
    planner.yml
    script.yml</code></pre>
            </section>

            <section id="faq" data-doc-section class="docs-article__section">
              <p class="docs-section__eyebrow">FAQ</p>
              <h2>常见问题</h2>

              <div class="docs-faq">
                <article class="docs-faq__item">
                  <h3>接口提示缺少 `api_key` 怎么办？</h3>
                  <p>先检查 `config/model/providers.secrets.yml` 是否存在，再确认对应 provider 键名是否和模型配置里的 `provider` 一致。</p>
                </article>
                <article class="docs-faq__item">
                  <h3>页面能打开，但提交任务失败怎么办？</h3>
                  <p>优先看后端日志和 `/api/v2/health`。大多数情况下是 MySQL 未连接、模型 Key 缺失，或调用方 `base_url` / `api_key` 不完整。</p>
                </article>
                <article class="docs-faq__item">
                  <h3>本地模式和 Docker 模式应该选哪个？</h3>
                  <p>想快速验证完整流程，选 Docker；只改前端页面或调试单个服务，选本地模式。</p>
                </article>
                <article class="docs-faq__item">
                  <h3>后台默认账号从哪里来？</h3>
                  <p>看 `.env.dev` 或 `.env.prod` 中的 `JIANDOU_AUTH_BOOTSTRAP_INITIAL_ADMIN_USERNAME` 和 `JIANDOU_AUTH_BOOTSTRAP_INITIAL_ADMIN_PASSWORD`。</p>
                </article>
              </div>
            </section>
          </article>
        </section>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import MarketingTopbar from "@/components/marketing/MarketingTopbar.vue";

type DocsItem = {
  id: string;
  title: string;
};

type DocsGroup = {
  title: string;
  items: DocsItem[];
};

const scrollRoot = ref<HTMLElement | null>(null);
const activeSectionId = ref("overview");

const sectionGroups: DocsGroup[] = [
  {
    title: "开始",
    items: [
      { id: "overview", title: "项目概览" },
      { id: "quick-start", title: "快速开始" }
    ]
  },
  {
    title: "部署与配置",
    items: [
      { id: "api-key", title: "配置 API Key" },
      { id: "run-project", title: "启动项目" },
      { id: "login-check", title: "首次登录与环境检查" }
    ]
  },
  {
    title: "使用流程",
    items: [
      { id: "first-task", title: "创建第一个任务" },
      { id: "task-management", title: "任务管理与参数复用" },
      { id: "settings-models", title: "设置与模型配置" }
    ]
  },
  {
    title: "附录",
    items: [
      { id: "faq", title: "常见问题" }
    ]
  }
];

let sectionObserver: IntersectionObserver | null = null;
let reducedMotionQuery: MediaQueryList | null = null;

function prefersReducedMotion() {
  return reducedMotionQuery?.matches ?? false;
}

function replaceHash(id: string) {
  if (typeof window === "undefined") {
    return;
  }
  const nextUrl = `${window.location.pathname}#${id}`;
  window.history.replaceState(null, "", nextUrl);
}

function scrollToSection(id: string, updateHash = true) {
  const target = document.getElementById(id);
  if (!target) {
    return;
  }
  target.scrollIntoView({
    behavior: prefersReducedMotion() ? "auto" : "smooth",
    block: "start"
  });
  activeSectionId.value = id;
  if (updateHash) {
    replaceHash(id);
  }
}

async function setupSectionObserver() {
  await nextTick();

  const root = scrollRoot.value;
  if (!root) {
    return;
  }

  const sections = Array.from(root.querySelectorAll<HTMLElement>("[data-doc-section]"));
  if (!sections.length) {
    return;
  }

  if (prefersReducedMotion() || typeof IntersectionObserver === "undefined") {
    return;
  }

  sectionObserver?.disconnect();
  sectionObserver = new IntersectionObserver(
    (entries) => {
      const visibleEntries = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => right.intersectionRatio - left.intersectionRatio);
      const nextSection = visibleEntries[0]?.target.getAttribute("id");
      if (nextSection) {
        activeSectionId.value = nextSection;
        replaceHash(nextSection);
      }
    },
    {
      root,
      threshold: [0.2, 0.45, 0.7],
      rootMargin: "-8% 0px -55% 0px"
    }
  );

  sections.forEach((section) => sectionObserver?.observe(section));
}

onMounted(async () => {
  reducedMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
  await setupSectionObserver();
  const hash = window.location.hash.replace(/^#/, "");
  if (hash) {
    setTimeout(() => {
      scrollToSection(hash, false);
    }, 0);
  }
});

onBeforeUnmount(() => {
  sectionObserver?.disconnect();
});
</script>

<style scoped>
.docs-site {
  position: relative;
  min-height: 100vh;
  height: 100vh;
  overflow-y: auto;
  color: #2a2d3a;
  background:
    radial-gradient(circle at top left, rgba(184, 121, 255, 0.16), transparent 24%),
    radial-gradient(circle at top right, rgba(114, 228, 255, 0.14), transparent 22%),
    linear-gradient(180deg, #f5f4fb 0%, #f8f9fd 100%);
}

.docs-site::before,
.docs-site::after {
  content: "";
  position: fixed;
  inset: auto;
  pointer-events: none;
  z-index: 0;
}

.docs-site::before {
  left: -140px;
  top: 160px;
  width: 460px;
  height: 460px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(184, 121, 255, 0.18), transparent 64%);
  filter: blur(40px);
}

.docs-site::after {
  right: -120px;
  top: 320px;
  width: 420px;
  height: 420px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(114, 228, 255, 0.18), transparent 64%);
  filter: blur(40px);
}

.docs-site__shell {
  position: relative;
  z-index: 1;
  width: min(1360px, calc(100% - 28px));
  margin: 0 auto;
  padding: 18px 0 28px;
}

.docs-sidebar__panel,
.docs-overview-strip,
.docs-article__section {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(157, 138, 201, 0.18);
  background: rgba(255, 255, 255, 0.72);
  box-shadow:
    0 18px 60px rgba(104, 83, 134, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.76);
  backdrop-filter: blur(18px);
}

.docs-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 42px;
  padding: 0 20px;
  border: 0;
  border-radius: 999px;
  font-size: 0.88rem;
  font-weight: 800;
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    background 160ms ease;
}

.docs-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  gap: 18px;
  margin-top: 18px;
  align-items: start;
}

.docs-sidebar {
  position: sticky;
  top: 112px;
}

.docs-sidebar__panel {
  border-radius: 30px;
  padding: 22px 18px 18px;
}

.docs-sidebar__eyebrow,
.docs-section__eyebrow {
  margin: 0;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #8a57e7;
}

.docs-sidebar__title,
.docs-overview-strip h2,
.docs-article__section h2 {
  margin: 0;
  color: #2a2d3a;
  letter-spacing: -0.03em;
}

.docs-sidebar__title {
  margin-top: 10px;
  font-size: 1.2rem;
  line-height: 1.2;
}

.docs-sidebar__groups {
  display: grid;
  gap: 18px;
  margin-top: 20px;
}

.docs-sidebar__group {
  display: grid;
  gap: 8px;
}

.docs-sidebar__group p {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #7b8090;
}

.docs-sidebar__link {
  display: block;
  padding: 8px 10px;
  border-radius: 12px;
  font-size: 0.92rem;
  color: #535868;
  transition:
    background 160ms ease,
    color 160ms ease,
    transform 160ms ease;
}

.docs-sidebar__link:hover {
  color: #2a2d3a;
  background: rgba(174, 105, 255, 0.1);
}

.docs-sidebar__link-active {
  color: #2a2d3a;
  background: linear-gradient(135deg, rgba(174, 105, 255, 0.12), rgba(95, 216, 255, 0.1));
  box-shadow: inset 2px 0 0 #8a57e7;
}

.docs-content {
  min-width: 0;
}

.docs-article {
  display: grid;
  gap: 16px;
}

.docs-overview-strip,
.docs-article__section {
  border-radius: 30px;
}

.docs-overview-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 26px 30px;
}

.docs-overview-strip__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.docs-overview-strip h2 {
  margin-top: 10px;
  font-size: clamp(1.9rem, 3vw, 2.5rem);
  line-height: 1.08;
}

.docs-section__lead,
.docs-card p,
.docs-mini-card span,
.docs-callout p,
.docs-note p,
.docs-faq__item p,
.docs-article__section > p:not(.docs-section__eyebrow) {
  margin: 14px 0 0;
  font-size: 1rem;
  line-height: 1.8;
  color: #535868;
}

.docs-button-primary {
  color: #fff;
  background: linear-gradient(135deg, #ae69ff, #6e59ff 42%, #59d6ff 100%);
  box-shadow: 0 12px 28px rgba(140, 105, 255, 0.28);
}

.docs-button:hover {
  transform: translateY(-1px);
}

.docs-button-secondary {
  color: #2a2d3a;
  background: rgba(255, 255, 255, 0.86);
  box-shadow:
    0 12px 24px rgba(85, 90, 120, 0.08),
    inset 0 0 0 1px rgba(157, 147, 196, 0.16);
}

.docs-article__section {
  padding: 30px;
  scroll-margin-top: 126px;
}

.docs-article__section h2 {
  margin-top: 10px;
  font-size: 1.9rem;
  line-height: 1.1;
}

.docs-article__section h3 {
  margin: 24px 0 0;
  font-size: 1.12rem;
  font-weight: 800;
  color: #2a2d3a;
}

.docs-grid {
  display: grid;
  gap: 14px;
  margin-top: 20px;
}

.docs-grid--cards {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.docs-grid--compact {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.docs-card,
.docs-mini-card,
.docs-callout,
.docs-note,
.docs-faq__item {
  border: 1px solid rgba(157, 138, 201, 0.16);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow:
    0 12px 24px rgba(85, 90, 120, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.docs-card,
.docs-faq__item {
  padding: 18px;
}

.docs-card h3,
.docs-faq__item h3 {
  margin: 0;
  color: #2a2d3a;
}

.docs-mini-card {
  display: grid;
  gap: 6px;
  padding: 16px;
}

.docs-mini-card strong {
  font-size: 0.95rem;
  word-break: break-all;
  color: #2a2d3a;
}

.docs-callout,
.docs-note {
  margin-top: 20px;
  padding: 18px;
}

.docs-callout strong,
.docs-note strong {
  display: block;
  font-size: 0.95rem;
  color: #2a2d3a;
}

.docs-callout {
  background: linear-gradient(135deg, rgba(174, 105, 255, 0.14), rgba(255, 255, 255, 0.9));
}

.docs-callout--soft {
  background: linear-gradient(135deg, rgba(95, 216, 255, 0.12), rgba(255, 255, 255, 0.9));
}

.docs-note {
  background: rgba(255, 250, 242, 0.92);
}

.docs-note--warning {
  border-color: rgba(217, 119, 6, 0.16);
  background: rgba(255, 248, 234, 0.94);
}

.docs-note--danger {
  border-color: rgba(220, 38, 38, 0.16);
  background: rgba(255, 243, 247, 0.94);
}

.docs-code {
  overflow-x: auto;
  margin: 18px 0 0;
  padding: 18px 20px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(25, 29, 43, 0.98), rgba(14, 18, 29, 0.98));
  color: #dae5ff;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.04),
    0 16px 32px rgba(31, 38, 61, 0.16);
}

.docs-code code {
  display: block;
  font-family: "SFMono-Regular", "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  font-size: 0.9rem;
  line-height: 1.8;
  white-space: pre;
}

.docs-steps,
.docs-list {
  margin: 18px 0 0;
  padding-left: 1.2rem;
  color: #535868;
}

.docs-steps li,
.docs-list li {
  margin-top: 10px;
  line-height: 1.8;
}

.docs-faq {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

@media (max-width: 1280px) {
}

@media (max-width: 960px) {
  .docs-site__shell {
    width: min(100%, calc(100% - 18px));
    padding-top: 10px;
  }

  .docs-layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .docs-sidebar {
    position: static;
  }

  .docs-sidebar__groups {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .docs-overview-strip {
    flex-direction: column;
    align-items: flex-start;
  }

  .docs-grid--cards,
  .docs-grid--compact {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .docs-overview-strip,
  .docs-article__section {
    padding: 24px 20px;
  }
}

@media (max-width: 640px) {
  .docs-site__shell {
    width: min(100%, calc(100% - 16px));
    padding-top: 8px;
  }

  .docs-sidebar__groups,
  .docs-grid--cards,
  .docs-grid--compact {
    grid-template-columns: minmax(0, 1fr);
  }

  .docs-button,
  .docs-button-secondary {
    width: 100%;
  }

  .docs-overview-strip h2,
  .docs-article__section h2 {
    font-size: 1.65rem;
  }
}
</style>
