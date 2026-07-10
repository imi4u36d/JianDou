import type {
  AuthSession as BarrelAuthSession,
  CreditSummary as BarrelCreditSummary,
  HealthResponse as BarrelHealthResponse,
} from "./index";
import type { AuthSession } from "./auth";
import type { CreditSummary } from "./credits";
import type { HealthResponse } from "./health";

type Equal<Left, Right> =
  (<Value>() => Value extends Left ? 1 : 2) extends
  (<Value>() => Value extends Right ? 1 : 2)
    ? true
    : false;
type Assert<Value extends true> = Value;

export type AuthCompatibility = Assert<Equal<AuthSession, BarrelAuthSession>>;
export type CreditCompatibility = Assert<Equal<CreditSummary, BarrelCreditSummary>>;
export type HealthCompatibility = Assert<Equal<HealthResponse, BarrelHealthResponse>>;
