import type { AdminOverviewResponse, AdminTaskListItem, TaskStatus } from "@/types";

export function dashboardSummaryCards(overview: AdminOverviewResponse | null) {
  const counts = overview?.counts;
  return [
    { label: "用户", value: counts?.totalUsers ?? 0, note: "全部账号", tone: "accent" },
    { label: "任务", value: counts?.totalTasks ?? 0, note: "总数", tone: "secondary" },
    { label: "成功", value: counts?.completedTasks ?? 0, note: "已完成", tone: "success" },
    { label: "失败", value: counts?.failedTasks ?? 0, note: "待排查", tone: "danger" },
    { label: "运行", value: counts?.runningTasks ?? 0, note: "执行中", tone: "warning" },
    { label: "排队", value: counts?.queuedTasks ?? 0, note: "等待中", tone: "neutral" },
  ];
}

export function dashboardPulseItems(overview: AdminOverviewResponse | null) {
  const counts = overview?.counts;
  return [
    { label: "活跃用户", value: counts?.activeUsers ?? 0, note: "可登录" },
    { label: "管理员", value: counts?.adminUsers ?? 0, note: "后台" },
    { label: "禁用账号", value: counts?.disabledUsers ?? 0, note: "已暂停" },
    { label: "在线 Worker", value: overview?.workers?.onlineCount ?? 0, note: "工作节点" },
    { label: "队列积压", value: overview?.queue?.queueLength ?? 0, note: "未开始" },
    { label: "高风险", value: counts?.highRiskTasks ?? 0, note: "需关注" },
    { label: "Trace", value: overview?.recentTraceCount ?? 0, note: "近期记录" },
    { label: "平均进度", value: `${counts?.averageProgress ?? 0}%`, note: "整体" },
  ];
}

export function formatDashboardDateTime(value?: string | null) {
  if (!value) return "未记录";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "未记录" : date.toLocaleString("zh-CN");
}

export function normalizeDashboardPercent(value?: number) {
  return typeof value === "number" && !Number.isNaN(value)
    ? Math.max(0, Math.min(100, Math.round(value)))
    : 0;
}

export function dashboardStatusLabel(status: TaskStatus) {
  return {
    PENDING: "排队中", PAUSED: "已暂停", ANALYZING: "分析中", PLANNING: "编排中",
    RENDERING: "渲染中", COMPLETED: "已完成", FAILED: "失败",
  }[status] ?? status;
}

export function dashboardStatusTagType(status: TaskStatus) {
  if (status === "COMPLETED") return "success" as const;
  if (status === "FAILED") return "danger" as const;
  if (["RENDERING", "ANALYZING", "PLANNING"].includes(status)) return "warning" as const;
  return "info" as const;
}

export function dashboardSeverityLabel(severity?: AdminTaskListItem["diagnosisSeverity"]) {
  const labels: Record<string, string> = {
    high: "高风险",
    medium: "中风险",
    low: "低风险",
    info: "正常",
  };
  return labels[severity ?? ""] ?? "待分析";
}

export function dashboardSeverityTagType(severity?: AdminTaskListItem["diagnosisSeverity"]) {
  if (severity === "high") return "danger" as const;
  if (severity === "medium") return "warning" as const;
  if (severity === "low") return "success" as const;
  return "info" as const;
}
