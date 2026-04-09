<template>
  <section class="hero-card">
    <div class="hero-copy">
      <p class="hero-kicker">AI CREATIVE WORKBENCH</p>
      <h1 class="hero-title">一句话到成片，内容团队的文生视频工作台</h1>
      <p class="hero-description">
        以最少输入启动生成流程，自动跟踪任务阶段，并将结果沉淀到可复用的素材库。设计、运营、发布可共享同一套交付链路。
      </p>
      <div class="hero-actions">
        <RouterLink class="primary-cta" to="/generate">开始生成</RouterLink>
        <RouterLink class="secondary-cta" to="/tasks">查看任务</RouterLink>
      </div>
      <div class="hero-chips">
        <span v-for="chip in chips" :key="chip" class="hero-chip">{{ chip }}</span>
      </div>
    </div>

    <aside class="hero-console" aria-label="生成中控台预览">
      <div class="console-head">
        <p>生成中控台</p>
        <span>Live</span>
      </div>
      <div class="console-flow">
        <article v-for="step in flowSteps" :key="step.label" class="flow-item">
          <p class="flow-label">{{ step.label }}</p>
          <p class="flow-value">{{ step.value }}</p>
        </article>
      </div>
      <div class="console-preview">
        <p class="preview-label">当前任务</p>
        <h3>城市夜雨 · 竖版短视频</h3>
        <p class="preview-meta">wan2.6-t2v · 1080x1920 · 5s</p>
        <div class="preview-progress">
          <span class="preview-bar"></span>
        </div>
      </div>
      <div class="console-metrics">
        <article v-for="item in metrics" :key="item.label">
          <p>{{ item.value }}</p>
          <small>{{ item.label }}</small>
        </article>
      </div>
    </aside>
    <div class="hero-aura" aria-hidden="true"></div>
    <div class="hero-orb" aria-hidden="true"></div>
    <div class="hero-grain" aria-hidden="true"></div>
    <div class="hero-pulse" aria-hidden="true">
      <span></span>
      <span></span>
      <span></span>
    </div>
  </section>
</template>

<script setup lang="ts">
const chips = ["最少参数提交", "任务状态实时追踪", "结果资产可复用"];

const flowSteps = [
  { label: "01 提示词输入", value: "镜头语言 + 场景设定" },
  { label: "02 模型编排", value: "按输出比例自动选择参数" },
  { label: "03 任务执行", value: "阶段回传 + 错误可追踪" },
];

const metrics = [
  { value: "4m 12s", label: "平均交付时长" },
  { value: "97%", label: "任务完成率" },
  { value: "12+", label: "常用输出规格" },
];
</script>

<style scoped>
.hero-card {
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
  gap: clamp(1rem, 2.4vw, 1.8rem);
  border-radius: 32px;
  padding: clamp(1.2rem, 3.4vw, 2.25rem);
  border: 1px solid rgba(124, 159, 230, 0.32);
  background:
    radial-gradient(circle at 8% 12%, rgba(88, 164, 255, 0.32), transparent 38%),
    radial-gradient(circle at 92% 20%, rgba(84, 205, 184, 0.26), transparent 34%),
    linear-gradient(135deg, #08152a, #0d2445 46%, #122f57 100%);
  box-shadow:
    inset 0 1px 0 rgba(186, 211, 255, 0.2),
    0 30px 60px rgba(6, 20, 42, 0.42);
}

.hero-copy {
  position: relative;
  z-index: 1;
}

.hero-kicker {
  margin: 0;
  font-size: 0.74rem;
  letter-spacing: 0.24em;
  text-transform: uppercase;
  color: rgba(208, 224, 255, 0.88);
  font-weight: 700;
}

.hero-title {
  margin: 0.7rem 0 0;
  max-width: 15ch;
  font-family: "Sora", "PingFang SC", "Noto Sans SC", sans-serif;
  font-size: clamp(2rem, 4.6vw, 3.35rem);
  line-height: 1.05;
  letter-spacing: -0.04em;
  color: #eff4ff;
}

.hero-description {
  margin: 1rem 0 0;
  max-width: 50ch;
  line-height: 1.72;
  color: rgba(203, 220, 245, 0.86);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  margin-top: 1.4rem;
}

.primary-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.75rem;
  padding: 0 1.3rem;
  border-radius: 999px;
  font-weight: 700;
  color: #0a1b36;
  background: linear-gradient(120deg, #82ccff, #83f4de);
  box-shadow: 0 12px 28px rgba(101, 227, 255, 0.32);
}

.secondary-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.75rem;
  padding: 0 1.25rem;
  border-radius: 999px;
  font-weight: 700;
  color: #d6e4ff;
  border: 1px solid rgba(171, 198, 245, 0.34);
  background: rgba(14, 34, 67, 0.5);
}

.primary-cta:hover,
.secondary-cta:hover {
  transform: translateY(-1px);
}

.hero-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 1rem;
}

.hero-chip {
  border-radius: 999px;
  padding: 0.38rem 0.7rem;
  font-size: 0.76rem;
  font-weight: 700;
  color: rgba(222, 234, 255, 0.9);
  background: rgba(27, 58, 105, 0.5);
  border: 1px solid rgba(170, 196, 240, 0.26);
}

.hero-console {
  position: relative;
  z-index: 1;
  border-radius: 22px;
  border: 1px solid rgba(173, 201, 247, 0.28);
  background:
    linear-gradient(180deg, rgba(7, 24, 49, 0.84), rgba(12, 34, 70, 0.84)),
    radial-gradient(circle at 16% 12%, rgba(117, 189, 255, 0.26), transparent 34%);
  padding: 1rem;
  box-shadow: inset 0 1px 0 rgba(186, 211, 255, 0.2);
}

.console-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.7rem;
}

.console-head p {
  margin: 0;
  font-size: 0.86rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(209, 226, 255, 0.9);
}

.console-head span {
  border-radius: 999px;
  padding: 0.24rem 0.52rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: #08203f;
  background: linear-gradient(120deg, #9fd8ff, #7df1d8);
}

.console-flow {
  margin-top: 0.9rem;
  display: grid;
  gap: 0.52rem;
}

.flow-item {
  border-radius: 14px;
  border: 1px solid rgba(168, 196, 245, 0.2);
  background: rgba(15, 39, 76, 0.56);
  padding: 0.65rem 0.75rem;
}

.flow-label {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: rgba(173, 196, 232, 0.9);
}

.flow-value {
  margin: 0.22rem 0 0;
  font-size: 0.82rem;
  color: rgba(226, 236, 255, 0.94);
}

.console-preview {
  margin-top: 0.8rem;
  border-radius: 16px;
  border: 1px solid rgba(171, 198, 245, 0.24);
  background: linear-gradient(160deg, rgba(12, 35, 71, 0.7), rgba(8, 25, 53, 0.72));
  padding: 0.82rem;
}

.preview-label {
  margin: 0;
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: rgba(173, 196, 232, 0.9);
}

.console-preview h3 {
  margin: 0.4rem 0 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #eef4ff;
}

.preview-meta {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: rgba(177, 203, 241, 0.92);
}

.preview-progress {
  margin-top: 0.7rem;
  height: 0.42rem;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(158, 188, 236, 0.24);
}

.preview-bar {
  display: block;
  width: 68%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #73c6ff, #71efd4);
}

.console-metrics {
  margin-top: 0.75rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.45rem;
}

.console-metrics article {
  border-radius: 12px;
  padding: 0.55rem 0.58rem;
  background: rgba(16, 42, 82, 0.52);
  border: 1px solid rgba(168, 196, 245, 0.2);
}

.console-metrics p {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #eef4ff;
}

.console-metrics small {
  display: block;
  margin-top: 0.18rem;
  color: rgba(173, 196, 232, 0.9);
  font-size: 0.66rem;
}

.hero-aura,
.hero-orb,
.hero-grain,
.hero-pulse {
  pointer-events: none;
  position: absolute;
}

.hero-aura {
  width: 400px;
  height: 400px;
  right: -160px;
  top: -170px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(113, 223, 255, 0.3), transparent 68%);
  filter: blur(6px);
}

.hero-orb {
  width: 240px;
  height: 240px;
  left: 46%;
  bottom: -140px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(96, 176, 255, 0.24), transparent 72%);
}

.hero-grain {
  inset: 0;
  opacity: 0.24;
  background-image: radial-gradient(rgba(221, 237, 255, 0.26) 0.45px, transparent 0.45px);
  background-size: 8px 8px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.62), transparent 82%);
}

.hero-pulse {
  right: 1.2rem;
  bottom: 0.9rem;
  display: flex;
  gap: 0.24rem;
  align-items: flex-end;
}

.hero-pulse span {
  width: 3px;
  border-radius: 999px;
  background: linear-gradient(180deg, #8ad4ff, #76f0d8);
  animation: pulse 1s ease-in-out infinite;
}

.hero-pulse span:nth-child(1) {
  height: 10px;
}

.hero-pulse span:nth-child(2) {
  height: 16px;
  animation-delay: 0.12s;
}

.hero-pulse span:nth-child(3) {
  height: 12px;
  animation-delay: 0.24s;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.45;
    transform: scaleY(0.76);
  }
  50% {
    opacity: 1;
    transform: scaleY(1);
  }
}

@media (max-width: 960px) {
  .hero-card {
    grid-template-columns: 1fr;
  }

  .hero-title {
    max-width: 20ch;
  }

  .hero-pulse {
    display: none;
  }
}

@media (max-width: 768px) {
  .console-metrics {
    grid-template-columns: 1fr;
  }

  .hero-chip {
    font-size: 0.72rem;
  }

  .hero-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
