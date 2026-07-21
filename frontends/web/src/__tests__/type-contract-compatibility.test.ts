import { describe, expectTypeOf, it } from "vitest";

import type {
  AuthSession as BarrelAuthSession,
  CreditSummary as BarrelCreditSummary,
  HealthResponse as BarrelHealthResponse,
  UploadResponse as BarrelUploadResponse,
} from "@/types";
import type { AuthSession } from "@/types/auth";
import type { CreditSummary } from "@/types/credits";
import type { HealthResponse } from "@/types/health";
import type { UploadResponse } from "@/types/uploads";

describe("type compatibility barrel", () => {
  it("preserves the domain contract shapes", () => {
    expectTypeOf<BarrelAuthSession>().toEqualTypeOf<AuthSession>();
    expectTypeOf<BarrelCreditSummary>().toEqualTypeOf<CreditSummary>();
    expectTypeOf<BarrelHealthResponse>().toEqualTypeOf<HealthResponse>();
    expectTypeOf<BarrelUploadResponse>().toEqualTypeOf<UploadResponse>();
  });
});
