import { describe, expect, it, vi } from "vitest";
import { useInviteManagement } from "@/admin/composables/useInviteManagement";
import {
  inviteStatusLabel,
  inviteStatusTagType,
  inviteSummaryCards,
} from "@/admin/features/invites/invite-management-presenters";
import type { AdminInvite } from "@/types";

const invite = (status: AdminInvite["status"] = "UNUSED"): AdminInvite => ({
  id: 1,
  code: "CODE123",
  role: "USER",
  status,
  createdAt: "2026-01-01",
  updatedAt: "2026-01-01",
});

describe("invite management", () => {
  it("loads, creates, copies and revokes through injected ports", async () => {
    const fetch = vi.fn(async () => [invite()]);
    const create = vi.fn(async () => invite());
    const revoke = vi.fn(async () => invite("REVOKED"));
    const confirm = vi.fn(async () => undefined);
    const copy = vi.fn(async () => undefined);
    const message = { success: vi.fn(), info: vi.fn(), error: vi.fn() };
    const state = useInviteManagement({
      fetch, create, revoke, confirm, copy, message, loadOnMount: false,
    });

    await state.loadInvites();
    state.openCreateDialog();
    await state.submitCreate();
    await state.revokeInvite(state.invites.value[0]);

    expect(create).toHaveBeenCalledWith({ role: "USER" });
    expect(copy).toHaveBeenCalledWith("CODE123");
    expect(revoke).toHaveBeenCalledWith(1);
    expect(confirm).toHaveBeenCalledOnce();
    expect(state.submitting.value).toBe(false);
  });

  it("builds stable summary and status presentation", () => {
    expect(inviteSummaryCards([invite(), invite("USED")])[1].value).toBe(1);
    expect(inviteStatusLabel("REVOKED")).toBe("已撤销");
    expect(inviteStatusTagType("EXPIRED")).toBe("danger");
  });
});
