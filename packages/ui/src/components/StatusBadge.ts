const TONE_CLASS_MAP = {
  neutral: "jd-status-badge jd-status-badge--neutral",
  info: "jd-status-badge jd-status-badge--info",
  success: "jd-status-badge jd-status-badge--success",
  warning: "jd-status-badge jd-status-badge--warning",
  danger: "jd-status-badge jd-status-badge--danger"
} as const;

export type StatusBadgeTone = keyof typeof TONE_CLASS_MAP;

export interface StatusBadgeProps {
  label: string;
  tone?: StatusBadgeTone;
}

export interface StatusBadgeViewModel {
  label: string;
  tone: StatusBadgeTone;
  className: string;
}

export const STATUS_BADGE_TONES = Object.keys(TONE_CLASS_MAP) as StatusBadgeTone[];

export function createStatusBadgeViewModel(props: StatusBadgeProps): StatusBadgeViewModel {
  const tone = props.tone && TONE_CLASS_MAP[props.tone] ? props.tone : "neutral";
  return {
    label: props.label,
    tone,
    className: TONE_CLASS_MAP[tone]
  };
}

export const StatusBadge = {
  name: "StatusBadge",
  createViewModel: createStatusBadgeViewModel
} as const;
