<template>
  <main class="official-site">
    <section class="official-hero">
      <div class="official-hero__mesh" aria-hidden="true"></div>
      <div class="official-hero__panel">
        <p class="official-hero__eyebrow">JIANDOU STUDIO ENGINE</p>
        <h1>把小说、脚本和灵感，压缩成可以批量生产的短剧视频流程。</h1>
        <p class="official-hero__description">
          煎豆是面向内容团队的 AI 文生视频工作台。它负责接住你的文本输入、组织模型调用、追踪生成任务，
          再把结果沉淀成可继续运营的资产。
        </p>

        <div class="official-hero__actions">
          <RouterLink class="official-button official-button-primary" to="/tasks">
            进入工作台
          </RouterLink>
          <RouterLink class="official-button official-button-secondary" to="/activate">
            激活邀请码
          </RouterLink>
        </div>

        <div class="official-hero__metrics">
          <article v-for="item in metrics" :key="item.label">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </article>
        </div>
      </div>

      <aside class="official-console" aria-label="工作流预览">
        <div class="official-console__header">
          <span>Pipeline Preview</span>
          <strong>Queue Mode</strong>
        </div>

        <div class="official-console__track">
          <article v-for="step in steps" :key="step.title" class="official-console__step">
            <p>{{ step.index }}</p>
            <h2>{{ step.title }}</h2>
            <span>{{ step.description }}</span>
          </article>
        </div>

        <div class="official-console__card">
          <p>当前任务样例</p>
          <h3>都市悬疑 · 第 08 集预告</h3>
          <span>脚本拆解 / 镜头规划 / 图像生成 / 成片拼接</span>
        </div>
      </aside>
    </section>

    <section class="official-section">
      <div class="official-section__head">
        <p>Why JianDou</p>
        <h2>官网负责对外表达，工作台负责真正开工。</h2>
      </div>

      <div class="official-grid">
        <article v-for="feature in features" :key="feature.title" class="official-card">
          <p>{{ feature.kicker }}</p>
          <h3>{{ feature.title }}</h3>
          <span>{{ feature.description }}</span>
        </article>
      </div>
    </section>

    <section class="official-section official-section-band">
      <div class="official-band">
        <div>
          <p class="official-band__eyebrow">Open The Workbench</p>
          <h2>官网首页只做一件事：把用户送进真正的生产入口。</h2>
        </div>
        <div class="official-band__actions">
          <RouterLink class="official-button official-button-primary" to="/tasks">
            直接进入
          </RouterLink>
          <RouterLink class="official-button official-button-secondary" to="/login">
            登录账号
          </RouterLink>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
const metrics = [
  { value: "TXT / Prompt", label: "输入起点" },
  { value: "Queue", label: "任务执行模式" },
  { value: "Assets", label: "结果沉淀方式" }
];

const steps = [
  { index: "01", title: "文本接入", description: "上传文本或直接输入创作素材" },
  { index: "02", title: "任务编排", description: "按照配置和模板拆分生成链路" },
  { index: "03", title: "结果交付", description: "输出素材、日志、状态和成片结果" }
];

const features = [
  {
    kicker: "TEXT TO PIPELINE",
    title: "不是单次试玩工具，而是面向持续生产的任务系统",
    description: "任务创建、状态追踪、暂停继续、异常诊断和结果回看都在同一套界面里完成。"
  },
  {
    kicker: "MODEL READY",
    title: "保留模型切换能力，但不把复杂度暴露给普通使用者",
    description: "官网对外讲能力，后台对内管理模型、配置和账号，避免把系统细节混进首屏。"
  },
  {
    kicker: "ASSET STORAGE",
    title: "上传素材、生成产物和过程文件都可以继续复用",
    description: "视频生成不是终点，素材沉淀和复盘追踪才是团队能放大产能的关键。"
  }
];
</script>

<style scoped>
.official-site {
  min-height: 100vh;
  color: #f7efe6;
  background:
    radial-gradient(circle at top left, rgba(236, 109, 44, 0.16), transparent 28%),
    radial-gradient(circle at 80% 14%, rgba(244, 198, 87, 0.18), transparent 22%),
    linear-gradient(180deg, #20150f 0%, #120d0a 46%, #0a0d10 100%);
}

.official-hero,
.official-section {
  width: min(1200px, calc(100% - 40px));
  margin: 0 auto;
}

.official-hero {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 28px;
  padding: 32px 0 28px;
}

.official-hero__mesh {
  position: absolute;
  inset: 12px 0 auto;
  height: 520px;
  border-radius: 40px;
  background:
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(180deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.8), transparent 90%);
  pointer-events: none;
}

.official-hero__panel,
.official-console,
.official-card,
.official-band {
  position: relative;
  border: 1px solid rgba(255, 243, 228, 0.1);
  background: rgba(16, 13, 12, 0.66);
  backdrop-filter: blur(18px);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.28);
}

.official-hero__panel {
  z-index: 1;
  padding: 44px;
  border-radius: 36px;
}

.official-hero__eyebrow,
.official-section__head p,
.official-band__eyebrow,
.official-card p,
.official-console__header span,
.official-console__step p,
.official-console__card p {
  margin: 0;
  letter-spacing: 0.28em;
  text-transform: uppercase;
  font-size: 0.72rem;
  font-weight: 700;
  color: rgba(247, 219, 182, 0.74);
}

.official-hero__panel h1,
.official-section__head h2,
.official-band h2 {
  margin: 14px 0 0;
  font-family: "Bebas Neue", "Oswald", "PingFang SC", sans-serif;
  letter-spacing: 0.02em;
  line-height: 0.96;
}

.official-hero__panel h1 {
  max-width: 10ch;
  font-size: clamp(4.2rem, 9vw, 7.6rem);
  color: #fff0db;
}

.official-hero__description {
  max-width: 34rem;
  margin: 24px 0 0;
  color: rgba(255, 239, 220, 0.76);
  font-size: 1.03rem;
  line-height: 1.85;
}

.official-hero__actions,
.official-band__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 28px;
}

.official-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 52px;
  padding: 0 22px;
  border-radius: 999px;
  font-weight: 700;
  transition: transform 140ms ease, background 140ms ease;
}

.official-button:hover {
  transform: translateY(-1px);
}

.official-button-primary {
  background: linear-gradient(135deg, #f4b34b, #ea6f33);
  color: #1d120d;
}

.official-button-secondary {
  border: 1px solid rgba(255, 243, 228, 0.16);
  background: rgba(255, 248, 240, 0.04);
  color: #fff4e6;
}

.official-hero__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 34px;
}

.official-hero__metrics article {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  border-radius: 22px;
  background: rgba(255, 250, 243, 0.04);
  border: 1px solid rgba(255, 243, 228, 0.08);
}

.official-hero__metrics strong {
  font-family: "JetBrains Mono", "SFMono-Regular", monospace;
  font-size: 1.22rem;
  color: #fff0db;
}

.official-hero__metrics span,
.official-card span,
.official-console__step span,
.official-console__card span {
  color: rgba(255, 239, 220, 0.68);
  line-height: 1.7;
}

.official-console {
  z-index: 1;
  display: grid;
  gap: 18px;
  align-content: start;
  padding: 26px;
  border-radius: 30px;
}

.official-console__header,
.official-console__card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.official-console__header {
  padding-bottom: 14px;
  border-bottom: 1px solid rgba(255, 243, 228, 0.08);
}

.official-console__header strong {
  color: #f6b560;
  font-size: 0.92rem;
}

.official-console__track {
  display: grid;
  gap: 12px;
}

.official-console__step {
  display: grid;
  gap: 6px;
  padding: 18px;
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 248, 240, 0.05), rgba(255, 248, 240, 0.02));
  border: 1px solid rgba(255, 243, 228, 0.08);
}

.official-console__step h2,
.official-console__card h3,
.official-card h3 {
  margin: 0;
  color: #fff0db;
}

.official-console__step h2 {
  font-size: 1.08rem;
}

.official-console__card {
  display: grid;
  gap: 8px;
  justify-content: start;
  padding: 20px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(244, 179, 75, 0.18), transparent 30%),
    linear-gradient(180deg, rgba(49, 28, 20, 0.9), rgba(20, 16, 14, 0.92));
}

.official-console__card h3 {
  font-size: 1.24rem;
}

.official-section {
  padding: 18px 0 34px;
}

.official-section__head {
  display: grid;
  gap: 10px;
  margin-bottom: 20px;
}

.official-section__head h2,
.official-band h2 {
  max-width: 12ch;
  font-size: clamp(2.4rem, 5vw, 4.1rem);
  color: #fff0db;
}

.official-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.official-card {
  display: grid;
  gap: 12px;
  padding: 26px;
  border-radius: 28px;
}

.official-card h3 {
  font-size: 1.32rem;
  line-height: 1.35;
}

.official-section-band {
  padding-bottom: 48px;
}

.official-band {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 30px;
  border-radius: 30px;
}

@media (max-width: 1024px) {
  .official-hero,
  .official-grid,
  .official-band {
    grid-template-columns: 1fr;
  }

  .official-band {
    display: grid;
  }

  .official-hero__panel h1 {
    max-width: none;
  }
}

@media (max-width: 720px) {
  .official-site {
    padding-bottom: 24px;
  }

  .official-hero,
  .official-section {
    width: min(100% - 24px, 1200px);
  }

  .official-hero {
    gap: 16px;
    padding-top: 12px;
  }

  .official-hero__panel,
  .official-console,
  .official-card,
  .official-band {
    padding: 22px;
    border-radius: 24px;
  }

  .official-hero__metrics,
  .official-grid {
    grid-template-columns: 1fr;
  }

  .official-hero__panel h1,
  .official-section__head h2,
  .official-band h2 {
    line-height: 1;
  }
}
</style>
