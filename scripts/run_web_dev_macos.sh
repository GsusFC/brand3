#!/usr/bin/env bash
set -euo pipefail

# macOS dev-only workaround.
#
# The LLM analyzer currently runs HTTP calls in a child process to enforce
# hard timeouts. On macOS, forking from the already multi-threaded Uvicorn
# process can trip Objective-C fork-safety during urllib proxy/framework
# initialization. This env var keeps local report rendering usable while the
# proper HTTP-client fix is implemented separately.
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export BRAND3_RATE_LIMIT_BYPASS_IPS="${BRAND3_RATE_LIMIT_BYPASS_IPS:-127.0.0.1,::1}"

export PYTHONPATH="${PYTHONPATH:-.}"

exec ./.venv/bin/python -m uvicorn web.app:app --host 127.0.0.1 --port 8000
