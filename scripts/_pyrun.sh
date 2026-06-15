#!/usr/bin/env bash
# Cross-platform Python launcher for AI log hooks.
# Tries python3 → python → py -3 on PATH; on Windows, falls back to common
# Python install locations because Git Bash launched by some hooks gets a
# stripped PATH that omits the Windows Python directory.
# Designed to be sourced or called as: bash scripts/_pyrun.sh <script> [args...]
#
# Exits 0 silently if no Python is found — hooks must never block the AI tool.
set -u

if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
elif command -v py >/dev/null 2>&1; then
  PY="py -3"
else
  # PATH lookup failed — probe standard Windows install locations.
  PY=""
  shopt -s nullglob 2>/dev/null || true
  for cand in \
    /c/Users/*/AppData/Local/Programs/Python/Python*/python.exe \
    "/c/Program Files/Python"*/python.exe \
    "/c/Program Files (x86)/Python"*/python.exe \
    /c/Python*/python.exe; do
    if [ -x "$cand" ]; then PY="$cand"; break; fi
  done
  shopt -u nullglob 2>/dev/null || true
  [ -n "$PY" ] || exit 0
fi

if [ "$#" -gt 0 ]; then
  SCRIPT="$1"
  shift

  # Hooks may be launched from outside the repository. If the requested script
  # path is relative and not found from the current cwd, resolve it relative to
  # this launcher (repo root/scripts).
  case "$SCRIPT" in
    /*) ;;
    *)
      if [ ! -f "$SCRIPT" ]; then
        SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
        REPO_ROOT="$(dirname -- "$SCRIPT_DIR")"
        if [ -f "$REPO_ROOT/$SCRIPT" ]; then
          SCRIPT="$REPO_ROOT/$SCRIPT"
        fi
      fi
      ;;
  esac

  # shellcheck disable=SC2086
  exec $PY "$SCRIPT" "$@"
fi

# shellcheck disable=SC2086
exec $PY
