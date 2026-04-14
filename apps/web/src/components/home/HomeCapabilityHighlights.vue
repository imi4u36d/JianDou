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
  background-color: #E0E5EC;
  box-shadow: 18px 18px 45px rgba(145, 164, 186, 0.45), -14px -14px 32px rgba(255, 255, 255, 0.9);
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
  color: #5f6573;
}

.section-title {
  margin: 0.48rem 0 0;
  font-family: "Inter", "PingFang SC", "Noto Sans SC", sans-serif;
  font-size: clamp(1.2rem, 3vw, 1.7rem);
  color: #1f242c;
}

.highlight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.highlight-card {
  border-radius: 18px;
  padding: 1rem;
  background-color: #E0E5EC;
  box-shadow: 12px 12px 28px rgba(145, 164, 186, 0.35), -8px -8px 20px rgba(255, 255, 255, 0.9);
}

.highlight-card-featured {
  grid-column: 1 / -1;
  padding: 1.2rem;
  background-color: #d7dce6;
  box-shadow: 14px 14px 32px rgba(145, 164, 186, 0.45), -10px -10px 26px rgba(255, 255, 255, 0.9);
}

.highlight-card-warm {
  background-color: #E0E5EC;
}

.card-tag {
  margin: 0;
  font-size: 0.66rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #6983a6;
  font-weight: 700;
}

.card-title {
  margin: 0.38rem 0 0;
  font-size: 1rem;
  font-weight: 700;
  color: #1f242c;
}

.card-description {
  margin: 0.55rem 0 0;
  font-size: 0.9rem;
  line-height: 1.68;
  color: #4c5262;
}

.highlight-card-featured .card-tag {
  color: #4c5262;
}

.highlight-card-featured .card-title {
  color: #1f242c;
  font-size: 1.1rem;
}

.highlight-card-featured .card-description {
  color: #4c5262;
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
