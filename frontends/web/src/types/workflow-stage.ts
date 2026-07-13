import type { MaterialAssetLibraryItem } from "./workflow-material";

export type WorkflowStageType = "storyboard" | "keyframe" | "video" | "joined" | "material_center";

export interface RateStageVersionRequest {
  effectRating: number;
  effectRatingNote?: string | null;
}

export interface WorkflowMetadataSummary {
  taskId?: string | null;
  sourceAssetId?: string | null;
  originWorkflowId?: string | null;
  originStageType?: string | null;
  originClipIndex?: number | null;
  originVersionNo?: number | null;
  scriptMarkdown?: string | null;
}

export interface WorkflowStageInputSummary {
  seed?: number | string | null;
  clipIndex?: number | null;
  frameRole?: string | null;
  generationMode?: string | null;
  variantKind?: string | null;
  characterName?: string | null;
  characterDefinition?: string | null;
  characterAppearance?: string | null;
  storyboardVersionId?: string | null;
  imagePrompt?: string | null;
}

export interface WorkflowFrameFailureSummary {
  frameRole?: string | null;
  errorMessage?: string | null;
}

export interface WorkflowStageOutputSummary {
  scriptMarkdown?: string | null;
  previewText?: string | null;
  width?: number | string | null;
  height?: number | string | null;
  startFrameUrl?: string | null;
  firstFrameUrl?: string | null;
  endFrameUrl?: string | null;
  lastFrameUrl?: string | null;
  fileUrl?: string | null;
  sheetUrl?: string | null;
  previewUrl?: string | null;
  frontViewUrl?: string | null;
  frontImageUrl?: string | null;
  frontUrl?: string | null;
  sideViewUrl?: string | null;
  sideImageUrl?: string | null;
  sideUrl?: string | null;
  profileViewUrl?: string | null;
  backViewUrl?: string | null;
  backImageUrl?: string | null;
  backUrl?: string | null;
  threeViewUrls?: string[] | null;
  viewUrls?: string[] | null;
  sheetUrls?: string[] | null;
  images?: string[] | null;
  selectedFirstFrame?: boolean | null;
  selectedLastFrame?: boolean | null;
  frameFailures?: WorkflowFrameFailureSummary[] | null;
  taskId?: string | null;
  taskStatus?: string | null;
  error?: string | null;
  taskMessage?: string | null;
  remoteSourceUrl?: string | null;
  characterName?: string | null;
  characterDefinition?: string | null;
  characterAppearance?: string | null;
}

export interface WorkflowModelCallSummary {
  runId?: string | null;
  requestId?: string | null;
  provider?: string | null;
  modelName?: string | null;
}

export interface StageVersion {
  id: string;
  stageType: Exclude<WorkflowStageType, "joined">;
  clipIndex: number;
  versionNo: number;
  title: string;
  status: string;
  selected: boolean;
  rating?: number | null;
  ratingNote?: string | null;
  ratedAt?: string | null;
  parentVersionId?: string | null;
  sourceMaterialAssetId?: string | null;
  materialAssetId?: string | null;
  previewUrl?: string | null;
  downloadUrl?: string | null;
  inputSummary?: WorkflowStageInputSummary | null;
  outputSummary?: WorkflowStageOutputSummary | null;
  modelCallSummary?: WorkflowModelCallSummary | null;
  createdAt: string;
  updatedAt: string;
  asset?: MaterialAssetLibraryItem | null;
}

export interface WorkflowCharacterSheet {
  id?: string | null;
  characterName?: string | null;
  name?: string | null;
  displayName?: string | null;
  appearanceSummary?: string | null;
  appearance?: string | null;
  characterIndex?: number | null;
  syntheticClipIndex?: number | null;
  clipIndex?: number | null;
  versions?: StageVersion[] | null;
  keyframeVersions?: StageVersion[] | null;
}

export interface WorkflowClipSlot {
  clipIndex: number;
  shotLabel?: string | null;
  scene?: string | null;
  durationHint?: string | null;
  targetDurationSeconds?: number | null;
  matchedCharacters?: WorkflowCharacterSheet[] | null;
  keyframeVersions: StageVersion[];
  videoVersions: StageVersion[];
}
