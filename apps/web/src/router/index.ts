import { createRouter, createWebHistory } from "vue-router";
import AppShell from "@/components/AppShell.vue";
import AdminShell from "@/components/AdminShell.vue";
import TasksView from "@/views/TasksView.vue";
import NewTaskView from "@/views/NewTaskView.vue";
import TaskDetailView from "@/views/TaskDetailView.vue";
import AdminDashboardView from "@/views/admin/AdminDashboardView.vue";
import AdminTasksView from "@/views/admin/AdminTasksView.vue";
import AdminTaskDetailView from "@/views/admin/AdminTaskDetailView.vue";
import AdminSystemView from "@/views/admin/AdminSystemView.vue";

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
        { path: "tasks/:id", component: TaskDetailView, props: true }
      ]
    },
    {
      path: "/admin",
      component: AdminShell,
      children: [
        { path: "", component: AdminDashboardView },
        { path: "tasks", component: AdminTasksView },
        { path: "tasks/:id", component: AdminTaskDetailView, props: true },
        { path: "system", component: AdminSystemView }
      ]
    }
  ]
});

export default router;
