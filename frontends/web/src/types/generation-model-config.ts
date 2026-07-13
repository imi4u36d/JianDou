export interface AdminModelConfigSummary {
  providerCount: number;
  vendorCount: number;
  modelCount: number;
  readyModelCount: number;
  readyTextModelCount: number;
  readyVisionModelCount: number;
  readyImageModelCount: number;
  readyVideoModelCount: number;
}

export interface AdminModelConfigDefaults {
  aspectRatio: string;
  imageSize: string;
  videoSize: string;
  videoDurationSeconds: number;
  timeoutSeconds: number;
  temperature: number;
  maxTokens: number;
}

export interface AdminModelConfigProviderItem {
  key: string;
  provider: string;
  vendor: string;
  kinds: string[];
  baseUrl: string;
  taskBaseUrl: string;
  endpointHost: string;
  taskEndpointHost: string;
  apiKeyConfigured: boolean;
  baseUrlConfigured: boolean;
  taskBaseUrlConfigured: boolean;
  extras: Record<string, string>;
  modelNames: string[];
}

export interface AdminModelConfigModelItem {
  name: string;
  label: string;
  kind: string;
  provider: string;
  vendor: string;
  family: string;
  description: string;
  supportsSeed: boolean;
  supportsResponsesApi: boolean;
  prefersChatCompletionsForVision?: boolean;
  generationMode: string;
  supportedSizes: string[];
  supportedDurations: number[];
  ready: boolean;
  configSource: string;
  endpointHost: string;
  taskEndpointHost: string;
  issues: string[];
}

export interface AdminModelConfigResponse {
  configSource: string;
  summary: AdminModelConfigSummary;
  defaults: AdminModelConfigDefaults;
  providers: AdminModelConfigProviderItem[];
  models: AdminModelConfigModelItem[];
  configErrors: string[];
}

export interface AdminModelConfigProviderKeyInput { key: string; apiKey: string; }
export interface AdminModelConfigKeyUpdateRequest { providers: AdminModelConfigProviderKeyInput[]; }
export interface AdminModelConfigValidationResponse { valid: boolean; snapshot: AdminModelConfigResponse; }
