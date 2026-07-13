import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchAdminOverview } from "@/admin/features/dashboard/services/dashboardService";
import { fetchAdminUsers } from "@/admin/features/users/services/userService";
import { dashboardPulseItems, dashboardSummaryCards, formatDashboardDateTime } from "@/admin/features/dashboard/dashboard-presenters";
import type { AdminOverviewResponse, AdminPaginatedResponse, AdminTaskListItem, AdminUser } from "@/types";

interface AdminDashboardApi {
  fetchOverview(): Promise<AdminOverviewResponse>;
  fetchUsers(): Promise<AdminPaginatedResponse<AdminUser>>;
}

interface AdminDashboardDependencies {
  api?: AdminDashboardApi;
  reportError?: (message: string) => void;
  loadOnMount?: boolean;
}

const defaultApi: AdminDashboardApi = {
  fetchOverview: fetchAdminOverview,
  fetchUsers: fetchAdminUsers,
};

export function useAdminDashboard(dependencies: AdminDashboardDependencies = {}) {
  const api = dependencies.api ?? defaultApi;
  const reportError = dependencies.reportError ?? ElMessage.error;
  const refreshing = ref(false);
  const initialLoading = ref(true);
  const overview = ref<AdminOverviewResponse | null>(null);
  const users = ref<AdminUser[]>([]);

  const summaryCards = computed(() => dashboardSummaryCards(overview.value, users.value));
  const pulseItems = computed(() => dashboardPulseItems(overview.value, users.value));
  const recentTasks = computed<AdminTaskListItem[]>(() => overview.value?.recentTasks ?? []);
  const recentFailures = computed<AdminTaskListItem[]>(() => overview.value?.recentFailures ?? []);
  const userQueues = computed(() => overview.value?.queue?.userQueues ?? []);
  const lastUpdatedLabel = computed(() => formatDashboardDateTime(overview.value?.generatedAt));

  async function loadDashboard() {
    refreshing.value = !initialLoading.value;
    const [overviewResult, usersResult] = await Promise.allSettled([
      api.fetchOverview(),
      api.fetchUsers(),
    ]);
    const errors: string[] = [];
    if (overviewResult.status === "fulfilled") overview.value = overviewResult.value ?? null;
    else errors.push(overviewResult.reason instanceof Error ? overviewResult.reason.message : "读取任务概览失败");
    if (usersResult.status === "fulfilled") users.value = usersResult.value?.items ?? [];
    else errors.push(usersResult.reason instanceof Error ? usersResult.reason.message : "读取用户统计失败");
    if (errors.length) reportError(errors.join("；"));
    refreshing.value = false;
    initialLoading.value = false;
  }

  if (dependencies.loadOnMount !== false) onMounted(loadDashboard);

  return {
    refreshing, initialLoading, overview, users, summaryCards, pulseItems, recentTasks,
    recentFailures, userQueues, lastUpdatedLabel, loadDashboard,
  };
}
