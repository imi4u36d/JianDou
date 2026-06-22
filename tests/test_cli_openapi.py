from __future__ import annotations

import pytest
pytestmark = pytest.mark.api
import json

from click.testing import CliRunner

from backend.__main__ import cli


def test_openapi_command_exports_schema(tmp_path) -> None:
    output = tmp_path / "openapi.json"
    result = CliRunner().invoke(cli, ["openapi", "--output", str(output)])

    assert result.exit_code == 0
    assert output.is_file()

    schema = json.loads(output.read_text(encoding="utf-8"))
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "JianDou API"
    assert "/api/v3/health" in schema["paths"]
    assert "/api/v3/auth/login" in schema["paths"]
