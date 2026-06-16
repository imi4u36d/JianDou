import { getJson } from "@/api/client";
import type { HealthResponse } from "@/types";

export async function fetchHealth() {
  return getJson<HealthResponse>("/health");
}
