import type { AdminInvite, AdminInviteActor, InviteStatus } from "@/types";

export function inviteSummaryCards(invites: AdminInvite[]) {
  const count = (status: InviteStatus) => invites.filter((invite) => invite.status === status).length;
  return [
    { label: "全部邀请码", value: invites.length, note: "总数" },
    { label: "可使用", value: count("UNUSED"), note: "12 小时" },
    { label: "已使用", value: count("USED"), note: "已激活" },
    { label: "已过期", value: count("EXPIRED"), note: "过期" },
  ];
}

export function formatInviteDateTime(value?: string | null) {
  if (!value) return "未记录";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "未记录" : date.toLocaleString("zh-CN");
}

export function inviteActorLabel(actor?: AdminInviteActor | null) {
  return actor?.username || "-";
}

export function inviteStatusLabel(status: InviteStatus) {
  return { UNUSED: "可使用", USED: "已使用", REVOKED: "已撤销", EXPIRED: "已过期" }[status] ?? status;
}

export function inviteStatusTagType(status: InviteStatus) {
  return { UNUSED: "success", USED: "info", REVOKED: "warning", EXPIRED: "danger" }[status] ?? "info";
}
