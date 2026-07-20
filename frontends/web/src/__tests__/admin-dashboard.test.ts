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
import type { AdminOverviewResponse } from "@/types";

const overview = {
  generatedAt: "2026-01-01",
  counts: {
    totalTasks: 8, completedTasks: 5, failedTasks: 1, runningTasks: 1, queuedTasks: 1,
    highRiskTasks: 1, averageProgress: 62, totalUsers: 3, activeUsers: 2, adminUsers: 1, disabledUsers: 1,
  },
  queue: { queueLength: 1, userQueues: [] },
  workers: { onlineCount: 2, items: [] },
  recentTasks: [], recentFailures: [], recentRunningTasks: [], recentTraceCount: 4, modelReady: true,
} as unknown as AdminOverviewResponse;

describe("admin dashboard", () => {
  it("builds summary and pulse view models", () => {
    expect(dashboardSummaryCards(overview)[0]).toMatchObject({ label: "用户", value: 3 });
    expect(dashboardPulseItems(overview)).toEqual(expect.arrayContaining([
      expect.objectContaining({ label: "在线 Worker", value: 2 }),
      expect.objectContaining({ label: "平均进度", value: "62%" }),
    ]));
    expect(normalizeDashboardPercent(105.4)).toBe(100);
    expect(dashboardStatusLabel("RENDERING")).toBe("渲染中");
    expect(dashboardStatusTagType("FAILED")).toBe("danger");
    expect(dashboardSeverityLabel()).toBe("待分析");
  });

  it("reports overview failures and finishes loading", async () => {
    const reportError = vi.fn();
    const state = useAdminDashboard({
      api: {
        fetchOverview: vi.fn(async () => { throw new Error("overview unavailable"); }),
      },
      reportError,
      loadOnMount: false,
    });

    await state.loadDashboard();

    expect(state.overview.value).toBeNull();
    expect(state.initialLoading.value).toBe(false);
    expect(state.refreshing.value).toBe(false);
    expect(reportError).toHaveBeenCalledWith("overview unavailable");
  });

  it("deduplicates concurrent refreshes", async () => {
    let resolveOverview!: (value: AdminOverviewResponse) => void;
    const fetchOverview = vi.fn(() => new Promise<AdminOverviewResponse>((resolve) => {
      resolveOverview = resolve;
    }));
    const state = useAdminDashboard({ api: { fetchOverview }, loadOnMount: false });

    const first = state.loadDashboard();
    const second = state.loadDashboard();

    expect(first).toBe(second);
    expect(fetchOverview).toHaveBeenCalledTimes(1);
    expect(state.refreshing.value).toBe(true);
    resolveOverview(overview);
    await first;
    expect(state.refreshing.value).toBe(false);
  });
});
