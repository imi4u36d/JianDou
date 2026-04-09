import { createRouter, createWebHistory } from "vue-router";
import WorkspaceShell from "@/components/layout/WorkspaceShell.vue";
import HomeView from "@/views/HomeView.vue";
import NewTaskView from "@/views/NewTaskView.vue";
import TasksView from "@/views/TasksView.vue";

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
          component: NewTaskView,
        },
        {
          path: "tasks/new",
          name: "tasks-new",
          component: NewTaskView,
        },
        {
          path: "tasks",
          name: "tasks",
          component: TasksView,
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
