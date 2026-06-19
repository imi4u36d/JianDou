<template>
  <div class="page-shell admin-layout">
    <aside class="surface-card admin-layout__aside">
      <div class="admin-layout__brand">
        <div class="admin-layout__brand-mark">
          <img alt="煎豆 Logo" class="admin-layout__brand-logo" src="/brand/jiandou-mark.svg" />
        </div>
        <div>
          <h1>JianDou</h1>
        </div>
      </div>

      <el-menu :default-active="activeMenu" class="admin-layout__menu" router>
        <el-menu-item index="/admin">
          <el-icon><DataAnalysis /></el-icon>
          <span>概览</span>
        </el-menu-item>
        <el-menu-item index="/admin/tasks">
          <el-icon><Tickets /></el-icon>
          <span>任务</span>
        </el-menu-item>
        <el-menu-item index="/admin/users">
          <el-icon><UserFilled /></el-icon>
          <span>用户</span>
        </el-menu-item>
        <el-menu-item index="/admin/invites">
          <el-icon><Ticket /></el-icon>
          <span>邀请码</span>
        </el-menu-item>
        <el-menu-item index="/admin/credits">
          <el-icon><Coin /></el-icon>
          <span>积分</span>
        </el-menu-item>
        <el-menu-item index="/admin/system">
          <el-icon><Setting /></el-icon>
          <span>系统</span>
        </el-menu-item>
      </el-menu>

      <div class="admin-layout__aside-footer">
        <div class="admin-layout__profile">
          <strong>{{ currentUser?.displayName || currentUser?.username }}</strong>
          <span>{{ currentUser?.username }} · {{ currentUser?.role }}</span>
        </div>
        <el-button plain @click="handleLogout">
          退出
        </el-button>
      </div>
    </aside>

    <section class="admin-layout__main">
      <header class="surface-card admin-layout__header">
        <div>
          <h2>{{ currentTitle }}</h2>
        </div>
      </header>

      <main class="admin-layout__content">
        <RouterView />
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { logoutAndClearSession, useAuthSessionState } from "@/auth/session";

const route = useRoute();
const router = useRouter();
const authState = useAuthSessionState();

const currentUser = computed(() => authState.user.value);
const activeMenu = computed(() => {
  if (route.path === "/admin" || route.path.startsWith("/admin/")) {
    // Highlight the correct menu item based on the sub-path
    for (const prefix of ["/admin/tasks", "/admin/users", "/admin/invites", "/admin/credits", "/admin/system"]) {
      if (route.path.startsWith(prefix)) {
        return prefix;
      }
    }
    return "/admin";
  }
  return route.path;
});
const currentTitle = computed(() => {
  const title = route.meta.title;
  return typeof title === "string" && title.trim() ? title : "管理系统";
});

async function handleLogout() {
  await logoutAndClearSession();
  await router.replace("/login");
}
</script>

<style scoped>
.admin-layout {
  position: relative;
  display: grid;
  grid-template-columns: 272px minmax(0, 1fr);
  gap: 20px;
  padding: 24px;
}

.admin-layout__aside {
  position: sticky;
  top: 24px;
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-height: calc(100vh - 48px);
  padding: 22px 14px 16px;
  border-radius: 22px;
  overflow: hidden;
}

.admin-layout__brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 10px;
}

.admin-layout__brand-mark {
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: 15px;
  background: linear-gradient(135deg, rgba(0, 169, 187, 0.16), rgba(27, 124, 255, 0.16));
}

.admin-layout__brand-logo {
  width: 30px;
  height: 30px;
  filter: drop-shadow(0 0 12px rgba(98, 136, 255, 0.18));
}

.admin-layout__eyebrow {
  margin: 0 0 4px;
  color: var(--jd-text-soft);
  font-size: 0.78rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.admin-layout__brand h1,
.admin-layout__header h2 {
  margin: 0;
  font-family: inherit;
}

.admin-layout__menu {
  flex: 1;
  min-height: 240px;
}

.admin-layout__aside-footer {
  display: grid;
  gap: 10px;
  padding: 14px 10px 8px;
  border-top: 1px solid rgba(23, 32, 42, 0.08);
}

.admin-layout__profile {
  display: grid;
  gap: 4px;
}

.admin-layout__profile span {
  color: var(--jd-text-soft);
  font-size: 0.92rem;
}

.admin-layout__main {
  min-width: 0;
}

.admin-layout__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-radius: 18px;
}

.admin-layout__header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--jd-text-soft);
  font-size: 0.94rem;
}

.admin-layout__content {
  padding-top: 20px;
}

@media (max-width: 1100px) {
  .admin-layout {
    grid-template-columns: 1fr;
  }

  .admin-layout__aside {
    position: static;
    top: auto;
    max-width: 100%;
    max-height: none;
    min-width: 0;
    gap: 12px;
    padding: 14px;
    border-radius: 18px;
  }

  .admin-layout__brand {
    padding: 0 4px;
  }

  .admin-layout__brand-mark {
    width: 42px;
    height: 42px;
    border-radius: 14px;
  }

  .admin-layout__brand-logo {
    width: 28px;
    height: 28px;
  }

  .admin-layout__menu {
    display: flex;
    width: 100%;
    min-height: 0;
    overflow-x: auto;
    padding: 2px 0;
  }

  .admin-layout__menu :deep(.el-menu-item) {
    flex: 0 0 auto;
    min-height: 40px;
    margin: 0 4px;
    padding: 0 12px;
    border-radius: 999px;
  }

  .admin-layout__aside-footer {
    display: none;
  }
}

@media (max-width: 768px) {
  .admin-layout {
    padding: 12px;
    gap: 12px;
  }

  .admin-layout__header {
    padding: 16px;
    border-radius: 16px;
  }

  .admin-layout__header h2 {
    font-size: 1.2rem;
  }

  .admin-layout__content {
    padding-top: 12px;
  }
}
</style>
