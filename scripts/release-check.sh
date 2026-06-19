#!/bin/sh
set -eu

cleanup() {
  rm -rf build dist jiandou.egg-info docs/openapi.json
}

cleanup
trap cleanup EXIT INT TERM

npm test

TMP_DB=$(mktemp -t jiandou.XXXXXX.db)
JIANDOU_DATABASE_URL="sqlite+aiosqlite:///$TMP_DB" uv run alembic upgrade head
rm -f "$TMP_DB"

npm run packages:typecheck
npm run web:typecheck
npm run api:openapi

uv build

uv run python - <<'PY'
from pathlib import Path
from zipfile import ZipFile

wheels = sorted(Path("dist").glob("jiandou-*.whl"))
if len(wheels) != 1:
    raise SystemExit(f"Expected exactly one wheel, found {len(wheels)}")

with ZipFile(wheels[0]) as wheel:
    names = set(wheel.namelist())
    if any(name.startswith("tests/") for name in names):
        raise SystemExit("Wheel must not include tests/")
    if not any(name.endswith(".dist-info/licenses/License") for name in names):
        raise SystemExit("Wheel must include the project license")

schema = Path("docs/openapi.json")
if not schema.is_file():
    raise SystemExit("OpenAPI schema was not generated")
PY

printf '%s\n' "Release preflight checks passed."
