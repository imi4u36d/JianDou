/**
 * 健康检查相关 API 请求封装。
 */
import { getJson } from "./client";
import type { HealthResponse } from "@/types";

/**
 * 获取健康检查。
 */
export function fetchHealth() {
  return getJson<HealthResponse>("/health");
}
