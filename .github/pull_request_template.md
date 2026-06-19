## Summary

- 

## Verification

- [ ] `npm test`
- [ ] `npm run packages:typecheck`
- [ ] `npm run web:typecheck`
- [ ] `npm run release:check` for release-facing changes
- [ ] Fresh database migration check:
  `TMP_DB=$(mktemp -t jiandou.XXXXXX.db) && JIANDOU_DATABASE_URL="sqlite+aiosqlite:///$TMP_DB" uv run alembic upgrade head && rm -f "$TMP_DB"`
- [ ] `CHANGELOG.md` updated for release-facing changes

## Notes

- Configuration or migration changes are documented.
- Security-sensitive changes avoid logging secrets and unsafe production defaults.
