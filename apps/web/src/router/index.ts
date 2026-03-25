import { createRouter, createWebHistory } from "vue-router";
import TasksView from "@/views/TasksView.vue";
import NewTaskView from "@/views/NewTaskView.vue";
import TaskDetailView from "@/views/TaskDetailView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/tasks" },
    { path: "/tasks", component: TasksView },
    { path: "/tasks/new", component: NewTaskView },
    { path: "/tasks/:id", component: TaskDetailView, props: true }
  ]
});

export default router;

