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
        <div class="preview-frame" aria-hidden="true">
          <span class="preview-frame__tag">Shot 03</span>
          <div class="preview-frame__sun"></div>
          <div class="preview-frame__subject"></div>
          <div class="preview-frame__timeline">
            <span></span>
          </div>
        </div>
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
  background:
    radial-gradient(circle at top right, rgba(255, 183, 174, 0.24), transparent 24%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.45)),
    var(--bg-surface);
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-raise);
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
  color: #6f7988;
  font-weight: 700;
}

.hero-title {
  margin: 0.7rem 0 0;
  max-width: 18ch;
  font-family: "Inter", "PingFang SC", "Noto Sans SC", sans-serif;
  font-size: clamp(2rem, 4.6vw, 3.35rem);
  line-height: 1.2;
  letter-spacing: -0.03em;
  color: var(--text-strong);
}

.hero-description {
  margin: 1rem 0 0;
  max-width: 60ch;
  line-height: 1.7;
  color: var(--text-body);
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
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-raise-soft);
  transition: transform 120ms ease, box-shadow 120ms ease;
}

.primary-cta {
  color: #553b44;
  background: linear-gradient(145deg, #ffe5de, #ffb7ae);
  border-color: rgba(197, 108, 115, 0.14);
}

.primary-cta:active {
  box-shadow: inset 6px 6px 12px rgba(142, 157, 175, 0.5), inset -4px -4px 10px rgba(255, 255, 255, 0.9);
}

.secondary-cta {
  color: var(--text-body);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.42)),
    var(--bg-surface);
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
  color: var(--text-body);
  border: 1px solid var(--surface-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.36)),
    var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.hero-console {
  position: relative;
  z-index: 1;
  border-radius: 22px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.42)),
    var(--bg-surface);
  padding: 1rem;
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-raise-soft);
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
  color: var(--text-body);
}

.console-head span {
  border-radius: 999px;
  padding: 0.24rem 0.52rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: #85585d;
  border: 1px solid rgba(197, 108, 115, 0.14);
  background: linear-gradient(145deg, rgba(255, 229, 222, 0.92), rgba(255, 183, 174, 0.72));
  box-shadow: none;
}

.console-flow {
  margin-top: 0.9rem;
  display: grid;
  gap: 0.52rem;
}

.flow-item {
  border-radius: 14px;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--surface-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.34)),
    var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.flow-label {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.flow-value {
  margin: 0.22rem 0 0;
  font-size: 0.82rem;
  color: var(--text-strong);
}

.console-preview {
  margin-top: 0.8rem;
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.42)),
    var(--bg-surface);
  padding: 0.82rem;
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-raise-soft);
}

.preview-frame {
  position: relative;
  overflow: hidden;
  min-height: 110px;
  margin-bottom: 0.78rem;
  border-radius: 14px;
  background:
    radial-gradient(circle at 20% 20%, rgba(255, 255, 255, 0.38), transparent 22%),
    linear-gradient(155deg, rgba(27, 39, 60, 0.86), rgba(84, 104, 137, 0.56)),
    linear-gradient(135deg, rgba(255, 183, 174, 0.42), transparent 55%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}

.preview-frame__tag {
  position: absolute;
  top: 0.75rem;
  left: 0.75rem;
  z-index: 2;
  border-radius: 999px;
  padding: 0.18rem 0.5rem;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.88);
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.preview-frame__sun {
  position: absolute;
  top: 1.25rem;
  right: 1.4rem;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 183, 174, 0.95), rgba(255, 183, 174, 0.08) 72%);
  filter: blur(1px);
}

.preview-frame__subject {
  position: absolute;
  left: 1.4rem;
  bottom: -0.6rem;
  width: 86px;
  height: 94px;
  border-radius: 48px 48px 0 0;
  background: linear-gradient(180deg, rgba(14, 18, 28, 0.12), rgba(14, 18, 28, 0.62));
  box-shadow: 78px -18px 0 -18px rgba(255, 255, 255, 0.14);
}

.preview-frame__timeline {
  position: absolute;
  left: 0.75rem;
  right: 0.75rem;
  bottom: 0.75rem;
  height: 0.3rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
}

.preview-frame__timeline span {
  display: block;
  width: 62%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(255, 183, 174, 0.82), rgba(255, 255, 255, 0.92));
}

.preview-label {
  margin: 0;
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.console-preview h3 {
  margin: 0.4rem 0 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-strong);
}

.preview-meta {
  margin: 0.35rem 0 0;
  font-size: 0.78rem;
  color: var(--text-body);
}

.preview-progress {
  margin-top: 0.7rem;
  height: 0.42rem;
  border-radius: 999px;
  overflow: hidden;
  background-color: rgba(197, 208, 223, 0.56);
  box-shadow: inset 0 0 0 1px rgba(141, 157, 180, 0.08);
}

.preview-bar {
  display: block;
  width: 68%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #c56c73, #ffb7ae);
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
  border: 1px solid var(--surface-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.3)),
    var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.console-metrics p {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text-strong);
}

.console-metrics small {
  display: block;
  margin-top: 0.18rem;
  color: var(--text-muted);
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
  background: radial-gradient(circle, rgba(255, 183, 174, 0.26), transparent 70%);
  filter: blur(5px);
}

.hero-orb {
  width: 240px;
  height: 240px;
  left: 46%;
  bottom: -140px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(190, 206, 230, 0.44), transparent 72%);
}

.hero-grain {
  inset: 0;
  opacity: 0.12;
  background-image: radial-gradient(rgba(185, 192, 204, 0.22) 0.45px, transparent 0.45px);
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
  background: #c56c73;
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
