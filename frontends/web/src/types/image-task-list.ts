import type { TaskListItem } from "@/types";

/**
 * 图片任务列表项接口定义。
 */
export interface ImageTaskListItem {
  id: string;
  title: string;
  status: string;
  progress: number;
  createdAt: string;
  updatedAt: string;
  startedAt?: string | null;
  finishedAt?: string | null;
  aspectRatio?: string;
  thumbnailUrl?: string | null;
  currentStage?: string;
  task?: TaskListItem;
}

/**
 * 图片任务列表的筛选状态。
 */
export type ImageTaskStatusFilter = "all" | "active" | "completed" | "failed";
