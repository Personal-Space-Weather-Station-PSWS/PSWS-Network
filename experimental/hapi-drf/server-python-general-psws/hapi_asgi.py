"""ASGI launcher for Gunicorn/Uvicorn workers."""

from __future__ import annotations

import os
from pathlib import Path

from hapiserver.app import app as app_factory


def _resolve_config_path() -> str:
  configured = os.environ.get("HAPI_CONFIG", "config.json")
  path = Path(configured)

  if not path.is_absolute():
    path = Path.cwd() / path

  if not path.exists():
    raise FileNotFoundError(
      f"HAPI config file was not found: {path}. "
      "Set HAPI_CONFIG to an existing JSON file path."
    )

  return str(path)


app = app_factory(_resolve_config_path())
