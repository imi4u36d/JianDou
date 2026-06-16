export type * from "./schema";

export interface OpenApiGenerationMetadata {
  readonly source: "placeholder";
  readonly description: string;
}

export const openApiGenerationMetadata: OpenApiGenerationMetadata = {
  source: "placeholder",
  description: "Reserved entrypoint for generated OpenAPI types and endpoint helpers."
};
