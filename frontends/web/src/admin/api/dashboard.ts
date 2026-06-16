import { getJson } from "@/api/client";
import type { AdminOverviewResponse } from "@/types";

export async function fetchAdminOverview() {
  return getJson<AdminOverviewResponse>("/admin/overview");
}
