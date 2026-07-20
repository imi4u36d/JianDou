import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchAdminOverview } from "@/admin/features/dashboard/services/dashboardService";
import { dashboardPulseItems, dashboardSummaryCards, formatDashboardDateTime } from "@/admin/features/dashboard/dashboard-presenters";
import type { AdminOverviewResponse, AdminTaskListItem } from "@/types";

interface AdminDashboardApi {
  fetchOverview(): Promise<AdminOverviewResponse>;
}

interface AdminDashboardDependencies {
  api?: AdminDashboardApi;
  reportError?: (message: string) => void;
  loadOnMount?: boolean;
}

const defaultApi: AdminDashboardApi = {
  fetchOverview: fetchAdminOverview,
};

export function useAdminDashboard(dependencies: AdminDashboardDependencies = {}) {
  const api = dependencies.api ?? defaultApi;
  const reportError = dependencies.reportError ?? ElMessage.error;
  const refreshing = ref(false);
  const initialLoading = ref(true);
  const overview = ref<AdminOverviewResponse | null>(null);
  let loadPromise: Promise<void> | null = null;

  const summaryCards = computed(() => dashboardSummaryCards(overview.value));
  const pulseItems = computed(() => dashboardPulseItems(overview.value));
  const recentTasks = computed<AdminTaskListItem[]>(() => overview.value?.recentTasks ?? []);
  const recentFailures = computed<AdminTaskListItem[]>(() => overview.value?.recentFailures ?? []);
  const userQueues = computed(() => overview.value?.queue?.userQueues ?? []);
  const lastUpdatedLabel = computed(() => formatDashboardDateTime(overview.value?.generatedAt));

  function loadDashboard() {
    if (loadPromise) return loadPromise;
    refreshing.value = true;
    loadPromise = api.fetchOverview()
      .then((result) => { overview.value = result ?? null; })
      .catch((error) => {
        reportError(error instanceof Error ? error.message : "读取任务概览失败");
      })
      .finally(() => {
        refreshing.value = false;
        initialLoading.value = false;
        loadPromise = null;
      });
    return loadPromise;
  }

  if (dependencies.loadOnMount !== false) onMounted(loadDashboard);

  return {
    refreshing, initialLoading, overview, summaryCards, pulseItems, recentTasks,
    recentFailures, userQueues, lastUpdatedLabel, loadDashboard,
  };
}
