<template>
  <section class="forbidden-view">
    <div class="forbidden-view__card">
      <p class="forbidden-view__eyebrow">403 Forbidden</p>
      <h1>当前账号没有管理端权限</h1>
      <div class="forbidden-view__actions">
        <RouterLink class="forbidden-view__secondary" to="/workspace">返回工作台</RouterLink>
        <RouterLink class="forbidden-view__primary" to="/tasks">打开任务列表</RouterLink>
      </div>
    </div>
  </section>
</template>

<style scoped>
.forbidden-view {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: var(--bg-base);
}

.forbidden-view__card {
  width: min(560px, 100%);
  padding: 34px;
  border-radius: 24px;
  border: 1px solid rgba(15, 20, 25, 0.06);
  background: #fff;
  box-shadow: var(--shadow-panel);
  text-align: center;
}

.forbidden-view__eyebrow {
  margin: 0 0 12px;
  color: var(--accent-cyan);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.forbidden-view__card h1 {
  margin: 0;
  font-family: inherit;
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  letter-spacing: -0.05em;
  color: var(--text-strong);
}

.forbidden-view__card p {
  margin: 16px 0 0;
  color: var(--text-body);
  line-height: 1.8;
}

.forbidden-view__actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 28px;
}

.forbidden-view__primary,
.forbidden-view__secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 46px;
  padding: 0 18px;
  border-radius: 16px;
  font-weight: 700;
}

.forbidden-view__primary {
  background: var(--bg-accent);
  color: #fff;
}

.forbidden-view__secondary {
  border: 1px solid rgba(15, 20, 25, 0.08);
  background: #fff;
  color: var(--text-strong);
}

@media (max-width: 640px) {
  .forbidden-view__actions {
    flex-direction: column;
  }
}
</style>
