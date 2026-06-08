import type { Component } from "vue";
import type { IconName } from "./types";

// Navigation
import IconHome from "./IconHome.vue";
import IconWorkflow from "./IconWorkflow.vue";
import IconTask from "./IconTask.vue";
import IconMaterial from "./IconMaterial.vue";

// Mode
import IconVideo from "./IconVideo.vue";
import IconImage from "./IconImage.vue";
import IconCharacter from "./IconCharacter.vue";

// Utility
import IconSearch from "./IconSearch.vue";
import IconClose from "./IconClose.vue";
import IconMore from "./IconMore.vue";
import IconChevronDown from "./IconChevronDown.vue";
import IconCheck from "./IconCheck.vue";
import IconBell from "./IconBell.vue";
import IconUpload from "./IconUpload.vue";
import IconGitHub from "./IconGitHub.vue";
import IconPlus from "./IconPlus.vue";
import IconRefresh from "./IconRefresh.vue";
import IconEdit from "./IconEdit.vue";
import IconDelete from "./IconDelete.vue";
import IconDownload from "./IconDownload.vue";
import IconSettings from "./IconSettings.vue";
import IconUser from "./IconUser.vue";

// Status
import IconSuccess from "./IconSuccess.vue";
import IconError from "./IconError.vue";
import IconWarning from "./IconWarning.vue";
import IconInfo from "./IconInfo.vue";

// Content type
import IconModel from "./IconModel.vue";
import IconText from "./IconText.vue";
import IconFrame from "./IconFrame.vue";
import IconDuration from "./IconDuration.vue";
import IconReference from "./IconReference.vue";
import IconTag from "./IconTag.vue";

// State
import IconEmpty from "./IconEmpty.vue";
import IconLoading from "./IconLoading.vue";

export { default as AppIcon } from "./AppIcon.vue";

export const iconComponentMap: Record<IconName, Component> = {
  // Navigation
  home: IconHome,
  workflow: IconWorkflow,
  task: IconTask,
  material: IconMaterial,
  // Mode
  video: IconVideo,
  image: IconImage,
  character: IconCharacter,
  // Utility
  search: IconSearch,
  close: IconClose,
  more: IconMore,
  "chevron-down": IconChevronDown,
  check: IconCheck,
  bell: IconBell,
  upload: IconUpload,
  github: IconGitHub,
  plus: IconPlus,
  refresh: IconRefresh,
  edit: IconEdit,
  delete: IconDelete,
  download: IconDownload,
  settings: IconSettings,
  user: IconUser,
  // Status
  success: IconSuccess,
  error: IconError,
  warning: IconWarning,
  info: IconInfo,
  // Content type
  model: IconModel,
  text: IconText,
  frame: IconFrame,
  duration: IconDuration,
  reference: IconReference,
  tag: IconTag,
  // State
  empty: IconEmpty,
  loading: IconLoading,
};

// Named exports for direct usage
export {
  IconHome,
  IconWorkflow,
  IconTask,
  IconMaterial,
  IconVideo,
  IconImage,
  IconCharacter,
  IconSearch,
  IconClose,
  IconMore,
  IconChevronDown,
  IconCheck,
  IconBell,
  IconUpload,
  IconGitHub,
  IconPlus,
  IconRefresh,
  IconEdit,
  IconDelete,
  IconDownload,
  IconSettings,
  IconUser,
  IconSuccess,
  IconError,
  IconWarning,
  IconInfo,
  IconModel,
  IconText,
  IconFrame,
  IconDuration,
  IconReference,
  IconTag,
  IconEmpty,
  IconLoading,
};

export type { IconName, IconSize } from "./types";
export { iconSizeMap } from "./types";
