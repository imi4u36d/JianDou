/**
 * 前端路由注册入口。
 */
import { createRouter, createWebHistory } from "vue-router";
import WorkspaceShell from "@/components/layout/WorkspaceShell.vue";

// ── Admin routes (lazy-loaded) ──
const AdminLoginView = () => import("@/admin/views/LoginView.vue");
const AdminForbiddenView = () => import("@/admin/views/ForbiddenView.vue");
const AdminLayout = () => import("@/admin/layouts/AdminLayout.vue");
const DashboardView = () => import("@/admin/views/DashboardView.vue");
const UserManagementView = () => import("@/admin/views/UserManagementView.vue");
const InviteManagementView = () => import("@/admin/views/InviteManagementView.vue");
const CreditManagementView = () => import("@/admin/views/CreditManagementView.vue");
const TaskManagementView = () => import("@/admin/views/TaskManagementView.vue");
const TaskDetailView = () => import("@/admin/views/TaskDetailView.vue");
const SystemView = () => import("@/admin/views/SystemView.vue");
import { ensureAuthSession, useAuthSessionState } from "@/auth/session";
import ActivateInviteView from "@/views/ActivateInviteView.vue";
import ForbiddenView from "@/views/ForbiddenView.vue";
import HomeView from "@/views/HomeView.vue";
import LoginView from "@/views/LoginView.vue";
import MaterialLibraryView from "@/views/MaterialLibraryView.vue";
import NewTaskView from "@/views/NewTaskView.vue";
import OfficialDocsView from "@/views/OfficialDocsView.vue";
import StageWorkflowView from "@/views/StageWorkflowView.vue";
import TasksView from "@/views/TasksView.vue";

function normalizeRedirectTarget(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return authState.isAdmin.value ? "/admin" : "/workspace";
  }
  return value;
}

const authState = useAuthSessionState();

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: {
        title: "登录",
        guestOnly: true
      }
    },
    {
      path: "/activate",
      name: "activate",
      component: ActivateInviteView,
      meta: {
        title: "激活邀请码",
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
      path: "/official",
      redirect: "/workspace"
    },
    {
      path: "/docs",
      name: "official-docs",
      component: OfficialDocsView,
      meta: {
        title: "使用文档"
      }
    },
    {
      path: "/",
      component: WorkspaceShell,
      children: [
        {
          path: "",
          redirect: "/workspace"
        },
        {
          path: "workspace",
          name: "workspace-home",
          component: HomeView,
          meta: {
            title: "工作台"
          }
        },
        {
          path: "generate",
          redirect: "/workspace"
        },
        {
          path: "tasks/new",
          name: "tasks-new",
          component: NewTaskView,
          meta: {
            title: "新建任务"
          }
        },
        {
          path: "workflows",
          name: "workflows",
          component: StageWorkflowView,
          meta: {
            title: "阶段工作流"
          }
        },
        {
          path: "workflows/:workflowId",
          name: "workflow-detail",
          component: StageWorkflowView,
          meta: {
            title: "阶段工作流"
          }
        },
        {
          path: "material-center",
          redirect: "/workspace"
        },
        {
          path: "materials",
          name: "materials",
          component: MaterialLibraryView,
          meta: {
            title: "素材库"
          }
        },
        {
          path: "tasks",
          name: "tasks",
          component: TasksView,
          meta: {
            title: "任务管理"
          }
        }
      ]
    },
    // ── Admin routes ──
    {
      path: "/admin/login",
      name: "admin-login",
      component: AdminLoginView,
      meta: {
        title: "管理员登录",
        guestOnly: true
      }
    },
    {
      path: "/admin/403",
      name: "admin-forbidden",
      component: AdminForbiddenView,
      meta: {
        title: "无权限访问"
      }
    },
    {
      path: "/admin",
      component: AdminLayout,
      meta: {
        requiresAdmin: true
      },
      children: [
        {
          path: "",
          name: "admin-dashboard",
          component: DashboardView,
          meta: {
            title: "首页概览"
          }
        },
        {
          path: "users",
          name: "admin-users",
          component: UserManagementView,
          meta: {
            title: "用户管理"
          }
        },
        {
          path: "invites",
          name: "admin-invites",
          component: InviteManagementView,
          meta: {
            title: "邀请码管理"
          }
        },
        {
          path: "credits",
          name: "admin-credits",
          component: CreditManagementView,
          meta: {
            title: "积分管理"
          }
        },
        {
          path: "tasks",
          name: "admin-tasks",
          component: TaskManagementView,
          meta: {
            title: "任务管理"
          }
        },
        {
          path: "tasks/:id",
          name: "admin-task-detail",
          component: TaskDetailView,
          meta: {
            title: "任务详情"
          }
        },
        {
          path: "system",
          name: "admin-system",
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
  const requiresSession = to.matched.some((record) => record.meta.requiresAuth || record.meta.requiresAdmin || record.meta.guestOnly);
  if (requiresSession) {
    await ensureAuthSession();
  }
  const isAuthenticated = authState.isAuthenticated.value;
  const isAdmin = authState.isAdmin.value;
  const guestOnly = to.matched.some((record) => record.meta.guestOnly);
  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth);
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin);
  if (guestOnly && isAuthenticated) {
    return normalizeRedirectTarget(to.query.redirect);
  }
  if (requiresAuth && !isAuthenticated) {
    return {
      path: "/login",
      query: {
        redirect: to.fullPath
      }
    };
  }
  if (requiresAdmin && !isAuthenticated) {
    return {
      path: "/admin/login",
      query: {
        redirect: to.fullPath
      }
    };
  }
  if (requiresAdmin && isAuthenticated && !isAdmin) {
    return {
      path: "/admin/403"
    };
  }
  return true;
});

router.afterEach((to) => {
  const title = typeof to.meta.title === "string" && to.meta.title.trim() ? to.meta.title : "煎豆";
  document.title = `${title} · 煎豆`;
});

export default router;
