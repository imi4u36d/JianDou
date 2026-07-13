import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchAdminTask, fetchAdminTasks } from "@/admin/features/tasks/services/taskService";
import { terminableTaskStatus } from "@/admin/features/tasks/task-management-presenters";
import type { AdminTaskListItem, AdminTaskSortMode, TaskDetail, TaskStatus } from "@/types";

export interface AdminTaskListDependencies {
  fetchTasks?: typeof fetchAdminTasks;
  fetchTask?: typeof fetchAdminTask;
  notifyError?: (message: string) => void;
}

export function useAdminTaskList(dependencies: AdminTaskListDependencies = {}) {
  const fetchTasks = dependencies.fetchTasks ?? fetchAdminTasks;
  const fetchTask = dependencies.fetchTask ?? fetchAdminTask;
  const notifyError = dependencies.notifyError ?? ((message: string) => ElMessage.error(message));
  const initialLoading = ref(true);
  const refreshing = ref(false);
  const tasks = ref<AdminTaskListItem[]>([]);
  const selectedTasks = ref<AdminTaskListItem[]>([]);
  const expandedTaskIds = ref<string[]>([]);
  const taskDetails = reactive<Record<string, TaskDetail | undefined>>({});
  const detailLoading = reactive<Record<string, boolean>>({});
  const detailErrors = reactive<Record<string, string>>({});
  const totalTasks = ref(0);
  const currentPage = ref(1);
  const pageSize = ref(20);
  const filters = reactive({
    q: "",
    status: "" as TaskStatus | "",
    sort: "created_desc" as AdminTaskSortMode,
  });
  const summaryCards = computed(() => [
    { label: "全部任务", value: totalTasks.value, note: "当前筛选" },
    { label: "当前页", value: tasks.value.length, note: `每页 ${pageSize.value}` },
  ]);
  const selectedTerminableIds = computed(() =>
    selectedTasks.value.filter((task) => terminableTaskStatus(task.status)).map((task) => task.id),
  );

  async function loadTaskDetail(taskId: string) {
    if (taskDetails[taskId] || detailLoading[taskId]) return;
    detailLoading[taskId] = true;
    detailErrors[taskId] = "";
    try {
      taskDetails[taskId] = await fetchTask(taskId);
    } catch (error) {
      detailErrors[taskId] = error instanceof Error ? error.message : "读取任务详情失败";
    } finally {
      detailLoading[taskId] = false;
    }
  }

  function clearTaskDetails() {
    expandedTaskIds.value = [];
    for (const collection of [taskDetails, detailLoading, detailErrors]) {
      Object.keys(collection).forEach((key) => delete collection[key]);
    }
  }

  function handleExpandChange(row: AdminTaskListItem, expandedRows: AdminTaskListItem[]) {
    expandedTaskIds.value = expandedRows.map((task) => task.id);
    if (expandedTaskIds.value.includes(row.id)) void loadTaskDetail(row.id);
  }

  function handleSelectionChange(selection: AdminTaskListItem[]) {
    selectedTasks.value = selection;
  }

  async function loadTasks() {
    refreshing.value = true;
    try {
      const result = await fetchTasks({
        ...filters,
        offset: (currentPage.value - 1) * pageSize.value,
        limit: pageSize.value,
      });
      clearTaskDetails();
      tasks.value = result?.items ?? [];
      totalTasks.value = result?.total ?? 0;
      selectedTasks.value = selectedTasks.value.filter((selected) =>
        tasks.value.some((task) => task.id === selected.id),
      );
    } catch (error) {
      notifyError(error instanceof Error ? error.message : "读取任务列表失败");
    } finally {
      initialLoading.value = false;
      refreshing.value = false;
    }
  }

  function handlePageChange() {
    void loadTasks();
  }

  function handleSizeChange() {
    currentPage.value = 1;
    void loadTasks();
  }

  function resetFilters() {
    Object.assign(filters, { q: "", status: "", sort: "created_desc" });
    currentPage.value = 1;
    void loadTasks();
  }

  return {
    initialLoading,
    refreshing,
    tasks,
    selectedTasks,
    expandedTaskIds,
    taskDetails,
    detailLoading,
    detailErrors,
    totalTasks,
    currentPage,
    pageSize,
    filters,
    summaryCards,
    selectedTerminableIds,
    loadTaskDetail,
    handleExpandChange,
    handleSelectionChange,
    loadTasks,
    handlePageChange,
    handleSizeChange,
    resetFilters,
  };
}
