from __future__ import annotations

import pytest
pytestmark = pytest.mark.infra
import re
from pathlib import Path

from pydantic import AliasChoices

from backend.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ENV_FILES = [
    ".env.dev.example",
    ".env.docker.example",
    ".env.prod.example",
]
OPTIONAL_ENV_KEYS = {
    "JIANDOU_AUTO_MIGRATE",
    "JIANDOU_MODEL_API_KEY",
    "JIANDOU_MODEL_BASE_URL",
}


def test_env_examples_cover_settings_fields() -> None:
    expected = _settings_env_keys()

    for filename in EXAMPLE_ENV_FILES:
        present = _env_keys(REPO_ROOT / filename)
        missing = sorted(expected - present)
        assert missing == [], f"{filename} is missing {missing}"


def test_configuration_reference_mentions_example_variables() -> None:
    documented = (REPO_ROOT / "docs/configuration.md").read_text(encoding="utf-8")
    env_keys = set()
    for filename in EXAMPLE_ENV_FILES:
        env_keys.update(_env_keys(REPO_ROOT / filename))

    missing = sorted(key for key in env_keys - OPTIONAL_ENV_KEYS if key not in documented)
    assert missing == []


def _settings_env_keys() -> set[str]:
    keys: set[str] = set()
    for field_name, field in Settings.model_fields.items():
        validation_alias = field.validation_alias
        if isinstance(validation_alias, AliasChoices):
            keys.add(str(validation_alias.choices[0]))
        elif isinstance(validation_alias, str):
            keys.add(validation_alias)
        else:
            keys.add(f"JIANDOU_{field_name.upper()}")
    return keys


def _env_keys(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"^(JIANDOU_[A-Z0-9_]+)=", text, flags=re.MULTILINE))
