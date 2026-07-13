export interface AppSelectOption {
  label: string;
  value: unknown;
  description?: string;
  disabled?: boolean;
}

export type AppSelectVariant = "field" | "toolbar" | "admin";

export interface AppSelectProps {
  modelValue: unknown;
  options: AppSelectOption[];
  placeholder?: string;
  disabled?: boolean;
  compact?: boolean;
  variant?: AppSelectVariant;
  prefix?: string;
}
