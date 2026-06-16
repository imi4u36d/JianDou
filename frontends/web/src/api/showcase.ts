import { getJson } from "./client";
import type { TaskShowcaseResponse } from "@/types";

/**
 * 获取官网与工作台共用的真实案例展示。
 */
export function fetchTaskShowcase() {
  return getJson<TaskShowcaseResponse>("/tasks/showcase");
}
