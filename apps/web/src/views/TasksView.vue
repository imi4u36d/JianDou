<template>
  <section>
    <PageHeader
      eyebrow="Workspace"
      title="任务列表"
      description="查看历史任务、当前处理中任务和已经产出的素材。"
    >
      <RouterLink to="/tasks/new" class="rounded-full bg-orange-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-orange-400">创建新任务</RouterLink>
    </PageHeader>

    <div v-if="errorMessage" class="mb-4 rounded-[24px] border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-100">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p>{{ errorMessage }}</p>
        <button class="rounded-full border border-rose-300/30 px-4 py-2 text-xs font-medium text-rose-50 transition hover:bg-rose-500/20" @click="loadTasks">
          重新加载
        </button>
      </div>
    </div>

    <div v-if="loading" class="rounded-[24px] border border-white/10 bg-white/5 p-10 text-center text-slate-300">
      正在加载任务列表...
    </div>

    <div v-else-if="sortedTasks.length === 0" class="rounded-[24px] border border-dashed border-white/15 bg-white/5 p-10 text-center">
      <h3 class="text-lg font-medium text-white">还没有任务</h3>
      <p class="mt-2 text-sm text-slate-300">先上传一个视频，系统会根据你的参数生成短剧素材。</p>
    </div>

    <div v-else class="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <TaskCard v-for="task in sortedTasks" :key="task.id" :task="task" />
    </div>

    <p class="mt-4 text-xs text-slate-400">最近刷新：{{ lastLoadedAt }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { fetchTasks } from "@/api/tasks";
import type { TaskListItem } from "@/types";
import PageHeader from "@/components/PageHeader.vue";
import TaskCard from "@/components/TaskCard.vue";
import { usePolling } from "@/composables/usePolling";

const tasks = ref<TaskListItem[]>([]);
const loading = ref(true);
const errorMessage = ref("");
const lastLoadedAt = ref("尚未刷新");

const sortedTasks = computed(() =>
  [...tasks.value].sort((left, right) => {
    return new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime();
  })
);

async function loadTasks() {
  errorMessage.value = "";
  loading.value = tasks.value.length === 0;
  try {
    tasks.value = await fetchTasks();
    lastLoadedAt.value = new Date().toLocaleString();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "加载任务列表失败";
  } finally {
    loading.value = false;
  }
}

const { start } = usePolling(loadTasks, 4000);

onMounted(async () => {
  await start();
});
</script>
