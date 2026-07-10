# Frontend contract boundaries

`types/index.ts` is the compatibility barrel for existing imports. New code should import contracts from a domain entry point instead:

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

The domain files currently re-export the existing definitions. This creates stable consumer boundaries first; definitions can then move out of the legacy barrel incrementally without another application-wide import migration.

Place a contract in the narrowest domain that owns it. Cross-domain API modules should use multiple explicit type imports rather than returning to the compatibility barrel.
