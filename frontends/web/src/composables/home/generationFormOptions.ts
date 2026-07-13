import type {
  CreateGenerationTaskRequest,
  GenerationImageSizeOption,
  GenerationTextAnalysisModelInfo,
} from "@/types";

export type ModeValue = "video" | "image" | "character_sheet";
export type AspectRatioValue = "16:9" | "9:16";
export type RatioOptionValue = "智能" | "1:1" | "21:9" | "16:9" | "3:2" | "4:3" | "3:4" | "2:3" | "9:16" | "9:20";

export type WorkbenchForm = Omit<CreateGenerationTaskRequest, "aspectRatio"> & {
  aspectRatio: RatioOptionValue;
  imageSize?: string | null;
};

export interface ModeOption {
  value: ModeValue;
  kind: "video" | "image";
  label: string;
  description: string;
  iconName: "video" | "image" | "character";
}

export const modeOptions: ModeOption[] = [
  {
    value: "image",
    kind: "image",
    label: "图片",
    description: "使用 OpenAI 图片模型生成或参考图再创作",
    iconName: "image",
  },
  {
    value: "video",
    kind: "video",
    label: "视频",
    description: "创建阶段化视频任务",
    iconName: "video",
  },
];

export const ratioDisplayOrder: RatioOptionValue[] = ["智能", "21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16", "9:20"];
const sizeRatioCandidates: RatioOptionValue[] = ["21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16", "9:20"];

export const videoOutputCountOptions = [1, 2, 3, 4, 6, 8, 10, 12];
export const imageOutputCountOptions = [1, 2, 3, 4];

export function normalizeModelName(value: unknown) {
  return String(value ?? "").trim().toLowerCase().replace(/[\s._-]/g, "");
}

export function normalizeSizeValue(value: unknown) {
  return String(value ?? "").trim().toLowerCase().replace(/\*/g, "x");
}

export function parseSeed(value: unknown): number | null {
  const raw = String(value ?? "").trim();
  if (!raw) return null;
  const numeric = Number(raw);
  if (!Number.isFinite(numeric) || !Number.isInteger(numeric) || numeric < 0) return null;
  return Math.trunc(numeric);
}

export function createRandomSeed() {
  if (typeof window !== "undefined" && window.crypto?.getRandomValues) {
    const values = new Uint32Array(1);
    window.crypto.getRandomValues(values);
    return Math.max(1, values[0] % 2147483647);
  }
  return Math.max(1, Math.floor(Math.random() * 2147483647));
}

export function parseSize(item: { value: string; width?: number; height?: number }) {
  if (typeof item.width === "number" && typeof item.height === "number" && item.width > 0 && item.height > 0) {
    return { width: item.width, height: item.height };
  }
  const matched = String(item.value ?? "").match(/^(\d+)\s*[xX*]\s*(\d+)$/);
  if (!matched) return null;
  const width = Number(matched[1]);
  const height = Number(matched[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return null;
  return { width, height };
}

export function resolveVideoSizeRatio(item: { value: string; width?: number; height?: number }): AspectRatioValue | null {
  const parsed = parseSize(item);
  if (!parsed || parsed.width === parsed.height) return null;
  return parsed.width > parsed.height ? "16:9" : "9:16";
}

export function imageSizeMatchesRatio(item: GenerationImageSizeOption, ratio: string) {
  return ratio === "智能" || sizeRatioLabel(item) === ratio;
}

export function compareSizeByArea(a: { value: string; width?: number; height?: number }, b: { value: string; width?: number; height?: number }) {
  const aSize = parseSize(a);
  const bSize = parseSize(b);
  return (aSize ? aSize.width * aSize.height : 0) - (bSize ? bSize.width * bSize.height : 0);
}

export function sizeRatioLabel(item: { value: string; width?: number; height?: number }): RatioOptionValue | null {
  const parsed = parseSize(item);
  if (!parsed) return null;
  const actual = parsed.width / parsed.height;
  const best = sizeRatioCandidates
    .map((value) => {
      const target = ratioValue(value);
      return target ? { value, delta: Math.abs(actual - target) / target } : null;
    })
    .filter((item): item is { value: RatioOptionValue; delta: number } => Boolean(item))
    .sort((a, b) => a.delta - b.delta)[0];
  return best && best.delta <= 0.03 ? best.value : null;
}

export function ratioShape(value: RatioOptionValue) {
  return value === "智能" ? "1 / 1" : value.replace(":", " / ");
}

export function ratioValue(value: RatioOptionValue) {
  if (value === "智能") return null;
  const [width, height] = value.split(":").map(Number);
  if (!Number.isFinite(width) || !Number.isFinite(height) || height <= 0) return null;
  return width / height;
}

export function videoAspectRatio(value: RatioOptionValue): AspectRatioValue {
  return value === "9:16" ? "9:16" : "16:9";
}

export function imageQualityLabel(item: { value: string; label?: string | null; width?: number; height?: number }) {
  const label = String(item.label ?? "");
  if (/\b4K\b/i.test(label)) return "超清 4K";
  if (/\b2K\b/i.test(label)) return "高清 2K";
  if (/\b1K\b/i.test(label)) return "标准 1K";
  const size = parseSize(item);
  if (!size) return String(item.value ?? "");
  const longest = Math.max(size.width, size.height);
  if (longest >= 2800) return "超清 4K";
  if (longest >= 1800) return "高清 2K";
  return "标准 1K";
}

export function modelOptionDescription(model: { description?: string | null; provider?: string | null; family?: string | null; value: string }) {
  return model.description || model.provider || model.family || model.value;
}

export function formatCreditBalance(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, "");
}

export function isOpenAIModel(model: { value?: string | null; label?: string | null; provider?: string | null; family?: string | null; description?: string | null }) {
  const fields = [model.provider, model.family, model.value, model.label, model.description].map(normalizeModelName);
  return fields.some((value) => value.includes("openai") || value.startsWith("gpt") || value.includes("gptimage") || value.includes("dalle"));
}

export function resolveDefaultImageModel(models: GenerationTextAnalysisModelInfo[], current?: string | null) {
  const currentValue = String(current ?? "").trim();
  if (currentValue && models.some((item) => item.value === currentValue)) return currentValue;
  const gptModel = models.find((item) => [item.family, item.provider, item.value, item.label].map(normalizeModelName).some((value) => value.includes("gpt")));
  return gptModel?.value || models[0]?.value || null;
}
