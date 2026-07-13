import { describe, expect, it, vi } from "vitest";
import { useAdminDashboard } from "@/admin/composables/useAdminDashboard";
import {
  dashboardPulseItems,
  dashboardSeverityLabel,
  dashboardStatusLabel,
  dashboardStatusTagType,
  dashboardSummaryCards,
  normalizeDashboardPercent,
} from "@/admin/features/dashboard/dashboard-presenters";
import type { AdminOverviewResponse, AdminUser } from "@/types";

const user = {
  id: 1, username: "admin", role: "ADMIN", status: "ACTIVE",
  createdAt: "2026-01-01", updatedAt: "2026-01-01",
} as AdminUser;

const overview = {
  generatedAt: "2026-01-01",
  counts: { totalTasks: 8, completedTasks: 5, failedTasks: 1, runningTasks: 1, queuedTasks: 1, highRiskTasks: 1, averageProgress: 62 },
  queue: { queueLength: 1, userQueues: [] },
  workers: { onlineCount: 2, items: [] },
  recentTasks: [], recentFailures: [], recentRunningTasks: [], recentTraceCount: 4, modelReady: true,
} as unknown as AdminOverviewResponse;

describe("admin dashboard", () => {
  it("builds summary and pulse view models", () => {
    expect(dashboardSummaryCards(overview, [user])[0]).toMatchObject({ label: "用户", value: 1 });
    expect(dashboardPulseItems(overview, [user])).toEqual(expect.arrayContaining([
      expect.objectContaining({ label: "在线 Worker", value: 2 }),
      expect.objectContaining({ label: "平均进度", value: "62%" }),
    ]));
    expect(normalizeDashboardPercent(105.4)).toBe(100);
    expect(dashboardStatusLabel("RENDERING")).toBe("渲染中");
    expect(dashboardStatusTagType("FAILED")).toBe("danger");
    expect(dashboardSeverityLabel()).toBe("待分析");
  });

  it("keeps successful data when one dashboard request fails", async () => {
    const reportError = vi.fn();
    const state = useAdminDashboard({
      api: {
        fetchOverview: vi.fn(async () => overview),
        fetchUsers: vi.fn(async () => { throw new Error("users unavailable"); }),
      },
      reportError,
      loadOnMount: false,
    });

    await state.loadDashboard();

    expect(state.overview.value).toEqual(overview);
    expect(state.initialLoading.value).toBe(false);
    expect(state.refreshing.value).toBe(false);
    expect(reportError).toHaveBeenCalledWith("users unavailable");
  });
});
