<template>
  <div class="workspace-shell">
    <aside class="workspace-sidebar liquid-glass">
      <div class="workspace-sidebar__top">
        <div class="workspace-sidebar__topbar">
          <div class="sidebar-brand">
            <img alt="煎豆 Logo" class="sidebar-brand__logo" src="/brand/jiandou-mark.svg" />
          </div>
        </div>

        <nav class="sidebar-nav">
          <RouterLink
            v-for="item in navItems"
            :key="item.to"
            class="sidebar-nav__item"
            :class="{ 'sidebar-nav__item-active': isActive(item.to) }"
            :to="item.to"
          >
            <span class="sidebar-nav__icon"><component :is="iconComponentMap[item.icon]" /></span>
            <span class="sidebar-nav__label">{{ item.label }}</span>
          </RouterLink>
        </nav>
      </div>

      <WorkspaceAccountMenu />
    </aside>

    <div class="workspace-main">
      <main class="workspace-content glass">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Shared workspace navigation shell.
 */
import { useRoute } from "vue-router";
import WorkspaceAccountMenu from "@/components/layout/WorkspaceAccountMenu.vue";
import { iconComponentMap, type IconName } from "@/components/icons";

const route = useRoute();

const navItems: { to: string; label: string; icon: IconName }[] = [
  { to: "/", label: "首页", icon: "home" },
  { to: "/image-tasks", label: "图片", icon: "image" },
  { to: "/video-tasks", label: "视频", icon: "video" },
  { to: "/materials", label: "素材", icon: "material" },
];

function isActive(target: string) {
  return route.path === target || route.path.startsWith(`${target}/`);
}
</script>

<style scoped src="./workspace-shell.css"></style>
