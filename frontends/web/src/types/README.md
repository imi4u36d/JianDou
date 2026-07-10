# Frontend contract boundaries

`types/index.ts` remains the compatibility barrel for existing imports. New code should import contracts from a domain entry point instead:

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

`auth.ts`, `credits.ts`, and `health.ts` now own their definitions. The compatibility barrel imports the account types it needs internally and re-exports all extracted contracts, so existing `@/types` consumers continue to compile.

The remaining domain files are migration facades over the compatibility barrel. Move their definitions incrementally, keeping each change reviewable and protected by typecheck coverage.

Place a contract in the narrowest domain that owns it. Cross-domain modules should use multiple explicit type imports rather than returning to the compatibility barrel.
