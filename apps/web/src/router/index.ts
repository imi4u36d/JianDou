import { createRouter, createWebHistory } from "vue-router";
import AdminShell from "@/components/AdminShell.vue";
import AppShell from "@/components/AppShell.vue";
import TaskDetailView from "@/views/TaskDetailView.vue";
import TasksView from "@/views/TasksView.vue";
import TextGenerateView from "@/views/TextGenerateView.vue";
import TextScriptView from "@/views/TextScriptView.vue";
import NewTaskView from "@/views/NewTaskView.vue";
import StudioView from "@/views/StudioView.vue";
import AdminDashboardView from "@/views/admin/AdminDashboardView.vue";
import AdminSystemView from "@/views/admin/AdminSystemView.vue";
import AdminTaskDetailView from "@/views/admin/AdminTaskDetailView.vue";
import AdminTasksView from "@/views/admin/AdminTasksView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/tasks" },
    {
      path: "/",
      component: AppShell,
      children: [
        { path: "tasks", component: TasksView },
        { path: "tasks/new", component: NewTaskView },
        { path: "tasks/:id", component: TaskDetailView },
        { path: "studio", component: StudioView },
        { path: "generate", component: TextGenerateView },
        { path: "script", component: TextScriptView },
      ]
    },
    {
      path: "/admin",
      component: AdminShell,
      children: [
        { path: "", redirect: "/admin/dashboard" },
        { path: "dashboard", component: AdminDashboardView },
        { path: "tasks", component: AdminTasksView },
        { path: "tasks/:id", component: AdminTaskDetailView },
        { path: "system", component: AdminSystemView },
      ]
    }
  ]
});

export default router;
