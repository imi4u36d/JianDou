<template>
  <section class="highlights">
    <header class="section-head">
      <p class="section-kicker">WORKFLOW DESIGN</p>
      <h2 class="section-title">以交付为中心的能力编排</h2>
    </header>
    <div class="highlight-grid">
      <article
        v-for="item in items"
        :key="item.title"
        class="highlight-card"
        :class="{
          'highlight-card-featured': item.variant === 'featured',
          'highlight-card-warm': item.variant === 'warm',
        }"
      >
        <p class="card-tag">{{ item.tag }}</p>
        <p class="card-title">{{ item.title }}</p>
        <p class="card-description">{{ item.description }}</p>
        <div v-if="item.variant === 'featured'" class="card-meta">
          <span>Prompt to Params</span>
          <span>Traceable Delivery</span>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
const items = [
  {
    tag: "Core",
    title: "从一句话到可交付成片",
    description: "输入提示词后自动生成参数建议，降低创作门槛，同时保留可控项供团队按业务场景微调。",
    variant: "featured",
  },
  {
    tag: "Live",
    title: "阶段化任务回传",
    description: "排队、执行、完成状态持续刷新，异常信息可定位到具体任务节点，减少排查成本。",
    variant: "default",
  },
  {
    tag: "Asset",
    title: "结果沉淀为素材资产",
    description: "每次生成结果可统一回看、下载和复用，为后续脚本迭代或版本对比提供稳定基础。",
    variant: "default",
  },
  {
    tag: "Ops",
    title: "适配内容团队协作节奏",
    description: "保持流程轻量，支持运营、设计、发布在同一工作台内流转，缩短从创意到上线的链路。",
    variant: "warm",
  },
];
</script>

<style scoped>
.highlights {
  border-radius: 26px;
  padding: clamp(1rem, 2.6vw, 1.6rem);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.38)),
    var(--bg-surface);
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-raise);
}

.section-head {
  margin-bottom: 1rem;
}

.section-kicker {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--text-muted);
}

.section-title {
  margin: 0.48rem 0 0;
  font-family: "Inter", "PingFang SC", "Noto Sans SC", sans-serif;
  font-size: clamp(1.2rem, 3vw, 1.7rem);
  color: var(--text-strong);
}

.highlight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.highlight-card {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  padding: 1rem;
  border: 1px solid var(--surface-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.36)),
    var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.highlight-card-featured {
  grid-column: 1 / -1;
  padding: 1.2rem;
  border-color: rgba(197, 108, 115, 0.18);
  background:
    radial-gradient(circle at top right, rgba(255, 183, 174, 0.2), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(255, 255, 255, 0.48)),
    var(--bg-surface);
  box-shadow: var(--shadow-raise);
}

.highlight-card-warm {
  border-color: rgba(197, 108, 115, 0.16);
}

.card-tag {
  margin: 0;
  font-size: 0.66rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #7b8ba4;
  font-weight: 700;
}

.card-title {
  margin: 0.38rem 0 0;
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-strong);
}

.card-description {
  margin: 0.55rem 0 0;
  font-size: 0.9rem;
  line-height: 1.68;
  color: var(--text-body);
}

.highlight-card-featured .card-tag {
  color: #8d5660;
}

.highlight-card-featured .card-title {
  color: var(--text-strong);
  font-size: 1.1rem;
}

.highlight-card-featured .card-description {
  color: var(--text-body);
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.8rem;
}

.card-meta span {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.28rem 0.58rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #8d5660;
  border: 1px solid rgba(197, 108, 115, 0.16);
  background: rgba(255, 247, 245, 0.74);
}

@media (max-width: 1024px) {
  .highlight-grid {
    grid-template-columns: 1fr;
  }

  .highlight-card-featured {
    grid-column: auto;
  }
}
</style>
