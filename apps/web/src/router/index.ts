/**
 * 前端路由注册入口。
 */
import { createRouter, createWebHistory } from "vue-router";
import WorkspaceShell from "@/components/layout/WorkspaceShell.vue";
import { ensureAuthSession, useAuthSessionState } from "@/auth/session";
import ActivateInviteView from "@/views/ActivateInviteView.vue";
import ForbiddenView from "@/views/ForbiddenView.vue";
import HomeView from "@/views/HomeView.vue";
import LoginView from "@/views/LoginView.vue";
import MaterialLibraryView from "@/views/MaterialLibraryView.vue";
import NewTaskView from "@/views/NewTaskView.vue";
import OfficialDocsView from "@/views/OfficialDocsView.vue";
import OfficialSiteView from "@/views/OfficialSiteView.vue";
import SettingsView from "@/views/SettingsView.vue";
import StageWorkflowView from "@/views/StageWorkflowView.vue";
import TasksView from "@/views/TasksView.vue";

function normalizeRedirectTarget(value: unknown) {
  if (typeof value !== "string" || !value.startsWith("/") || value.startsWith("//")) {
    return "/tasks";
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
      path: "/",
      name: "official-site",
      component: OfficialSiteView,
      meta: {
        title: "官网"
      }
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
      meta: {
        requiresAuth: true
      },
      children: [
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
          name: "generate",
          component: NewTaskView,
          meta: {
            title: "一键生成"
          }
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
        },
        {
          path: "settings",
          name: "settings",
          component: SettingsView,
          meta: {
            title: "设置"
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
  if (requiresAdmin && isAuthenticated && !isAdmin) {
    return {
      path: "/403"
    };
  }
  return true;
});

router.afterEach((to) => {
  const title = typeof to.meta.title === "string" && to.meta.title.trim() ? to.meta.title : "煎豆";
  document.title = `${title} · 煎豆`;
});

export default router;
