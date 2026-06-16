"""Tests for deploy shell entrypoint safety checks."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "deploy" / "entrypoint.sh"


def test_disable_litestream_is_rejected_in_production():
    env = os.environ.copy()
    env.update(
        {
            "BRAND3_DISABLE_LITESTREAM": "true",
            "BRAND3_ENVIRONMENT": "production",
            "BRAND3_DB_PATH": "/tmp/brand3-test.sqlite3",
        }
    )

    result = subprocess.run(
        ["bash", str(ENTRYPOINT)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "refusing BRAND3_DISABLE_LITESTREAM=true in production" in result.stderr


def test_disable_litestream_still_allows_non_production_staging(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_uvicorn = bin_dir / "uvicorn"
    fake_uvicorn.write_text("#!/bin/sh\necho uvicorn \"$@\"\n", encoding="utf-8")
    fake_uvicorn.chmod(fake_uvicorn.stat().st_mode | stat.S_IXUSR)

    env = os.environ.copy()
    env.update(
        {
            "BRAND3_DISABLE_LITESTREAM": "true",
            "BRAND3_ENVIRONMENT": "staging",
            "BRAND3_DB_PATH": str(tmp_path / "brand3.sqlite3"),
            "PATH": f"{bin_dir}:{env.get('PATH', '')}",
        }
    )

    result = subprocess.run(
        ["bash", str(ENTRYPOINT)],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "starting uvicorn without replication" in result.stdout
    assert "uvicorn web.app:app --host 0.0.0.0 --port 8080" in result.stdout
