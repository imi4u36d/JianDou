export type IconSize = "xs" | "sm" | "md" | "lg" | "xl" | "2xl";

export const iconSizeMap: Record<IconSize, number> = {
  xs: 14,
  sm: 16,
  md: 20,
  lg: 24,
  xl: 32,
  "2xl": 48,
};

export type IconName =
  // Navigation
  | "home"
  | "workflow"
  | "task"
  | "material"
  // Mode
  | "video"
  | "image"
  | "character"
  // Utility
  | "search"
  | "close"
  | "more"
  | "chevron-down"
  | "check"
  | "bell"
  | "upload"
  | "github"
  | "plus"
  | "refresh"
  | "edit"
  | "delete"
  | "download"
  | "settings"
  | "user"
  // Status
  | "success"
  | "error"
  | "warning"
  | "info"
  // Content type
  | "model"
  | "text"
  | "frame"
  | "duration"
  | "reference"
  | "tag"
  // State
  | "empty"
  | "loading";
