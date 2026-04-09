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
  border: 1px solid rgba(185, 203, 233, 0.58);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(246, 250, 255, 0.72)),
    radial-gradient(circle at 12% 16%, rgba(104, 169, 255, 0.16), transparent 34%);
  box-shadow: 0 16px 38px rgba(37, 60, 96, 0.11);
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
  color: #5f7597;
}

.section-title {
  margin: 0.48rem 0 0;
  font-family: "Sora", "PingFang SC", "Noto Sans SC", sans-serif;
  font-size: clamp(1.2rem, 3vw, 1.7rem);
  color: #132f56;
}

.highlight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.highlight-card {
  border-radius: 18px;
  border: 1px solid rgba(199, 215, 241, 0.72);
  background:
    radial-gradient(circle at 6% 10%, rgba(124, 210, 255, 0.14), transparent 40%),
    rgba(255, 255, 255, 0.82);
  padding: 1rem;
}

.highlight-card-featured {
  grid-column: 1 / -1;
  padding: 1.2rem;
  background:
    radial-gradient(circle at 86% 22%, rgba(90, 167, 255, 0.24), transparent 34%),
    linear-gradient(135deg, rgba(13, 46, 93, 0.96), rgba(16, 63, 122, 0.94));
  border: 1px solid rgba(112, 158, 226, 0.56);
}

.highlight-card-warm {
  background:
    radial-gradient(circle at 84% 20%, rgba(255, 178, 119, 0.26), transparent 36%),
    linear-gradient(160deg, rgba(255, 248, 236, 0.95), rgba(255, 251, 245, 0.86));
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
  font-size: 0.98rem;
  font-weight: 700;
  color: #153358;
}

.card-description {
  margin: 0.55rem 0 0;
  font-size: 0.9rem;
  line-height: 1.68;
  color: #4b6384;
}

.highlight-card-featured .card-tag {
  color: rgba(190, 216, 255, 0.9);
}

.highlight-card-featured .card-title {
  color: #eef4ff;
  font-size: 1.1rem;
}

.highlight-card-featured .card-description {
  color: rgba(205, 222, 245, 0.9);
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
