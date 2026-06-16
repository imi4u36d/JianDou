import { createRouter, createWebHistory } from "vue-router";
import { ensureAuthSession, useAuthSessionState } from "@/auth/session";
import AdminLayout from "@/layouts/AdminLayout.vue";
import CreditManagementView from "@/views/CreditManagementView.vue";
import DashboardView from "@/views/DashboardView.vue";
import ForbiddenView from "@/views/ForbiddenView.vue";
import InviteManagementView from "@/views/InviteManagementView.vue";
import LoginView from "@/views/LoginView.vue";
import SystemView from "@/views/SystemView.vue";
import TaskDetailView from "@/views/TaskDetailView.vue";
import TaskManagementView from "@/views/TaskManagementView.vue";
import UserManagementView from "@/views/UserManagementView.vue";

function normalizeRedirectTarget(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
  }
  return value;
}

const authState = useAuthSessionState();

const router = createRouter({
  history: createWebHistory("/admin/"),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: {
        title: "管理员登录",
        guestOnly: true
      }
    },
    {
      path: "/403",
      name: "forbidden",
      component: ForbiddenView,
      meta: {
        title: "无权限访问"
      }
    },
    {
      path: "/",
      component: AdminLayout,
      meta: {
        requiresAdmin: true
      },
      children: [
        {
          path: "",
          name: "dashboard",
          component: DashboardView,
          meta: {
            title: "首页概览"
          }
        },
        {
          path: "users",
          name: "users",
          component: UserManagementView,
          meta: {
            title: "用户管理"
          }
        },
        {
          path: "invites",
          name: "invites",
          component: InviteManagementView,
          meta: {
            title: "邀请码管理"
          }
        },
        {
          path: "credits",
          name: "credits",
          component: CreditManagementView,
          meta: {
            title: "积分管理"
          }
        },
        {
          path: "tasks",
          name: "tasks",
          component: TaskManagementView,
          meta: {
            title: "任务管理"
          }
        },
        {
          path: "tasks/:id",
          name: "task-detail",
          component: TaskDetailView,
          meta: {
            title: "任务详情"
          }
        },
        {
          path: "system",
          name: "system",
          component: SystemView,
          meta: {
            title: "系统配置"
          }
        }
      ]
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/"
    }
  ]
});

router.beforeEach(async (to) => {
  const requiresSession = to.matched.some((record) => record.meta.requiresAdmin || record.meta.guestOnly);
  if (requiresSession) {
    await ensureAuthSession();
  }
  const isAuthenticated = authState.isAuthenticated.value;
  const isAdmin = authState.isAdmin.value;
  const guestOnly = to.matched.some((record) => record.meta.guestOnly);
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin);

  if (guestOnly && isAuthenticated && isAdmin) {
    return normalizeRedirectTarget(to.query.redirect);
  }
  if (guestOnly && isAuthenticated && !isAdmin) {
    return {
      path: "/403"
    };
  }
  if (requiresAdmin && !isAuthenticated) {
    return {
      path: "/login",
      query: {
        redirect: to.fullPath
      }
    };
  }
  if (requiresAdmin && !isAdmin) {
    return {
      path: "/403"
    };
  }
  return true;
});

router.afterEach((to) => {
  const title = typeof to.meta.title === "string" && to.meta.title.trim() ? to.meta.title : "JianDou 管理系统";
  document.title = `${title} · JianDou Admin`;
});

export default router;
