"""Shared Jinja2 template environment for the web app."""

from hashlib import sha256
from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_STATIC_FILES = [
    _STATIC_DIR / "main.css",
    _STATIC_DIR / "moodboard.js",
    _STATIC_DIR / "status_waiting.js",
]
try:
    STATIC_ASSET_VERSION = sha256(b"".join(path.read_bytes() for path in _STATIC_FILES)).hexdigest()[:12]
except OSError:
    STATIC_ASSET_VERSION = "dev"

templates.env.globals["static_asset_version"] = STATIC_ASSET_VERSION
