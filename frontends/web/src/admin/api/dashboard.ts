import type { AdminOverviewResponse } from "@/types/admin";

import { getJson } from "@/api/client";

export async function fetchAdminOverview() {
  return getJson<AdminOverviewResponse>("/admin/overview");
}
