import { createRouter, createWebHistory } from "vue-router";
import WorkspaceShell from "@/components/layout/WorkspaceShell.vue";
import GenerateView from "@/views/GenerateView.vue";
import HomeView from "@/views/HomeView.vue";
import TasksDashboardView from "@/views/TasksDashboardView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: WorkspaceShell,
      children: [
        {
          path: "",
          name: "home",
          component: HomeView,
        },
        {
          path: "generate",
          name: "generate",
          component: GenerateView,
        },
        {
          path: "tasks",
          name: "tasks",
          component: TasksDashboardView,
        },
      ],
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/",
    },
  ],
});

export default router;
