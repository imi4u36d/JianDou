/**
 * 统一工作流列表项类型。
 * 所有创作均以工作流形式管理。
 */
import type { WorkflowSummary } from "@/types";

/**
 * 统一列表项接口定义。
 */
export interface UnifiedListItem {
  id: string;
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
  workflow?: WorkflowSummary;
}

/**
 * 统一列表的筛选状态。
 */
export type UnifiedStatusFilter = "all" | "active" | "pending" | "completed" | "failed";
export type UnifiedSortMode = "updated_desc" | "created_desc" | "progress_desc" | "status_desc";
