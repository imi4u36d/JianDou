import type { AppSelectOption } from "@/components/common/app-select";
import type { GenerationOptionsResponse } from "@/types";

type ModelOption = {
  value: string;
  label: string;
  provider?: string | null;
  vendor?: string | null;
  family?: string | null;
  description?: string | null;
};

export function toAspectRatioOptions(catalog: GenerationOptionsResponse | null): AppSelectOption[] {
  const ratios = catalog?.aspectRatios ?? [
    { label: "16:9", value: "16:9" },
    { label: "9:16", value: "9:16" },
  ];
  return ratios.map(({ label, value }) => ({ label, value }));
}

export function defaultTaskAspectRatio(
  options: AppSelectOption[],
  preferred?: string | null,
): string {
  const fallback = "16:9";
  const candidate = preferred || fallback;
  return options.some((item) => item.value === candidate) ? candidate : fallback;
}

function optionSearchText(item: ModelOption): string {
  return [item.value, item.label, item.provider, item.vendor, item.family, item.description]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function preferredModelValue(
  models: ModelOption[] | undefined,
  preferredKeyword: string,
): string {
  const items = models ?? [];
  const preferred = preferredKeyword.toLowerCase();
  return items.find((item) => optionSearchText(item).includes(preferred))?.value ?? items[0]?.value ?? "";
}

export function videoSizeAspectRatio(
  value?: string | null,
  width?: number,
  height?: number,
): string {
  const resolvedWidth = Number(width ?? 0);
  const resolvedHeight = Number(height ?? 0);
  if (resolvedWidth > 0 && resolvedHeight > 0) {
    return resolvedWidth > resolvedHeight ? "16:9" : "9:16";
  }
  const [rawWidth, rawHeight] = String(value ?? "").replace(/\*/g, "x").split("x");
  const parsedWidth = Number(rawWidth);
  const parsedHeight = Number(rawHeight);
  if (parsedWidth > 0 && parsedHeight > 0) {
    return parsedWidth > parsedHeight ? "16:9" : "9:16";
  }
  return "";
}

export function preferredVideoSizeValue(
  catalog: GenerationOptionsResponse,
  videoModel: string,
  aspectRatio: string,
): string | null {
  const selectedModel = videoModel.trim().toLowerCase();
  const available = catalog.videoSizes.filter((item) => {
    const itemAspectRatio = videoSizeAspectRatio(item.value, item.width, item.height);
    if (itemAspectRatio && itemAspectRatio !== aspectRatio) return false;
    if (!selectedModel || !item.supportedModels?.length) return true;
    return item.supportedModels.some((model) => model.trim().toLowerCase() === selectedModel);
  });
  return available.find((item) => item.value === catalog.defaultVideoSize)?.value
    ?? available[0]?.value
    ?? catalog.defaultVideoSize
    ?? null;
}
