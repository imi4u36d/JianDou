import type { HealthResponse } from "@/types/health";

import { getJson } from "@/api/client";

export async function fetchHealth() {
  return getJson<HealthResponse>("/health");
}
