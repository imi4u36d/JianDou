<template>
  <section class="showcase">
    <header class="section-head">
      <p class="section-kicker">OUTPUT SHOWCASE</p>
      <h2 class="section-title">案例陈列</h2>
      <p class="section-description">同一工作台支持竖版、横版与产品叙事类视频产出，便于快速匹配不同发布渠道。</p>
    </header>
    <div class="showcase-grid">
      <article class="lead-card">
        <div class="lead-cover" :style="{ '--cover-accent': leadCase.accent }">
          <span class="cover-badge">主案例</span>
          <p class="cover-title">{{ leadCase.scene }}</p>
        </div>
        <div class="lead-body">
          <h3>{{ leadCase.title }}</h3>
          <p>{{ leadCase.prompt }}</p>
          <div class="video-meta">
            <span>{{ leadCase.model }}</span>
            <span>{{ leadCase.size }}</span>
            <span>{{ leadCase.duration }}</span>
          </div>
        </div>
      </article>

      <div class="side-grid">
        <article v-for="item in sideCases" :key="item.title" class="side-card">
          <div class="side-cover" :style="{ '--cover-accent': item.accent }">
            <span class="cover-badge">{{ item.duration }}</span>
            <p class="cover-title">{{ item.scene }}</p>
          </div>
          <div class="side-body">
            <h4>{{ item.title }}</h4>
            <p>{{ item.prompt }}</p>
            <div class="video-meta">
              <span>{{ item.model }}</span>
              <span>{{ item.size }}</span>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
const leadCase = {
  title: "城市夜雨",
  scene: "电影感街景",
  prompt: "雨夜霓虹街头，镜头推进后人物回头定格，适合剧情预告与品牌氛围短片。",
  duration: "5s",
  model: "wan2.6-t2v",
  size: "1080x1920",
  accent: "rgba(95, 168, 255, 0.82)",
};

const sideCases = [
  {
    title: "海岸日出",
    scene: "自然风光",
    prompt: "金色日出照亮海面，无人机俯瞰海岸线，适合旅游与生活方式内容。",
    duration: "8s",
    model: "wan2.6-t2v-us",
    size: "1920x1080",
    accent: "rgba(255, 180, 108, 0.8)",
  },
  {
    title: "科技展厅",
    scene: "产品发布",
    prompt: "未来感展厅中旋转产品模型，适用于新品发布和参数亮点展示。",
    duration: "6s",
    model: "wan2.5-t2v-preview",
    size: "1280x720",
    accent: "rgba(95, 208, 186, 0.8)",
  },
];
</script>

<style scoped>
.showcase {
  border-radius: 26px;
  padding: clamp(1rem, 2.6vw, 1.6rem);
  border: 1px solid rgba(185, 203, 233, 0.58);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(246, 250, 255, 0.72)),
    radial-gradient(circle at 86% 20%, rgba(104, 169, 255, 0.16), transparent 34%);
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

.section-description {
  margin: 0.45rem 0 0;
  color: #4c6486;
  font-size: 0.92rem;
  line-height: 1.68;
}

.showcase-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(280px, 0.88fr);
  gap: 0.85rem;
}

.lead-card,
.side-card {
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid rgba(191, 210, 240, 0.7);
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 12px 28px rgba(36, 60, 98, 0.08);
}

.lead-cover,
.side-cover {
  position: relative;
  min-height: 160px;
  padding: 0.95rem;
  background:
    radial-gradient(circle at 12% 18%, color-mix(in srgb, var(--cover-accent) 44%, transparent), transparent 40%),
    linear-gradient(145deg, rgba(13, 28, 52, 0.95), rgba(18, 56, 112, 0.86));
}

.lead-cover {
  min-height: 210px;
}

.cover-badge {
  display: inline-flex;
  min-width: 2.6rem;
  height: 1.5rem;
  padding: 0 0.58rem;
  border-radius: 999px;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 700;
  color: #e9f4ff;
  background: rgba(233, 245, 255, 0.18);
}

.cover-title {
  position: absolute;
  left: 0.95rem;
  right: 0.95rem;
  bottom: 0.86rem;
  margin: 0;
  color: #eff7ff;
  font-weight: 600;
}

.lead-body,
.side-body {
  padding: 0.98rem;
}

.lead-body h3,
.side-body h4 {
  margin: 0;
  color: #163156;
}

.lead-body h3 {
  font-size: 1.08rem;
}

.side-body h4 {
  font-size: 1rem;
}

.lead-body p,
.side-body p {
  margin: 0.45rem 0 0;
  font-size: 0.85rem;
  line-height: 1.66;
  color: #4e678a;
}

.video-meta {
  margin-top: 0.7rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.video-meta span {
  border-radius: 999px;
  padding: 0.22rem 0.56rem;
  font-size: 0.72rem;
  color: #425f84;
  background: rgba(203, 226, 255, 0.5);
}

.side-grid {
  display: grid;
  gap: 0.82rem;
}

@media (max-width: 1024px) {
  .showcase-grid {
    grid-template-columns: 1fr;
  }

  .lead-cover {
    min-height: 180px;
  }
}
</style>
