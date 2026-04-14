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
          <div class="cover-topline">
            <span class="cover-badge">主案例</span>
            <span class="cover-ratio">{{ leadCase.size }}</span>
          </div>
          <div class="cover-scene" aria-hidden="true">
            <div class="cover-glow"></div>
            <div class="cover-bars">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div class="cover-subject"></div>
            <div class="cover-track"><span></span></div>
          </div>
          <div class="cover-bottom">
            <p class="cover-title">{{ leadCase.scene }}</p>
            <span class="cover-shot">Shot 03</span>
          </div>
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
            <div class="cover-topline">
              <span class="cover-badge">{{ item.duration }}</span>
              <span class="cover-ratio">{{ item.size }}</span>
            </div>
            <div class="cover-scene" aria-hidden="true">
              <div class="cover-glow"></div>
              <div class="cover-bars">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div class="cover-subject cover-subject-small"></div>
              <div class="cover-track"><span></span></div>
            </div>
            <div class="cover-bottom">
              <p class="cover-title">{{ item.scene }}</p>
              <span class="cover-shot">Shot 0{{ sideCases.indexOf(item) + 4 }}</span>
            </div>
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
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(255, 255, 255, 0.4)),
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

.section-description {
  margin: 0.45rem 0 0;
  color: var(--text-body);
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
  border: 1px solid var(--surface-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.34)),
    var(--bg-surface);
  box-shadow: var(--shadow-raise-soft);
}

.lead-cover,
.side-cover {
  position: relative;
  min-height: 160px;
  padding: 0.95rem;
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.28), transparent 26%),
    linear-gradient(160deg, rgba(19, 28, 41, 0.86), rgba(72, 89, 117, 0.5)),
    linear-gradient(145deg, var(--cover-accent), rgba(255, 255, 255, 0));
}

.lead-cover {
  min-height: 210px;
}

.cover-topline,
.cover-bottom {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.65rem;
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
  color: rgba(255, 255, 255, 0.88);
  background-color: rgba(255, 255, 255, 0.14);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.14);
}

.cover-ratio,
.cover-shot {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.22rem 0.56rem;
  font-size: 0.68rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.76);
  background: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.12);
}

.cover-scene {
  position: relative;
  min-height: 110px;
  margin-top: 0.75rem;
}

.cover-glow {
  position: absolute;
  top: 0;
  right: 1rem;
  width: 86px;
  height: 86px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.04) 72%);
}

.cover-bars {
  position: absolute;
  left: 0;
  right: 0;
  top: 0.5rem;
  display: flex;
  gap: 0.35rem;
}

.cover-bars span {
  height: 0.35rem;
  flex: 1;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
}

.cover-subject {
  position: absolute;
  left: 1.2rem;
  bottom: 1rem;
  width: 88px;
  height: 72px;
  border-radius: 52px 52px 16px 16px;
  background: linear-gradient(180deg, rgba(13, 18, 27, 0.12), rgba(13, 18, 27, 0.58));
  box-shadow: 70px -14px 0 -16px rgba(255, 255, 255, 0.12);
}

.cover-subject-small {
  width: 72px;
  height: 58px;
  box-shadow: 56px -10px 0 -16px rgba(255, 255, 255, 0.1);
}

.cover-track {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0.2rem;
  height: 0.32rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
}

.cover-track span {
  display: block;
  width: 58%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.26), rgba(255, 255, 255, 0.92));
}

.cover-title {
  margin: 0;
  color: rgba(255, 255, 255, 0.92);
  font-weight: 600;
}

.lead-body,
.side-body {
  padding: 0.98rem;
}

.lead-body h3,
.side-body h4 {
  margin: 0;
  color: var(--text-strong);
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
  color: var(--text-body);
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
  color: var(--text-body);
  border: 1px solid var(--surface-border);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.84), rgba(255, 255, 255, 0.28)),
    var(--bg-surface);
  box-shadow: var(--shadow-pressed);
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
