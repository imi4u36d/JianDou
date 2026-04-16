<template>
  <main class="home-page">
    <section class="hero-block">
      <div class="hero-block__glow hero-block__glow-left" aria-hidden="true"></div>
      <div class="hero-block__glow hero-block__glow-right" aria-hidden="true"></div>

      <div class="hero-copy">
        <h2 class="hero-title">从小说到成片，一键直达</h2>
        <div class="hero-actions">
          <RouterLink class="btn-primary hero-btn hero-btn-primary" to="/generate">
            <span class="hero-btn__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="9" />
                <path d="m10 8 6 4-6 4V8Z" fill="currentColor" stroke="none" />
              </svg>
            </span>
            创建新任务
          </RouterLink>
          <RouterLink class="btn-secondary hero-btn hero-btn-secondary" to="/tasks">
            <span class="hero-btn__icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="4" y="4" width="6" height="6" rx="1.4" />
                <rect x="14" y="4" width="6" height="6" rx="1.4" />
                <rect x="4" y="14" width="6" height="6" rx="1.4" />
                <rect x="14" y="14" width="6" height="6" rx="1.4" />
              </svg>
            </span>
            查看任务
          </RouterLink>
        </div>
      </div>
    </section>

    <section class="cases-section">
      <div class="cases-section__head">
        <h3>案例展示</h3>
      </div>

      <div class="case-grid">
        <article
          v-for="item in caseStudies"
          :key="item.title"
          class="case-card"
          :style="{ '--case-accent': item.accent, '--case-scene': item.scene }"
        >
          <div class="case-card__visual">
            <div class="case-card__blur case-card__blur-left" aria-hidden="true"></div>
            <div class="case-card__poster">
              <div class="case-card__poster-inner"></div>
              <p>{{ item.posterLabel }}</p>
            </div>
            <div class="case-card__blur case-card__blur-right" aria-hidden="true"></div>
          </div>
          <div class="case-card__body">
            <h4>{{ item.title }}</h4>
            <p>{{ item.subtitle }}</p>
          </div>
        </article>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
/**
 * 首页页面组件。
 */
const caseStudies = [
  {
    title: "悬疑短剧 · 第 12 集",
    subtitle: "电影感短剧预告",
    posterLabel: "悬疑短剧",
    accent: "rgba(164, 83, 255, 0.42)",
    scene: "linear-gradient(180deg, rgba(35,40,52,0.78), rgba(6,8,13,0.92)), radial-gradient(circle at 50% 40%, rgba(207,180,140,0.48), transparent 56%)",
  },
  {
    title: "奇幻世界 · Seed #88271",
    subtitle: "9:16 竖版视频",
    posterLabel: "奇幻爱情",
    accent: "rgba(78, 219, 255, 0.38)",
    scene: "linear-gradient(180deg, rgba(47,31,38,0.7), rgba(9,8,12,0.94)), radial-gradient(circle at 54% 38%, rgba(230,176,128,0.42), transparent 48%)",
  },
  {
    title: "森林魔法 · Seed #88271",
    subtitle: "9:16 竖版视频",
    posterLabel: "森林魔法",
    accent: "rgba(125, 169, 255, 0.38)",
    scene: "linear-gradient(180deg, rgba(18,35,43,0.78), rgba(7,10,14,0.95)), radial-gradient(circle at 52% 38%, rgba(128,184,164,0.4), transparent 48%)",
  },
];
</script>

<style scoped>
.home-page {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 46px;
  height: 100%;
  min-height: 0;
  padding: 44px 16px 10px;
  overflow: hidden;
}

.hero-block {
  position: relative;
  display: grid;
  place-items: center;
  padding: 54px 20px 52px;
  overflow: hidden;
}

.hero-block__glow {
  position: absolute;
  border-radius: 999px;
  filter: blur(78px);
  opacity: 0.55;
  pointer-events: none;
}

.hero-block__glow-left {
  left: 10%;
  top: 6%;
  width: 300px;
  height: 180px;
  background: rgba(164, 83, 255, 0.28);
}

.hero-block__glow-right {
  right: 8%;
  top: 12%;
  width: 340px;
  height: 200px;
  background: rgba(78, 219, 255, 0.22);
}

.hero-copy {
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
  gap: 26px;
  text-align: center;
}

.hero-title {
  margin: 0;
  max-width: 12ch;
  font-family: "Sora", "Inter", sans-serif;
  font-size: clamp(3rem, 6vw, 4.6rem);
  font-weight: 700;
  line-height: 1.06;
  letter-spacing: -0.07em;
  background: linear-gradient(90deg, #c567ff 0%, #9e92ff 38%, #65c8ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  text-shadow:
    0 0 32px rgba(176, 92, 255, 0.2),
    0 0 48px rgba(78, 219, 255, 0.12);
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 24px;
}

.hero-btn {
  min-width: 280px;
  min-height: 72px;
  padding: 0 28px;
  border-radius: 22px;
  font-size: 1rem;
}

.hero-btn-primary {
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.08),
    0 18px 40px rgba(176, 92, 255, 0.24),
    0 0 68px rgba(78, 219, 255, 0.16);
}

.hero-btn-secondary {
  background: rgba(8, 11, 18, 0.82);
  border-color: rgba(176, 92, 255, 0.52);
  color: #aa8bff;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.04),
    0 0 36px rgba(176, 92, 255, 0.1);
}

.hero-btn__icon {
  display: inline-flex;
  width: 22px;
  height: 22px;
}

.hero-btn__icon svg {
  width: 22px;
  height: 22px;
}

.cases-section {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
  min-height: 0;
}

.cases-section__head h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.92);
}

.case-grid {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  min-height: 0;
  overflow: auto;
  padding-right: 6px;
}

.case-card {
  display: grid;
  gap: 14px;
}

.case-card__visual {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 108px 1fr;
  align-items: stretch;
  min-height: 196px;
  overflow: hidden;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background:
    radial-gradient(circle at 50% 50%, var(--case-accent), transparent 58%),
    var(--case-scene);
  box-shadow: var(--shadow-panel);
}

.case-card__blur {
  position: relative;
}

.case-card__blur::after {
  content: "";
  position: absolute;
  inset: 0;
  backdrop-filter: blur(16px);
  background: rgba(255, 255, 255, 0.04);
}

.case-card__poster {
  position: relative;
  z-index: 1;
  display: grid;
  align-content: end;
  justify-items: center;
  padding: 10px 0 14px;
  background: rgba(0, 0, 0, 0.42);
  border-left: 1px solid rgba(255, 255, 255, 0.08);
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}

.case-card__poster-inner {
  width: 100%;
  flex: 1;
  min-height: 148px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0)),
    radial-gradient(circle at 50% 34%, rgba(255, 244, 216, 0.2), transparent 34%),
    linear-gradient(180deg, rgba(25, 32, 46, 0.42), rgba(6, 9, 14, 0.12));
}

.case-card__poster p {
  margin: 0;
  font-size: 0.54rem;
  color: rgba(255, 255, 255, 0.88);
}

.case-card__body {
  display: grid;
  gap: 4px;
}

.case-card__body h4 {
  margin: 0;
  font-size: 0.98rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.94);
}

.case-card__body p {
  margin: 0;
  font-size: 0.84rem;
  color: rgba(255, 255, 255, 0.5);
}

@media (max-width: 1100px) {
  .case-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .home-page {
    padding: 18px 2px 10px;
    gap: 28px;
  }

  .hero-block {
    padding: 24px 0 10px;
  }

  .hero-actions {
    width: 100%;
    gap: 14px;
  }

  .hero-btn {
    min-width: 0;
    width: 100%;
    min-height: 58px;
    border-radius: 18px;
  }
}
</style>
