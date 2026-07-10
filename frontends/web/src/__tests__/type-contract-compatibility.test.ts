import { describe, expectTypeOf, it } from "vitest";

import type {
  AuthSession as BarrelAuthSession,
  CreditSummary as BarrelCreditSummary,
  HealthResponse as BarrelHealthResponse,
  PublicShareItem as BarrelPublicShareItem,
  UploadResponse as BarrelUploadResponse,
} from "@/types";
import type { AuthSession } from "@/types/auth";
import type { CreditSummary } from "@/types/credits";
import type { HealthResponse } from "@/types/health";
import type { PublicShareItem } from "@/types/public-shares";
import type { UploadResponse } from "@/types/uploads";

describe("type compatibility barrel", () => {
  it("preserves the domain contract shapes", () => {
    expectTypeOf<BarrelAuthSession>().toEqualTypeOf<AuthSession>();
    expectTypeOf<BarrelCreditSummary>().toEqualTypeOf<CreditSummary>();
    expectTypeOf<BarrelHealthResponse>().toEqualTypeOf<HealthResponse>();
    expectTypeOf<BarrelPublicShareItem>().toEqualTypeOf<PublicShareItem>();
    expectTypeOf<BarrelUploadResponse>().toEqualTypeOf<UploadResponse>();
  });
});
