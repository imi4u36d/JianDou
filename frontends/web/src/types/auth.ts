/** Authentication and account contracts. */
export type UserRole = "ADMIN" | "USER";

export type UserStatus = "ACTIVE" | "DISABLED";

export type InviteStatus = "UNUSED" | "USED" | "REVOKED" | "EXPIRED";

export interface AuthenticatedUser {
  id: number;
  username: string;
  role: UserRole;
}

export interface AuthSession {
  authenticated: boolean;
  user: AuthenticatedUser | null;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface ActivateInviteRequest {
  code: string;
  username: string;
  password: string;
}
