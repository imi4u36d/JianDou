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
  background-color: #E0E5EC;
  box-shadow: 18px 18px 40px rgba(145, 164, 186, 0.6), -16px -16px 32px rgba(255, 255, 255, 0.9);
}

.hero-copy {
  position: relative;
  z-index: 1;
}

.hero-kicker {
  margin: 0;
  font-size: 0.75rem;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  color: #5c6272;
  font-weight: 700;
}

.hero-title {
  margin: 0.7rem 0 0;
  max-width: 18ch;
  font-family: "Inter", "PingFang SC", "Noto Sans SC", sans-serif;
  font-size: clamp(2rem, 4.6vw, 3.35rem);
  line-height: 1.2;
  letter-spacing: -0.03em;
  color: #1f242c;
}

.hero-description {
  margin: 1rem 0 0;
  max-width: 60ch;
  line-height: 1.7;
  color: #4c5262;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
  margin-top: 1.5rem;
}

.primary-cta,
.secondary-cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 2.75rem;
  padding: 0 1.3rem;
  border-radius: 999px;
  font-weight: 700;
  font-family: inherit;
  box-shadow: 8px 8px 18px rgba(118, 135, 160, 0.45), -8px -8px 18px rgba(255, 255, 255, 0.8);
  transition: transform 120ms ease, box-shadow 120ms ease;
}

.primary-cta {
  color: #1b1f27;
  background-color: #FF9AA2;
}

.primary-cta:active {
  box-shadow: inset 6px 6px 12px rgba(142, 157, 175, 0.5), inset -4px -4px 10px rgba(255, 255, 255, 0.9);
}

.secondary-cta {
  color: #505564;
  background-color: #E0E5EC;
}

.secondary-cta:active {
  box-shadow: inset 6px 6px 12px rgba(142, 157, 175, 0.35), inset -4px -4px 10px rgba(255, 255, 255, 0.8);
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
  font-size: 0.75rem;
  font-weight: 700;
  color: #4a4e59;
  background-color: #E0E5EC;
  box-shadow: 6px 6px 16px rgba(145, 164, 186, 0.4), -6px -6px 16px rgba(255, 255, 255, 0.9);
}

.hero-console {
  position: relative;
  z-index: 1;
  border-radius: 22px;
  background-color: #E0E5EC;
  padding: 1rem;
  box-shadow: 16px 16px 35px rgba(145, 164, 186, 0.55), -12px -12px 28px rgba(255, 255, 255, 0.85);
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
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #515664;
}

.console-head span {
  border-radius: 999px;
  padding: 0.24rem 0.52rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: #505564;
  background-color: #d0d4e0;
  box-shadow: inset 2px 2px 4px rgba(126, 141, 161, 0.4), inset -2px -2px 4px rgba(255, 255, 255, 0.7);
}

.console-flow {
  margin-top: 0.9rem;
  display: grid;
  gap: 0.52rem;
}

.flow-item {
  border-radius: 14px;
  padding: 0.65rem 0.75rem;
  background-color: #E0E5EC;
  box-shadow: 6px 6px 16px rgba(145, 164, 186, 0.35), -4px -4px 12px rgba(255, 255, 255, 0.9);
}

.flow-label {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #606376;
}

.flow-value {
  margin: 0.22rem 0 0;
  font-size: 0.82rem;
  color: #1f242c;
}

.console-preview {
  margin-top: 0.8rem;
  border-radius: 16px;
  background-color: #E0E5EC;
  padding: 0.82rem;
  box-shadow: 10px 10px 24px rgba(145, 164, 186, 0.4), -8px -8px 24px rgba(255, 255, 255, 0.9);
}

.preview-label {
  margin: 0;
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #606376;
}

.console-preview h3 {
  margin: 0.4rem 0 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #1f242c;
}

.preview-meta {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: #4c5262;
}

.preview-progress {
  margin-top: 0.7rem;
  height: 0.42rem;
  border-radius: 999px;
  overflow: hidden;
  background-color: #d0d4e0;
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.8), inset 0 -1px 2px rgba(112, 125, 144, 0.25);
}

.preview-bar {
  display: block;
  width: 68%;
  height: 100%;
  border-radius: inherit;
  background-color: #9ea7b8;
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
  background-color: #E0E5EC;
  box-shadow: 6px 6px 18px rgba(145, 164, 186, 0.35), -4px -4px 12px rgba(255, 255, 255, 0.9);
}

.console-metrics p {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: #1f242c;
}

.console-metrics small {
  display: block;
  margin-top: 0.18rem;
  color: #606376;
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
  background: radial-gradient(circle, rgba(224, 229, 236, 0.75), transparent 70%);
  filter: blur(5px);
}

.hero-orb {
  width: 240px;
  height: 240px;
  left: 46%;
  bottom: -140px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(196, 204, 215, 0.7), transparent 72%);
}

.hero-grain {
  inset: 0;
  opacity: 0.15;
  background-image: radial-gradient(rgba(185, 192, 204, 0.32) 0.45px, transparent 0.45px);
  background-size: 8px 8px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.3), transparent 78%);
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
  background: #babfd0;
  animation: pulse 1.25s ease-in-out infinite;
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
    opacity: 0.35;
    transform: scaleY(0.8);
  }
  50% {
    opacity: 0.85;
    transform: scaleY(1);
  }
}

@media (max-width: 960px) {
  .hero-card {
    grid-template-columns: 1fr;
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
