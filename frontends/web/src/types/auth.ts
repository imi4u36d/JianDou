/**
 * Authentication and account contracts.
 *
 * This domain entry point intentionally re-exports the current compatibility
 * barrel. Consumers can depend on a stable domain path while definitions are
 * migrated out of `types/index.ts` incrementally.
 */
export type {
  ActivateInviteRequest,
  AuthenticatedUser,
  AuthSession,
  InviteStatus,
  LoginRequest,
  UserRole,
  UserStatus,
} from "./index";
