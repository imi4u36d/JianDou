<template>
  <div class="workbench-shell">
    <div class="workbench-shell-glow workbench-shell-glow-left" aria-hidden="true"></div>
    <div class="workbench-shell-glow workbench-shell-glow-right" aria-hidden="true"></div>

    <div class="workbench-shell-frame">
      <header class="workbench-topbar">
        <div class="workbench-brand">
          <span class="workbench-brand-mark"></span>
          <div class="workbench-brand-copy">
            <strong>AI Cut Studio</strong>
            <span>Agent-first workspace</span>
          </div>
        </div>

        <nav class="workbench-topbar-nav" aria-label="主导航">
          <RouterLink to="/tasks" class="workbench-nav-link" :class="isTasksRoute ? 'workbench-nav-link-active' : ''">
            任务
          </RouterLink>
          <RouterLink to="/tasks/new" class="workbench-nav-link" :class="isCreateTaskRoute ? 'workbench-nav-link-active' : ''">
            新建
          </RouterLink>
          <RouterLink to="/studio" class="workbench-nav-link" :class="isStudioRoute ? 'workbench-nav-link-active' : ''">
            工作台
          </RouterLink>
          <RouterLink to="/generate" class="workbench-nav-link" :class="isGenerateRoute ? 'workbench-nav-link-active' : ''">
            文生媒体
          </RouterLink>
          <RouterLink to="/script" class="workbench-nav-link" :class="isScriptRoute ? 'workbench-nav-link-active' : ''">
            文生脚本
          </RouterLink>
          <RouterLink to="/admin/dashboard" class="workbench-nav-link" :class="isAdminRoute ? 'workbench-nav-link-active' : ''">
            后台
          </RouterLink>
        </nav>
      </header>

      <main class="workbench-main">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();

const isTasksRoute = computed(() => route.path === "/tasks" || /^\/tasks\/[^/]+$/.test(route.path));
const isCreateTaskRoute = computed(() => route.path === "/tasks/new");
const isStudioRoute = computed(() => route.path === "/studio" || route.path.startsWith("/studio/"));
const isGenerateRoute = computed(() => route.path === "/generate" || route.path.startsWith("/generate/"));
const isScriptRoute = computed(() => route.path === "/script" || route.path.startsWith("/script/"));
const isAdminRoute = computed(() => route.path === "/admin" || route.path.startsWith("/admin/"));
</script>

<style scoped>
.workbench-shell {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
  color: #1f2937;
  background:
    radial-gradient(circle at 16% 12%, rgba(125, 211, 252, 0.18), transparent 22%),
    radial-gradient(circle at 82% 14%, rgba(134, 239, 172, 0.16), transparent 24%),
    linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
}

.workbench-shell-glow {
  position: fixed;
  width: 26rem;
  height: 26rem;
  border-radius: 999px;
  filter: blur(24px);
  opacity: 0.36;
  pointer-events: none;
}

.workbench-shell-glow-left {
  left: -10rem;
  top: -8rem;
  background: rgba(125, 211, 252, 0.2);
}

.workbench-shell-glow-right {
  right: -10rem;
  top: 12rem;
  background: rgba(134, 239, 172, 0.18);
}

.workbench-shell-frame {
  position: relative;
  z-index: 1;
  margin: 0 auto;
  display: grid;
  min-height: 100vh;
  width: min(100%, 1760px);
  padding: 1rem;
}

.workbench-topbar {
  position: sticky;
  top: 0.8rem;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border: 1px solid #dfe6f1;
  border-radius: 1.6rem;
  background: rgba(255, 255, 255, 0.88);
  padding: 0.95rem 1.05rem;
  box-shadow: 0 14px 40px rgba(148, 163, 184, 0.16);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
}

.workbench-brand {
  display: inline-flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
}

.workbench-brand-mark {
  width: 0.82rem;
  height: 0.82rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #38bdf8, #22c55e);
  box-shadow: 0 0 0 6px rgba(56, 189, 248, 0.15);
}

.workbench-brand-copy {
  display: grid;
  gap: 0.08rem;
}

.workbench-brand-copy strong {
  color: #0f172a;
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.workbench-brand-copy span {
  color: #64748b;
  font-size: 0.72rem;
}

.workbench-topbar-nav {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.workbench-nav-link {
  border: 1px solid #dbe3ee;
  border-radius: 999px;
  background: #fff;
  padding: 0.48rem 0.85rem;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.workbench-nav-link:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(148, 163, 184, 0.14);
}

.workbench-nav-link-active {
  border-color: #93c5fd;
  background: #eff6ff;
  color: #1d4ed8;
}

.workbench-main {
  min-width: 0;
  padding-top: 1rem;
}

@media (max-width: 860px) {
  .workbench-topbar {
    flex-direction: column;
    align-items: stretch;
  }

  .workbench-topbar-nav {
    justify-content: flex-start;
  }
}
</style>
