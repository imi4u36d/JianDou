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
import StageWorkflowView from "@/views/StageWorkflowView.vue";
import UnifiedTaskView from "@/views/UnifiedTaskView.vue";

function normalizeRedirectTarget(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return authState.isAdmin.value ? "/admin" : "/tasks";
  }
  return value;
}

const authState = useAuthSessionState();

function isGuestOnlyRoute(to: { matched: Array<{ meta: Record<string, unknown> }> }) {
  return to.matched.some((record) => record.meta.guestOnly);
}

function routeRequiresAuth(to: { matched: Array<{ meta: Record<string, unknown> }> }) {
  if (!to.matched.length || isGuestOnlyRoute(to)) {
    return false;
  }
  return true;
}

function loginRedirectPath(path: string) {
  return path.startsWith("/admin") ? "/admin/login" : "/login";
}

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
        title: "激活",
        guestOnly: true
      }
    },
    {
      path: "/403",
      name: "forbidden",
      component: ForbiddenView,
      meta: {
        title: "无权限"
      }
    },
    {
      path: "/",
      component: WorkspaceShell,
      children: [
        {
          path: "",
          name: "home",
          component: HomeView,
          meta: {
            title: "首页"
          }
        },
        {
          path: "tasks",
          name: "tasks",
          component: UnifiedTaskView,
          meta: {
            title: "任务"
          }
        },
        {
          path: "materials",
          name: "materials",
          component: MaterialLibraryView,
          meta: {
            title: "素材"
          }
        },
        // ── 旧路由重定向（向后兼容） ──
        {
          path: "workspace",
          redirect: "/tasks"
        },
        {
          path: "videos",
          name: "videos",
          component: StageWorkflowView,
          meta: {
            title: "视频"
          }
        },
        {
          path: "videos/:workflowId",
          name: "video-detail",
          component: StageWorkflowView,
          meta: {
            title: "视频"
          }
        },
        {
          path: "workflows",
          redirect: "/videos"
        },
        {
          path: "workflows/:workflowId",
          redirect: (to) => ({
            path: `/videos/${String(to.params.workflowId || "")}`,
            query: to.query,
          })
        }
      ]
    },
    // ── Admin routes ──
    {
      path: "/admin/login",
      name: "admin-login",
      component: AdminLoginView,
      meta: {
        title: "管理端登录",
        guestOnly: true
      }
    },
    {
      path: "/admin/403",
      name: "admin-forbidden",
      component: AdminForbiddenView,
      meta: {
        title: "无权限"
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
            title: "概览"
          }
        },
        {
          path: "users",
          name: "admin-users",
          component: UserManagementView,
          meta: {
            title: "用户"
          }
        },
        {
          path: "invites",
          name: "admin-invites",
          component: InviteManagementView,
          meta: {
            title: "邀请码"
          }
        },
        {
          path: "credits",
          name: "admin-credits",
          component: CreditManagementView,
          meta: {
            title: "积分"
          }
        },
        {
          path: "tasks",
          name: "admin-tasks",
          component: TaskManagementView,
          meta: {
            title: "任务"
          }
        },
        {
          path: "tasks/:id",
          name: "admin-task-detail",
          component: TaskDetailView,
          meta: {
            title: "详情"
          }
        },
        {
          path: "system",
          name: "admin-system",
          component: SystemView,
          meta: {
            title: "系统"
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
  const requiresAuth = routeRequiresAuth(to);
  const requiresSession = requiresAuth || isGuestOnlyRoute(to);
  if (requiresSession) {
    await ensureAuthSession();
  }
  const isAuthenticated = authState.isAuthenticated.value;
  const isAdmin = authState.isAdmin.value;
  const guestOnly = isGuestOnlyRoute(to);
  const requiresAdmin = to.matched.some((record) => record.meta.requiresAdmin);
  if (guestOnly && isAuthenticated) {
    return normalizeRedirectTarget(to.query.redirect);
  }
  if (requiresAuth && !isAuthenticated) {
    return {
      path: loginRedirectPath(to.path),
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
