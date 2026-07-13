# Frontend contract boundaries

`types/index.ts` is a compatibility barrel for legacy `@/types` imports. New code should import contracts from an owning domain module:

- `@/types/auth`
- `@/types/generation`
- `@/types/tasks`
- `@/types/workflows`
- `@/types/materials`
- `@/types/uploads`
- `@/types/public-shares`
- `@/types/credits`
- `@/types/health`
- `@/types/admin`

## Ownership status

The following modules now own their definitions directly:

- `auth.ts`
- `credits.ts`
- `health.ts`
- `public-shares.ts`
- `uploads.ts`

The compatibility barrel re-exports those contracts and imports only the auth primitives still required by legacy admin definitions. The remaining domain modules currently re-export definitions that have not yet been moved.

Place a contract in the narrowest domain that owns it. Cross-domain API modules should use multiple explicit type imports rather than returning to the compatibility barrel. Owned contract modules must not import or re-export `./index`; ESLint enforces that boundary.
