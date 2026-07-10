/**
 * 健康检查相关 API 请求封装。
 */
import type { HealthResponse } from "@/types/health";

import { getJson } from "./client";

/** 获取健康检查。 */
export function fetchHealth() {
  return getJson<HealthResponse>("/health");
}
