"""Shared Jinja2 template environment for the web app."""

from hashlib import sha256
from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

_STATIC_CSS = Path(__file__).resolve().parent / "static" / "main.css"
try:
    STATIC_ASSET_VERSION = sha256(_STATIC_CSS.read_bytes()).hexdigest()[:12]
except OSError:
    STATIC_ASSET_VERSION = "dev"

templates.env.globals["static_asset_version"] = STATIC_ASSET_VERSION
