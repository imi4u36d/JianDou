export function formatDateTime(value?: string | null): string {
  if (!value) {
    return "未记录";
  }
  const timestamp = new Date(value);
  return Number.isNaN(timestamp.getTime()) ? value : timestamp.toLocaleString();
}

export function formatModelKind(kind: string): string {
  const labels: Record<string, string> = {
    text: "文本",
    image: "图片",
    video: "视频",
  };
  return labels[kind.trim().toLowerCase()] ?? kind;
}
