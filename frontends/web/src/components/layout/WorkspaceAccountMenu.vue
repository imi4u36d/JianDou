<template>
  <section class="sidebar-account-zone">
    <button class="sidebar-credit-card" type="button" :title="creditTitle" @click="openCreditDialog">
      <span class="sidebar-credit-card__label">积分</span>
      <strong>{{ creditValue }}</strong>
    </button>
    <div ref="accountMenuRef" class="sidebar-account" @keydown.escape="closeUserMenu">
      <button
        class="sidebar-account__trigger"
        type="button"
        aria-label="用户信息"
        :aria-expanded="userMenuOpen"
        @click.stop="toggleUserMenu"
      >
        <span class="sidebar-account__avatar">{{ avatarInitials }}</span>
        <span v-if="currentUser" class="sidebar-account__status" aria-hidden="true"></span>
      </button>

      <div v-if="userMenuOpen" class="sidebar-user-popover" @click.stop>
        <div class="sidebar-user-popover__header">
          <div class="sidebar-user-popover__avatar">{{ avatarInitials }}</div>
          <div>
            <p class="sidebar-user-popover__name">{{ accountTitle }}</p>
            <p class="sidebar-user-popover__meta">{{ accountMeta }}</p>
          </div>
        </div>
        <div class="sidebar-user-popover__actions">
          <a v-if="isAdmin" class="sidebar-user-popover__link" :href="adminPortalUrl">管理</a>
          <button v-if="currentUser" class="sidebar-user-popover__logout" type="button" @click="handleLogout">
            退出
          </button>
          <RouterLink v-else class="sidebar-user-popover__link" to="/login" @click="closeUserMenu">
            登录
          </RouterLink>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchCreditSummary } from "@/api/credits";
import { requireAuth } from "@/auth/modal";
import { getRuntimeConfig } from "@/api/runtime-config";
import { logoutAndClearSession, useAuthSessionState } from "@/auth/session";
import { openCreditDetailsDialog } from "@/composables/useCreditDialog";
import type { CreditSummary } from "@/types";

const route = useRoute();
const router = useRouter();
const authState = useAuthSessionState();
const adminPortalUrl = getRuntimeConfig().adminBaseUrl;
const userMenuOpen = ref(false);
const accountMenuRef = ref<HTMLElement | null>(null);
const credits = ref<CreditSummary | null>(null);
const creditsLoading = ref(false);

const currentUser = computed(() => authState.user.value);
const isAdmin = computed(() => authState.isAdmin.value);
const avatarInitials = computed(() => (currentUser.value?.username || "JD").slice(0, 2).toUpperCase());
const roleLabel = computed(() => {
  if (currentUser.value?.role === "ADMIN") return "管理员";
  if (currentUser.value?.role === "USER") return "普通用户";
  return "未登录";
});
const accountTitle = computed(() => currentUser.value?.username || "未登录");
const accountMeta = computed(() => currentUser.value ? roleLabel.value : "未登录");
const creditValue = computed(() => {
  if (!currentUser.value || (creditsLoading.value && !credits.value) || !credits.value) return "--";
  if (credits.value.exempt) return "免扣";
  return formatCreditBalance(credits.value.balance ?? 0);
});
const creditTitle = computed(() => {
  if (!currentUser.value) return "登录后查看积分余额";
  if (credits.value?.exempt) return "当前账号积分免扣";
  return `剩余积分：${creditValue.value}`;
});

function formatCreditBalance(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value;
}

function closeUserMenu() {
  userMenuOpen.value = false;
}

async function loadCredits() {
  if (!authState.isAuthenticated.value) {
    credits.value = null;
    return;
  }
  creditsLoading.value = true;
  try {
    credits.value = await fetchCreditSummary();
  } catch {
    credits.value = null;
  } finally {
    creditsLoading.value = false;
  }
}

async function openCreditDialog() {
  closeUserMenu();
  const authenticated = await requireAuth({
    title: "登录后查看积分",
    message: "登录后可以查看积分余额、充值入口和使用明细。",
  });
  if (authenticated) openCreditDetailsDialog(credits.value);
}

function handleDocumentPointerDown(event: PointerEvent) {
  if (!userMenuOpen.value) return;
  const target = event.target;
  if (!(target instanceof Node) || accountMenuRef.value?.contains(target)) return;
  closeUserMenu();
}

async function handleLogout() {
  closeUserMenu();
  await logoutAndClearSession();
  await router.replace("/login");
}

onMounted(() => {
  void loadCredits();
  document.addEventListener("pointerdown", handleDocumentPointerDown);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", handleDocumentPointerDown);
});

watch(() => route.fullPath, () => {
  closeUserMenu();
  void loadCredits();
});

watch(() => authState.isAuthenticated.value, () => {
  void loadCredits();
});
</script>

<style scoped src="./workspace-account-menu.css"></style>
