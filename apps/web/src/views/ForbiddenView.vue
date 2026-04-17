<template>
  <section class="forbidden-view">
    <div class="forbidden-view__card">
      <p class="forbidden-view__eyebrow">403 Forbidden</p>
      <h1>当前账号没有管理端权限</h1>
      <p>
        普通用户仍然可以进入工作台，但 `/admin/*` 仅对 `ADMIN` 角色开放。
      </p>
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
  background:
    radial-gradient(circle at 20% 20%, rgba(255, 187, 116, 0.16), transparent 24%),
    radial-gradient(circle at 80% 75%, rgba(92, 197, 255, 0.18), transparent 24%),
    linear-gradient(135deg, #0c121d, #171521);
}

.forbidden-view__card {
  width: min(560px, 100%);
  padding: 34px;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(11, 16, 24, 0.82);
  box-shadow: 0 28px 70px rgba(0, 0, 0, 0.42);
  text-align: center;
}

.forbidden-view__eyebrow {
  margin: 0 0 12px;
  color: rgba(255, 190, 117, 0.84);
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.forbidden-view__card h1 {
  margin: 0;
  font-family: "Sora", "Inter", sans-serif;
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  letter-spacing: -0.05em;
}

.forbidden-view__card p {
  margin: 16px 0 0;
  color: rgba(236, 242, 255, 0.72);
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
  background: linear-gradient(135deg, #ffb468, #61cbff);
  color: #07101c;
}

.forbidden-view__secondary {
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.86);
}

@media (max-width: 640px) {
  .forbidden-view__actions {
    flex-direction: column;
  }
}
</style>
