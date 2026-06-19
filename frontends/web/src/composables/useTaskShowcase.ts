import { onMounted, ref } from "vue";
import { fetchTaskShowcase } from "@/api/showcase";
import type { TaskShowcaseItem } from "@/types";

/**
 * 公开案例展示数据加载。
 */
export function useTaskShowcase() {
  const items = ref<TaskShowcaseItem[]>([]);
  const loading = ref(true);
  const errorMessage = ref("");
  const generatedAt = ref("");
  const totalCompletedTasks = ref(0);

  async function loadShowcase() {
    loading.value = true;
    errorMessage.value = "";
    try {
      const response = await fetchTaskShowcase();
      items.value = Array.isArray(response.items) ? response.items : [];
      generatedAt.value = response.generatedAt ?? "";
      totalCompletedTasks.value = Number.isFinite(response.totalCompletedTasks) ? response.totalCompletedTasks : 0;
    } catch (error) {
      items.value = [];
      generatedAt.value = "";
      totalCompletedTasks.value = 0;
      errorMessage.value = error instanceof Error ? error.message : "真实案例加载失败";
    } finally {
      loading.value = false;
    }
  }

  onMounted(() => {
    void loadShowcase();
  });

  return {
    items,
    loading,
    errorMessage,
    generatedAt,
    totalCompletedTasks,
    loadShowcase,
  };
}
