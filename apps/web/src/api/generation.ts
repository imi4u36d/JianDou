import { getJson, postJson } from "./client";
import type {
  GenerationCallLogEntry,
  GenerateMediaRequest,
  GenerateMediaResponse,
  GenerationImageSizeOption,
  GenerationMediaKind,
  GenerationModelInfo,
  GenerationOptionsResponse,
  GenerationStylePresetOption,
  GenerationVersionInfo,
  GenerationTextAnalysisModelInfo,
  GenerationVideoDurationOption,
  GenerationVideoModelInfo,
  GenerationVideoSizeOption,
  ProbeTextAnalysisModelRequest,
  ProbeTextAnalysisModelResponse,
  VideoModelUsageItem,
  VideoModelUsageResponse,
} from "@/types";

type UnknownRecord = Record<string, unknown>;

const OPTIONS_ENDPOINT = "/generations/versions";
const IMAGE_GENERATE_ENDPOINT = "/generations/image";
const VIDEO_GENERATE_ENDPOINT = "/generations/video";
const TEXT_ANALYSIS_MODEL_PROBE_ENDPOINT = "/generations/text-analysis-model/probe";
const VIDEO_MODEL_USAGE_ENDPOINT = "/generations/video-model-usage";
const FALLBACK_VERSIONS = Array.from({ length: 10 }, (_, index) => index + 1);
const DEFAULT_IMAGE_SIZES: GenerationImageSizeOption[] = [
  { value: "768x768", label: "768 × 768", width: 768, height: 768 },
  { value: "1024x1024", label: "1024 × 1024", width: 1024, height: 1024 },
  { value: "1365x768", label: "1365 × 768", width: 1365, height: 768 },
];
const OFFICIAL_VIDEO_MODELS: GenerationVideoModelInfo[] = [
  {
    value: "wan2.6-i2v",
    label: "Wan 2.6 (图生视频)",
    provider: "aliyun-bailian",
    family: "wan",
    generationMode: "i2v",
    isDefault: true,
  },
  {
    value: "wan2.6-t2v",
    label: "Wan 2.6 (文生视频)",
    provider: "aliyun-bailian",
    family: "wan",
    generationMode: "t2v",
    aliases: ["wan2.6-t2v-plus", "wan2.6-t2v-turbo"],
  },
  {
    value: "wan2.6-t2v-us",
    label: "Wan 2.6 US",
    provider: "aliyun-bailian",
    family: "wan",
    generationMode: "t2v",
  },
  {
    value: "wan2.5-t2v-preview",
    label: "Wan 2.5 Preview",
    provider: "aliyun-bailian",
    family: "wan",
    generationMode: "t2v",
    aliases: ["wan2.5-t2v-plus", "wan2.5-t2v-turbo"],
  },
  {
    value: "wan2.2-t2v-plus",
    label: "Wan 2.2 Plus",
    provider: "aliyun-bailian",
    family: "wan",
    generationMode: "t2v",
    aliases: ["wan2.2-t2v", "wan2.2-t2v-preview"],
  },
  {
    value: "wanx2.1-t2v-turbo",
    label: "WanX 2.1 Turbo",
    provider: "aliyun-bailian",
    family: "wanx",
    generationMode: "t2v",
    aliases: ["wanx2.1-t2v"],
  },
  {
    value: "wanx2.1-t2v-plus",
    label: "WanX 2.1 Plus",
    provider: "aliyun-bailian",
    family: "wanx",
    generationMode: "t2v",
    aliases: ["wanx2.1-t2v-preview"],
  },
  {
    value: "qwen-vl",
    label: "阿里 Qwen-VL 工作流",
    provider: "aliyun-bailian",
    family: "qwen",
    generationMode: "vl",
    aliases: ["qwen-vl-plus-latest", "qwen-vl-max-latest", "qwen-vl-workflow"],
  },
  {
    value: "seeddance-1.5-pro",
    label: "SeedDance 1.5 Pro",
    provider: "volcengine",
    family: "seeddance",
    generationMode: "i2v",
    aliases: [
      "seeddance1.5pro",
      "seeddance-1-5-pro",
      "seed-dance-1.5-pro",
      "doubao-seedance-1-5-pro-251215",
    ],
  },
];
const DEFAULT_VIDEO_SIZES: GenerationVideoSizeOption[] = [
  { value: "1080x1920", label: "1080 × 1920", width: 1080, height: 1920 },
  { value: "1920x1080", label: "1920 × 1080", width: 1920, height: 1080 },
  { value: "1280x720", label: "1280 × 720", width: 1280, height: 720 },
];
const DEFAULT_VIDEO_DURATIONS: GenerationVideoDurationOption[] = [
  { value: 4, label: "4 秒" },
  { value: 6, label: "6 秒" },
  { value: 8, label: "8 秒" },
];
const OFFICIAL_TEXT_ANALYSIS_MODELS: GenerationTextAnalysisModelInfo[] = [
  {
    value: "gpt-5.4",
    label: "GPT-5.4",
    provider: "openai",
    family: "gpt",
    isDefault: true,
    aliases: ["gpt5.4", "gpt-5-4", "gpt-5.4-latest"],
  },
  {
    value: "qwen3.6-plus",
    label: "Qwen 3.6 Plus",
    provider: "qwen",
    family: "qwen",
    aliases: ["qwen3.6-plus", "qwen-max-latest", "qwen-max", "qwen-plus"],
  },
];
const DEFAULT_TEXT_ANALYSIS_MODELS = OFFICIAL_TEXT_ANALYSIS_MODELS.map((item) => ({ ...item }));
function asRecord(value: unknown): UnknownRecord | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as UnknownRecord;
}

function parseNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function parseVersionNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase();
    const candidate = normalized.startsWith("v") ? normalized.slice(1) : normalized;
    const parsed = Number(candidate);
    if (Number.isFinite(parsed)) {
      return parsed;
    }
  }
  return null;
}

function parseString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function parseMediaKind(value: unknown): GenerationMediaKind | null {
  const normalized = parseString(value).toLowerCase();
  if (normalized === "image" || normalized === "video") {
    return normalized;
  }
  return null;
}

function parseStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => parseString(item)).filter((item) => Boolean(item));
}

function parseNumberArray(value: unknown): number[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => parseNumber(item))
    .filter((item): item is number => item !== null)
    .map((item) => Math.trunc(item));
}

function normalizeOfficialVideoModelName(value: unknown): string {
  const raw = parseString(value).toLowerCase();
  if (!raw) {
    return "";
  }
  const aliasMap = new Map<string, string>([
    ["wan2.6-t2v-plus", "wan2.6-t2v"],
    ["wan2.6-t2v-turbo", "wan2.6-t2v"],
    ["wan2.5-t2v-plus", "wan2.5-t2v-preview"],
    ["wan2.5-t2v-turbo", "wan2.5-t2v-preview"],
    ["wan2.2-t2v", "wan2.2-t2v-plus"],
    ["wan2.2-t2v-preview", "wan2.2-t2v-plus"],
    ["wanx2.1-t2v", "wanx2.1-t2v-turbo"],
    ["wanx2.1-t2v-preview", "wanx2.1-t2v-plus"],
    ["qwen-vl-plus-latest", "qwen-vl"],
    ["qwen-vl-max-latest", "qwen-vl"],
    ["qwen-vl-workflow", "qwen-vl"],
    ["seeddance1.5pro", "seeddance-1.5-pro"],
    ["seeddance-1-5-pro", "seeddance-1.5-pro"],
    ["seed-dance-1.5-pro", "seeddance-1.5-pro"],
    ["doubao-seedance-1-5-pro-251215", "seeddance-1.5-pro"],
  ]);
  if (aliasMap.has(raw)) {
    return aliasMap.get(raw) ?? raw;
  }
  const direct = OFFICIAL_VIDEO_MODELS.find((item) => item.value.toLowerCase() === raw);
  if (direct) {
    return direct.value;
  }
  for (const model of OFFICIAL_VIDEO_MODELS) {
    if (model.aliases?.some((alias) => alias.toLowerCase() === raw)) {
      return model.value;
    }
  }
  return raw;
}

function normalizeOfficialTextAnalysisModelName(value: unknown): string {
  const raw = parseString(value).toLowerCase();
  if (!raw) {
    return "";
  }
  for (const model of OFFICIAL_TEXT_ANALYSIS_MODELS) {
    if (model.value.toLowerCase() === raw) {
      return model.value;
    }
    if (model.aliases?.some((alias) => alias.toLowerCase() === raw)) {
      return model.value;
    }
  }
  return raw;
}

function normalizeVideoModelOption(value: unknown): GenerationVideoModelInfo | null {
  const record = asRecord(value);
  const rawValue = record ? parseString(record.value ?? record.model ?? record.id ?? record.key ?? record.name ?? record.label) : parseString(value);
  if (!rawValue) {
    return null;
  }
  const canonical = normalizeOfficialVideoModelName(rawValue);
  const official = OFFICIAL_VIDEO_MODELS.find((item) => item.value === canonical);
  const description = record ? parseString(record.description) || undefined : undefined;
  const supportedSizes = record ? parseStringArray(record.supportedSizes ?? record.videoSizes ?? record.sizes) : [];
  const supportedDurations = record ? parseNumberArray(record.supportedDurations ?? record.videoDurations ?? record.durations) : [];
  const aliases = record ? parseStringArray(record.aliases ?? record.altNames ?? record.aliasValues) : [];
  const explicitLabel = record ? parseString(record.label ?? record.name) : "";
  return {
    value: official?.value ?? canonical,
    label: explicitLabel || official?.label || canonical,
    description: description ?? null,
    isDefault: Boolean(record?.isDefault) || Boolean(official?.isDefault),
    provider: parseString(record?.provider) || official?.provider || null,
    family: parseString(record?.family) || official?.family || null,
    generationMode:
      (parseString(record?.generationMode) as GenerationVideoModelInfo["generationMode"]) ||
      official?.generationMode ||
      null,
    supportedSizes: supportedSizes.length ? supportedSizes : official?.supportedSizes,
    supportedDurations: supportedDurations.length ? supportedDurations : official?.supportedDurations,
    aliases: aliases.length ? aliases : official?.aliases,
  };
}

function normalizeVideoModelOptions(value: unknown): GenerationVideoModelInfo[] {
  const rawItems = Array.isArray(value) ? value : [];
  if (!rawItems.length) {
    return [];
  }
  const normalized = new Map<string, GenerationVideoModelInfo>();
  const ordered: GenerationVideoModelInfo[] = [];
  for (const item of rawItems) {
    const model = normalizeVideoModelOption(item);
    if (!model || normalized.has(model.value)) {
      continue;
    }
    normalized.set(model.value, model);
    ordered.push(model);
  }
  return ordered;
}

function normalizeTextAnalysisModelOption(value: unknown): GenerationTextAnalysisModelInfo | null {
  const record = asRecord(value);
  const rawValue = record ? parseString(record.value ?? record.model ?? record.id ?? record.key ?? record.name ?? record.label) : parseString(value);
  if (!rawValue) {
    return null;
  }
  const canonical = normalizeOfficialTextAnalysisModelName(rawValue);
  const official = OFFICIAL_TEXT_ANALYSIS_MODELS.find((item) => item.value === canonical);
  const aliases = record ? parseStringArray(record.aliases ?? record.altNames ?? record.aliasValues) : [];
  const explicitLabel = record ? parseString(record.label ?? record.name) : "";
  return {
    value: official?.value ?? canonical,
    label: explicitLabel || official?.label || canonical,
    description: (record ? parseString(record.description) : "") || official?.description || null,
    isDefault: Boolean(record?.isDefault) || Boolean(official?.isDefault),
    provider: parseString(record?.provider) || official?.provider || null,
    family: parseString(record?.family) || official?.family || null,
    aliases: aliases.length ? aliases : official?.aliases,
  };
}

function normalizeTextAnalysisModelOptions(value: unknown): GenerationTextAnalysisModelInfo[] {
  const rawItems = Array.isArray(value) ? value : [];
  if (!rawItems.length) {
    return DEFAULT_TEXT_ANALYSIS_MODELS.map((item) => ({ ...item }));
  }
  const normalized = new Map<string, GenerationTextAnalysisModelInfo>();
  for (const item of rawItems) {
    const model = normalizeTextAnalysisModelOption(item);
    if (!model) {
      continue;
    }
    normalized.set(model.value, model);
  }
  const ordered: GenerationTextAnalysisModelInfo[] = [];
  for (const official of OFFICIAL_TEXT_ANALYSIS_MODELS) {
    const existing = normalized.get(official.value);
    if (existing) {
      ordered.push({
        ...official,
        ...existing,
        value: official.value,
        label: existing.label || official.label,
      });
      normalized.delete(official.value);
    } else {
      ordered.push({ ...official });
    }
  }
  for (const item of normalized.values()) {
    ordered.push(item);
  }
  return ordered;
}

function normalizeVideoModelUsage(raw: unknown): VideoModelUsageResponse {
  const record = asRecord(raw) ?? {};
  const sourceItems = Array.isArray(record.items) ? record.items : Array.isArray(raw) ? raw : [];
  const items = sourceItems
    .map((item) => {
      const row = asRecord(item);
      if (!row) {
        return null;
      }
      const model = normalizeOfficialVideoModelName(
        row.model ?? row.providerModel ?? row.videoModel ?? row.name ?? row.key
      );
      if (!model) {
        return null;
      }
      const used = parseNumber(row.used ?? row.usedAmount ?? row.consumed ?? row.usage);
      const remaining = parseNumber(row.remaining ?? row.left ?? row.balance ?? row.quotaRemaining);
      return {
        model,
        label: parseString(row.label) || null,
        used: used !== null ? used : 0,
        unit: parseString(row.unit ?? row.usedUnit) || null,
        remaining,
        remainingUnit: parseString(row.remainingUnit ?? row.balanceUnit) || null,
        remainingLabel: parseString(row.remainingLabel) || null,
        quota: parseNumber(row.quota ?? row.total ?? row.limit),
        usedDurationSeconds: parseNumber(row.usedDurationSeconds ?? row.used_duration_seconds),
        provider: parseString(row.provider) || null,
        source: parseString(row.source) || null,
        note: parseString(row.note) || null,
        updatedAt: parseString(row.updatedAt ?? row.updated_at) || null,
      } satisfies VideoModelUsageItem;
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);
  return {
    items,
    updatedAt: parseString(record.generatedAt ?? record.updatedAt ?? record.updated_at) || null,
  };
}

function normalizeVideoSizeOption(value: unknown): GenerationVideoSizeOption | null {
  const record = asRecord(value);
  const rawValue = record ? parseString(record.value ?? record.size ?? record.id ?? record.key ?? record.name ?? record.label) : parseString(value);
  if (!rawValue) {
    return null;
  }
  const width = record ? parseNumber(record.width) : null;
  const height = record ? parseNumber(record.height) : null;
  const supportedModels = record ? parseStringArray(record.supportedModels ?? record.models) : [];
  return {
    value: rawValue,
    label: record ? parseString(record.label ?? record.name) || rawValue : rawValue,
    width: width ? Math.trunc(width) : undefined,
    height: height ? Math.trunc(height) : undefined,
    supportedModels: supportedModels.length ? supportedModels.map((item) => normalizeOfficialVideoModelName(item) || item) : undefined,
  };
}

function normalizeVideoSizeOptions(value: unknown): GenerationVideoSizeOption[] {
  const rawItems = Array.isArray(value) ? value : [];
  if (!rawItems.length) {
    return DEFAULT_VIDEO_SIZES.map((item) => ({ ...item }));
  }
  const seen = new Set<string>();
  const result: GenerationVideoSizeOption[] = [];
  for (const item of rawItems) {
    const normalized = normalizeVideoSizeOption(item);
    if (!normalized || seen.has(normalized.value)) {
      continue;
    }
    seen.add(normalized.value);
    result.push(normalized);
  }
  return result.length ? result : DEFAULT_VIDEO_SIZES.map((item) => ({ ...item }));
}

function normalizeVersions(value: unknown): number[] {
  if (!Array.isArray(value)) {
    return FALLBACK_VERSIONS;
  }
  const versions = Array.from(
    new Set(
      value
        .map((item) => {
          if (typeof item === "number" || typeof item === "string") {
            return parseVersionNumber(item);
          }
          const itemRecord = asRecord(item);
          return parseVersionNumber(itemRecord?.version ?? itemRecord?.value ?? itemRecord?.id);
        })
        .filter((item): item is number => item !== null)
        .map((item) => Math.trunc(item))
        .filter((item) => item >= 1 && item <= 10)
    )
  ).sort((left, right) => left - right);
  return versions.length ? versions : FALLBACK_VERSIONS;
}

function normalizeVersionDetails(value: unknown): GenerationVersionInfo[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const details = value
    .map((item) => {
      const itemRecord = asRecord(item);
      if (!itemRecord) {
        return null;
      }
      const version = parseVersionNumber(itemRecord.version ?? itemRecord.value ?? itemRecord.id);
      if (!version) {
        return null;
      }
      const supportedKinds = Array.isArray(itemRecord.supportedKinds)
        ? itemRecord.supportedKinds
            .map((entry) => parseMediaKind(entry))
            .filter((entry): entry is GenerationMediaKind => entry !== null)
        : [];
      return {
        version: Math.trunc(version),
        label: parseString(itemRecord.label ?? itemRecord.name) || `v${Math.trunc(version)}`,
        isDefault: Boolean(itemRecord.isDefault) || undefined,
        supportedKinds: supportedKinds.length ? supportedKinds : undefined,
        description: parseString(itemRecord.description) || undefined,
      } satisfies GenerationVersionInfo;
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);
  return details.sort((left, right) => left.version - right.version);
}

function normalizeStylePresets(value: unknown): GenerationStylePresetOption[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => {
      if (typeof item === "string") {
        const key = item.trim();
        if (!key) {
          return null;
        }
        return {
          key,
          label: key,
        };
      }
      const itemRecord = asRecord(item);
      if (!itemRecord) {
        return null;
      }
      const key = parseString(itemRecord.key ?? itemRecord.value ?? itemRecord.id);
      if (!key) {
        return null;
      }
      const mediaKinds = Array.isArray(itemRecord.mediaKinds)
        ? itemRecord.mediaKinds
            .map((entry) => parseMediaKind(entry))
            .filter((entry): entry is GenerationMediaKind => entry !== null)
        : [];
      return {
        key,
        label: parseString(itemRecord.label ?? itemRecord.name) || key,
        description: parseString(itemRecord.description) || undefined,
        mediaKinds: mediaKinds.length ? mediaKinds : undefined,
      };
    })
    .filter((item): item is GenerationStylePresetOption => Boolean(item));
}

function normalizeImageSizes(value: unknown): GenerationImageSizeOption[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => {
      if (typeof item === "string") {
        const size = item.trim();
        if (!size) {
          return null;
        }
        return {
          value: size,
          label: size,
        };
      }
      const itemRecord = asRecord(item);
      if (!itemRecord) {
        return null;
      }
      const rawValue = parseString(itemRecord.value ?? itemRecord.size ?? itemRecord.id);
      const width = parseNumber(itemRecord.width);
      const height = parseNumber(itemRecord.height);
      const valueLabel = rawValue || (width && height ? `${Math.trunc(width)}x${Math.trunc(height)}` : "");
      if (!valueLabel) {
        return null;
      }
      return {
        value: valueLabel,
        label: parseString(itemRecord.label ?? itemRecord.name) || valueLabel,
        width: width ? Math.trunc(width) : undefined,
        height: height ? Math.trunc(height) : undefined,
      };
    })
    .filter((item): item is GenerationImageSizeOption => Boolean(item));
}

function normalizeVideoDurations(value: unknown): GenerationVideoDurationOption[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => {
      if (typeof item === "number" || typeof item === "string") {
        const parsedValue = parseNumber(item);
        if (!parsedValue || parsedValue <= 0) {
          return null;
        }
        return {
          value: Math.trunc(parsedValue),
          label: `${Math.trunc(parsedValue)} 秒`,
        };
      }
      const itemRecord = asRecord(item);
      if (!itemRecord) {
        return null;
      }
      const parsedValue = parseNumber(itemRecord.value ?? itemRecord.duration ?? itemRecord.seconds);
      if (!parsedValue || parsedValue <= 0) {
        return null;
      }
      return {
        value: Math.trunc(parsedValue),
        label: parseString(itemRecord.label ?? itemRecord.name) || `${Math.trunc(parsedValue)} 秒`,
        supportedModels: parseStringArray(itemRecord.supportedModels ?? itemRecord.models)
          .map((model) => normalizeOfficialVideoModelName(model) || model)
          .filter((model) => Boolean(model)),
      };
    })
    .filter((item): item is GenerationVideoDurationOption => Boolean(item))
    .sort((left, right) => left.value - right.value);
}

function normalizeGenerationOptions(raw: unknown): GenerationOptionsResponse {
  const record = asRecord(raw) ?? {};
  const defaults = asRecord(record.defaults) ?? {};
  const versionsSource = Array.isArray(raw) ? raw : (record.versions ?? record.availableVersions ?? record.versionOptions);
  const versionDetails = normalizeVersionDetails(versionsSource);
  const versions = normalizeVersions(versionsSource);
  const defaultFromVersions = Array.isArray(versionsSource)
    ? parseVersionNumber(
        asRecord(versionsSource.find((item) => {
          const info = asRecord(item);
          return Boolean(info?.isDefault === true || parseString(info?.isDefault).toLowerCase() === "true");
        }))?.version
      )
    : null;
  const stylePresets = normalizeStylePresets(record.stylePresets ?? record.presets ?? record.styles);
  const imageSizes =
    normalizeImageSizes(record.imageSizes ?? record.sizes ?? record.imageSizeOptions).length > 0
      ? normalizeImageSizes(record.imageSizes ?? record.sizes ?? record.imageSizeOptions)
      : DEFAULT_IMAGE_SIZES;
  const videoModels = normalizeVideoModelOptions(
    record.videoModels ?? record.videoModelOptions ?? record.models ?? record.videoModelsList
  );
  const defaultVideoModel = normalizeOfficialVideoModelName(
    defaults.videoModel ?? defaults.defaultVideoModel ?? record.defaultVideoModel ?? videoModels.find((item) => item.isDefault)?.value ?? videoModels[0]?.value
  );
  const textAnalysisModels = normalizeTextAnalysisModelOptions(
    record.textAnalysisModels ?? record.scriptModels ?? record.textModels ?? record.analysisModels
  );
  const defaultTextAnalysisModel = normalizeOfficialTextAnalysisModelName(
    defaults.textAnalysisModel ??
      defaults.defaultTextAnalysisModel ??
      record.defaultTextAnalysisModel ??
      textAnalysisModels.find((item) => item.isDefault)?.value ??
      textAnalysisModels[0]?.value
  );
  const videoSizes =
    normalizeVideoSizeOptions(record.videoSizes ?? record.videoSizeOptions ?? record.resolutions ?? record.videoResolutions).length > 0
      ? normalizeVideoSizeOptions(record.videoSizes ?? record.videoSizeOptions ?? record.resolutions ?? record.videoResolutions)
      : DEFAULT_VIDEO_SIZES.map((item) => ({ ...item }));
  const videoDurations =
    normalizeVideoDurations(record.videoDurations ?? record.durations ?? record.videoDurationOptions).length > 0
      ? normalizeVideoDurations(record.videoDurations ?? record.durations ?? record.videoDurationOptions)
      : DEFAULT_VIDEO_DURATIONS;
  const defaultVideoDurationSeconds = parseNumber(defaults.videoDurationSeconds ?? record.defaultVideoDurationSeconds);
  const defaultVideoSize =
    parseString(defaults.videoSize ?? defaults.defaultVideoSize ?? record.defaultVideoSize) ||
    videoSizes[0]?.value ||
    DEFAULT_VIDEO_SIZES[0]?.value;
  const defaultImageSize =
    parseString(defaults.imageSize ?? record.defaultImageSize) ||
    imageSizes[0]?.value ||
    DEFAULT_IMAGE_SIZES[1]?.value;

  return {
    versions,
    versionDetails: versionDetails.length ? versionDetails : undefined,
    defaultVersion: defaultFromVersions ? Math.trunc(defaultFromVersions) : (versions[0] ?? 1),
    stylePresets,
    imageSizes,
    videoModels,
    defaultVideoModel: defaultVideoModel || null,
    textAnalysisModels,
    defaultTextAnalysisModel: defaultTextAnalysisModel || null,
    videoSizes,
    videoDurations,
    defaultStylePreset: parseString(defaults.stylePreset ?? record.defaultStylePreset) || null,
    defaultImageSize: defaultImageSize || undefined,
    defaultVideoSize: defaultVideoSize || undefined,
    defaultVideoDurationSeconds: defaultVideoDurationSeconds ? Math.trunc(defaultVideoDurationSeconds) : undefined,
  };
}

function normalizeModelInfo(record: UnknownRecord, metadata: UnknownRecord): GenerationModelInfo | null {
  const source = parseString(record.source ?? metadata.source);
  const sourceModel = source.startsWith("remote:") ? source.slice("remote:".length) : "";
  const modelInfoRecord = asRecord(record.modelInfo ?? metadata.modelInfo) ?? {};
  const providerModel = parseString(
    modelInfoRecord.providerModel ??
      modelInfoRecord.textAnalysisModel ??
      modelInfoRecord.resolvedModel ??
      metadata.providerModel ??
      metadata.textAnalysisModel ??
      record.providerModel ??
      record.videoModel ??
      record.textAnalysisModel ??
      metadata.videoModel
  );
  const requestedModel = parseString(
    modelInfoRecord.requestedModel ??
      modelInfoRecord.selectedModel ??
      modelInfoRecord.textAnalysisModel ??
      metadata.requestedModel ??
      metadata.textAnalysisModel ??
      record.textAnalysisModel
  );
  const resolvedModel = parseString(
    modelInfoRecord.resolvedModel ??
      modelInfoRecord.modelName ??
      metadata.resolvedModel ??
      metadata.modelName ??
      record.modelName
  );
  let modelNameRaw: unknown = modelInfoRecord.modelName;
  if (!parseString(modelNameRaw)) {
    modelNameRaw = resolvedModel || providerModel || sourceModel || record.model || metadata.model;
  }

  const strategyVersion = parseVersionNumber(modelInfoRecord.strategyVersion ?? modelInfoRecord.version ?? metadata.version);
  const mediaKind = parseMediaKind(modelInfoRecord.mediaKind ?? record.kind ?? metadata.kind);
  const modelName = parseString(modelNameRaw);
  const provider = parseString(modelInfoRecord.provider ?? metadata.provider ?? record.provider);

  if (!modelName && !provider && !strategyVersion && !mediaKind) {
    return null;
  }

  return {
    provider: provider || null,
    modelName: modelName || null,
    providerModel: providerModel || null,
    requestedModel: requestedModel || null,
    resolvedModel: resolvedModel || modelName || null,
    textAnalysisModel: requestedModel || null,
    endpointHost: parseString(modelInfoRecord.endpointHost ?? metadata.endpointHost) || null,
    temperature: parseNumber(modelInfoRecord.temperature ?? metadata.temperature),
    maxTokens: parseNumber(modelInfoRecord.maxTokens ?? metadata.maxTokens),
    timeoutSeconds: parseNumber(modelInfoRecord.timeoutSeconds ?? metadata.timeoutSeconds),
    strategyVersion: strategyVersion ? Math.trunc(strategyVersion) : null,
    strategyVersionLabel: parseString(modelInfoRecord.strategyVersionLabel ?? metadata.profileName) || null,
    strategySummary: parseString(modelInfoRecord.strategySummary) || null,
    mediaKind,
  };
}

function normalizeCallChain(record: UnknownRecord, metadata: UnknownRecord): GenerationCallLogEntry[] {
  const rawChain = record.callChain ?? metadata.callChain;
  if (!Array.isArray(rawChain)) {
    return [];
  }
  const chain = rawChain
    .map((item) => {
      const itemRecord = asRecord(item);
      if (!itemRecord) {
        return null;
      }
      const timestamp = parseString(itemRecord.timestamp ?? itemRecord.at);
      const stage = parseString(itemRecord.stage);
      const event = parseString(itemRecord.event);
      const status = parseString(itemRecord.status);
      const message = parseString(itemRecord.message);
      if (!timestamp || !stage || !event || !status || !message) {
        return null;
      }
      const detailsRecord = asRecord(itemRecord.details);
      const entry: GenerationCallLogEntry = {
        timestamp,
        stage,
        event,
        status,
        message,
      };
      if (detailsRecord) {
        entry.details = detailsRecord;
      }
      return entry;
    })
    .filter((item): item is NonNullable<typeof item> => item !== null);
  return chain;
}

function normalizeGenerationResponse(raw: unknown, requestPayload: GenerateMediaRequest): GenerateMediaResponse {
  const record = asRecord(raw) ?? {};
  const output = asRecord(record.output) ?? record;
  const metadata = asRecord(record.metadata) ?? {};
  const id =
    parseString(record.id ?? record.generationId ?? record.jobId ?? output.id ?? output.generationId) ||
    `${Date.now()}`;
  const mediaKind =
    parseMediaKind(record.mediaKind ?? record.kind ?? record.type ?? output.mediaKind ?? output.kind) || requestPayload.mediaKind;
  const outputUrl = parseString(
    record.outputUrl ?? record.url ?? record.resultUrl ?? record.mediaUrl ?? output.outputUrl ?? output.url ?? output.resultUrl ?? output.mediaUrl
  );
  if (!outputUrl) {
    throw new Error("生成结果缺少输出地址。");
  }
  const version =
    parseVersionNumber(record.version ?? record.modelVersion ?? output.version ?? metadata.version) ?? requestPayload.version;
  const durationSeconds =
    parseNumber(record.durationSeconds ?? output.durationSeconds ?? metadata.durationSeconds) ?? null;
  const width = parseNumber(record.width ?? output.width ?? metadata.width) ?? null;
  const height = parseNumber(record.height ?? output.height ?? metadata.height) ?? null;
  const providerModel = parseString(
    record.providerModel ?? record.videoModel ?? output.providerModel ?? output.videoModel ?? metadata.providerModel ?? metadata.videoModel ?? requestPayload.providerModel
  );
  const modelInfo = normalizeModelInfo(record, metadata);
  const callChain = normalizeCallChain(record, metadata);

  return {
    id,
    mediaKind,
    prompt: parseString(record.prompt ?? output.prompt) || requestPayload.prompt,
    version: Math.trunc(version),
    outputUrl,
    thumbnailUrl: parseString(record.thumbnailUrl ?? record.thumbUrl ?? output.thumbnailUrl ?? output.thumbUrl) || null,
    stylePreset: parseString(record.stylePreset ?? output.stylePreset ?? metadata.stylePreset) || requestPayload.stylePreset || null,
    providerModel: providerModel || modelInfo?.providerModel || null,
    mimeType: parseString(record.mimeType ?? output.mimeType ?? metadata.mimeType) || null,
    width: width ? Math.trunc(width) : null,
    height: height ? Math.trunc(height) : null,
    durationSeconds,
    createdAt: parseString(record.createdAt ?? output.createdAt ?? metadata.createdAt) || null,
    modelInfo,
    callChain,
    metadata,
  };
}

function parseImageSize(size: string | undefined): { width: number; height: number } {
  const normalized = (size ?? "").trim();
  const match = normalized.match(/^(\d+)\s*[xX]\s*(\d+)$/);
  if (!match) {
    return { width: 1024, height: 1024 };
  }
  const width = Number(match[1]);
  const height = Number(match[2]);
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    return { width: 1024, height: 1024 };
  }
  return { width: Math.trunc(width), height: Math.trunc(height) };
}

function buildBackendPayload(payload: GenerateMediaRequest) {
  if (payload.mediaKind === "image") {
    const { width, height } = parseImageSize(payload.imageSize);
    return {
      prompt: payload.prompt,
      version: payload.version,
      kind: "image" as const,
      textAnalysisModel: payload.textAnalysisModel || undefined,
      width,
      height,
      stylePreset: payload.stylePreset || undefined,
    };
  }
  const { width, height } = parseImageSize(payload.videoSize || "1080x1920");
  return {
    prompt: payload.prompt,
    version: payload.version,
    kind: "video" as const,
    width,
    height,
    durationSeconds: payload.videoDurationSeconds,
    minDurationSeconds: payload.minDurationSeconds,
    maxDurationSeconds: payload.maxDurationSeconds,
    providerModel: payload.providerModel || undefined,
    textAnalysisModel: payload.textAnalysisModel || undefined,
    videoSize: payload.videoSize || undefined,
    stylePreset: payload.stylePreset || undefined,
  };
}

export async function fetchGenerationOptions() {
  const raw = await getJson<unknown>(OPTIONS_ENDPOINT);
  return normalizeGenerationOptions(raw);
}

export async function generateMediaFromText(payload: GenerateMediaRequest) {
  const backendPayload = buildBackendPayload(payload);
  const endpoint = payload.mediaKind === "image" ? IMAGE_GENERATE_ENDPOINT : VIDEO_GENERATE_ENDPOINT;
  const raw = await postJson<unknown>(endpoint, backendPayload);
  return normalizeGenerationResponse(raw, payload);
}

export async function probeTextAnalysisModel(payload: ProbeTextAnalysisModelRequest) {
  return postJson<ProbeTextAnalysisModelResponse>(TEXT_ANALYSIS_MODEL_PROBE_ENDPOINT, {
    textAnalysisModel: payload.textAnalysisModel?.trim() || undefined,
  });
}

export async function fetchVideoModelUsage() {
  const raw = await getJson<unknown>(VIDEO_MODEL_USAGE_ENDPOINT);
  return normalizeVideoModelUsage(raw);
}
