/**
 * 前端路由注册入口。
 */
import { createRouter, createWebHistory } from "vue-router";
import WorkspaceShell from "@/components/layout/WorkspaceShell.vue";
import HomeView from "@/views/HomeView.vue";
import NewTaskView from "@/views/NewTaskView.vue";
import SettingsView from "@/views/SettingsView.vue";
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
          meta: {
            title: "首页",
          },
        },
        {
          path: "generate",
          name: "generate",
          component: NewTaskView,
          meta: {
            title: "新建任务",
          },
        },
        {
          path: "tasks/new",
          name: "tasks-new",
          component: NewTaskView,
          meta: {
            title: "新建任务",
          },
        },
        {
          path: "tasks",
          name: "tasks",
          component: TasksView,
          meta: {
            title: "任务管理",
          },
        },
        {
          path: "settings",
          name: "settings",
          component: SettingsView,
          meta: {
            title: "设置",
          },
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
