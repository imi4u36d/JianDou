/**
 * 统一任务列表项类型。
 * 所有创作均以任务形式管理。
 */
import type { TaskListItem } from "@/types";
import type { WorkflowSummary } from "@/types";

export type UnifiedListItemKind = "task" | "workflow";

/**
 * 统一列表项接口定义。
 */
export interface UnifiedListItem {
  id: string;
  kind: UnifiedListItemKind;
  title: string;
  status: string;
  progress: number;
  createdAt: string;
  updatedAt: string;
  aspectRatio?: string;
  thumbnailUrl?: string | null;
  currentStage?: string;
  executionMode?: string;
  autoPilotState?: string;
  task?: TaskListItem;
  workflow?: WorkflowSummary;
}

/**
 * 统一列表的筛选状态。
 */
export type UnifiedStatusFilter = "all" | "active" | "pending" | "completed" | "failed";
export type UnifiedSortMode = "updated_desc" | "created_desc" | "progress_desc" | "status_desc";
