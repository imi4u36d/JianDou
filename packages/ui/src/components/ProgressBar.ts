function clampPercent(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

export interface ProgressBarProps {
  value?: number;
  label?: string;
  showText?: boolean;
}

export interface ProgressBarViewModel {
  value: number;
  label: string;
  showText: boolean;
  text: string;
  trackClassName: string;
  barClassName: string;
  style: {
    width: string;
  };
}

export function createProgressBarViewModel(props: ProgressBarProps = {}): ProgressBarViewModel {
  const value = clampPercent(props.value ?? 0);
  return {
    value,
    label: props.label || "progress",
    showText: props.showText ?? true,
    text: `${value}%`,
    trackClassName: "jd-progress__track",
    barClassName: "jd-progress__bar",
    style: {
      width: `${value}%`
    }
  };
}

export const ProgressBar = {
  name: "ProgressBar",
  rootClassName: "jd-progress",
  createViewModel: createProgressBarViewModel
} as const;
