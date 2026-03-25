import { getJson } from "./client";
import type { HealthResponse } from "@/types";

export function fetchHealth() {
  return getJson<HealthResponse>("/health");
}
