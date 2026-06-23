/**
 * 统一任务列表项类型。
 * 将 Task 和 Workflow 归一化为同一接口，用于统一列表展示。
 */
import type { TaskListItem, WorkflowSummary } from "@/types";

/**
 * 统一列表项的种类。
 */
export type UnifiedItemKind = "task" | "workflow";

/**
 * 统一列表项接口定义。
 * task 和 workflow 字段保存原始数据，子组件可直接解包使用。
 */
export interface UnifiedListItem {
  kind: UnifiedItemKind;
  id: string;
  title: string;
  status: string;
  progress: number;
  createdAt: string;
  updatedAt: string;
  aspectRatio?: string;
  thumbnailUrl?: string | null;
  taskType?: string;
  currentStage?: string;
  task?: TaskListItem;
  workflow?: WorkflowSummary;
}

/**
 * 统一列表的筛选状态。
 */
export type UnifiedStatusFilter = "all" | "active" | "pending" | "completed" | "failed";
export type UnifiedKindFilter = "all" | "task" | "workflow";
export type UnifiedSortMode = "updated_desc" | "created_desc" | "progress_desc" | "status_desc";
