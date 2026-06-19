import type { TaskShowcaseItem, TaskShowcaseModels } from "@/types";

export interface ShowcaseVisualMeta {
  accent: string;
  scene: string;
}

export interface ShowcaseModelNode {
  key: keyof TaskShowcaseModels;
  badge: string;
  name: string;
  vendor: string;
  className: string;
}

const SHOWCASE_VISUALS: ShowcaseVisualMeta[] = [
  {
    accent: "rgba(164, 83, 255, 0.42)",
    scene: "linear-gradient(180deg, rgba(35,40,52,0.78), rgba(6,8,13,0.92)), radial-gradient(circle at 50% 40%, rgba(207,180,140,0.48), transparent 56%)",
  },
  {
    accent: "rgba(78, 219, 255, 0.38)",
    scene: "linear-gradient(180deg, rgba(47,31,38,0.7), rgba(9,8,12,0.94)), radial-gradient(circle at 54% 38%, rgba(230,176,128,0.42), transparent 48%)",
  },
  {
    accent: "rgba(125, 169, 255, 0.38)",
    scene: "linear-gradient(180deg, rgba(18,35,43,0.78), rgba(7,10,14,0.95)), radial-gradient(circle at 52% 38%, rgba(128,184,164,0.4), transparent 48%)",
  },
  {
    accent: "rgba(255, 194, 118, 0.36)",
    scene: "linear-gradient(180deg, rgba(42,35,29,0.78), rgba(11,9,8,0.94)), radial-gradient(circle at 46% 32%, rgba(238,196,141,0.42), transparent 48%)",
  },
];

const MODEL_NODE_DEFS: Array<{
  key: keyof TaskShowcaseModels;
  badge: string;
  name: string;
  className: string;
}> = [
  { key: "textAnalysisModel", badge: "文", name: "文本模型", className: "showcase-node-openai" },
  { key: "imageModel", badge: "帧", name: "关键帧模型", className: "showcase-node-frame" },
  { key: "videoModel", badge: "影", name: "视频模型", className: "showcase-node-sora" },
];

function hashValue(value: string) {
  let hash = 0;
  for (const char of value) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return hash;
}

/**
 * 返回案例视觉占位方案。
 */
export function resolveShowcaseVisual(item: Pick<TaskShowcaseItem, "id" | "title">, offset = 0) {
  const seed = item.id || item.title || `${offset}`;
  return SHOWCASE_VISUALS[(hashValue(seed) + offset) % SHOWCASE_VISUALS.length];
}

/**
 * 返回案例主模型名称。
 */
export function selectShowcasePrimaryModel(item: TaskShowcaseItem) {
  return item.models?.videoModel
    || item.models?.imageModel
    || item.models?.textAnalysisModel
    || "";
}

/**
 * 格式化案例时长。
 */
export function formatShowcaseDuration(item: Pick<TaskShowcaseItem, "minDurationSeconds" | "maxDurationSeconds">) {
  const min = Number(item.minDurationSeconds ?? 0);
  const max = Number(item.maxDurationSeconds ?? 0);
  if (min > 0 && max > 0 && min !== max) {
    return `${min}-${max}s`;
  }
  const seconds = Math.max(min, max);
  return seconds > 0 ? `${seconds}s` : "未设置";
}

/**
 * 格式化案例评分。
 */
export function formatShowcaseRatingLabel(effectRating?: number | null) {
  return typeof effectRating === "number" && Number.isFinite(effectRating)
    ? `★ ${effectRating.toFixed(1)}`
    : "未评分";
}

/**
 * 格式化案例摘要信息。
 */
export function formatShowcaseTimeMeta(item: TaskShowcaseItem) {
  return [
    item.aspectRatio || "",
    formatShowcaseDuration(item),
    selectShowcasePrimaryModel(item),
  ].filter(Boolean).join(" · ");
}

/**
 * 聚合真实案例中实际使用的模型。
 */
export function collectShowcaseModelNodes(items: TaskShowcaseItem[]) {
  return MODEL_NODE_DEFS.map((definition) => {
    const counts = new Map<string, number>();
    for (const item of items) {
      const modelName = item.models?.[definition.key];
      if (typeof modelName !== "string" || !modelName.trim()) {
        continue;
      }
      counts.set(modelName, (counts.get(modelName) ?? 0) + 1);
    }
    let selectedModel = "";
    let selectedCount = 0;
    counts.forEach((count, name) => {
      if (count > selectedCount) {
        selectedModel = name;
        selectedCount = count;
      }
    });
    if (!selectedModel) {
      return null;
    }
    return {
      key: definition.key,
      badge: definition.badge,
      name: definition.name,
      vendor: selectedCount > 1 ? `${selectedModel} · ${selectedCount}条` : selectedModel,
      className: definition.className,
    } satisfies ShowcaseModelNode;
  }).filter((item): item is ShowcaseModelNode => Boolean(item));
}
