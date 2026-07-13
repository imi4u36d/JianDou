import type { TaskShowcaseResponse } from "@/types/tasks";

import { getJson } from "./client";

/** 获取官网与工作台共用的真实案例展示。 */
export function fetchTaskShowcase() {
  return getJson<TaskShowcaseResponse>("/tasks/showcase");
}
