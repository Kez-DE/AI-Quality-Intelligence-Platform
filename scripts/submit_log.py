#!/usr/bin/env python3
"""
Submit .ai-log/session.jsonl to grading server.
Called by git pre-push hook or manually.

After a successful submit, the live log is rotated:
  - Moved into .ai-log/archive/YYYY-MM-DD.jsonl (appended, never overwritten)
  - The live session.jsonl is recreated empty by the next hook write

If the POST fails, the pending file is restored so nothing is lost.
"""
import json
import os
import shutil
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    def _load_env_file(path: Path = Path(".env")) -> None:
        if not path.exists():
            return
        with open(path, encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value

    _load_env_file()

SERVER_URL = os.environ.get("AI_LOG_SERVER", "")
API_KEY = os.environ.get("AI_LOG_API_KEY", "")

# Hooks historically wrote to the canonical ".ai-log" directory, while some
# local .env files accidentally used ".ai-logs". Sweep both locations so a
# typo in AI_LOG_DIR cannot make pre-push silently miss valid hook entries.
CANONICAL_LOG_DIR = Path(".ai-log")
LEGACY_LOG_DIR = Path(".ai-logs")

# Match server-side MAX_BATCH_ENTRIES so we never get a 422.
# If the local file has more than this, we submit the oldest BATCH_LIMIT
# and leave the rest for the next push.
BATCH_LIMIT = 500


def _archive(log_dir: Path, pending: Path) -> None:
    """Append pending file to today's archive. Never overwrites existing data."""
    if not pending.exists() or pending.stat().st_size == 0:
        return
    archive_dir = log_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_file = archive_dir / f"{today}.jsonl"
    with open(pending, "rb") as src, open(archive_file, "ab") as dst:
        shutil.copyfileobj(src, dst)


def _archive_entries(log_dir: Path, entries: list[dict]) -> None:
    """Archive only the entries that were actually accepted for submission."""
    if not entries:
        return
    archive_dir = log_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    archive_file = archive_dir / f"{today}.jsonl"
    with open(archive_file, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _restore_pending(log_file: Path, pending: Path) -> None:
    """Failure path: put pending back at LOG_FILE so the next push retries.
    If hook wrote new entries to LOG_FILE in the meantime, prepend pending."""
    if not pending.exists():
        return
    if log_file.exists():
        # Concat: pending (older) + LOG_FILE (newer) → LOG_FILE
        tmp = log_file.with_suffix(".merge.jsonl")
        with open(tmp, "wb") as out:
            with open(pending, "rb") as a:
                shutil.copyfileobj(a, out)
            with open(log_file, "rb") as b:
                shutil.copyfileobj(b, out)
        os.replace(tmp, log_file)
        pending.unlink()
    else:
        pending.rename(log_file)


def _candidate_log_dirs() -> list[Path]:
    env_dir = Path(os.environ.get("AI_LOG_DIR", str(CANONICAL_LOG_DIR)))
    candidates = [env_dir, CANONICAL_LOG_DIR, LEGACY_LOG_DIR]

    seen = set()
    unique = []
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _submit_log_file(log_dir: Path) -> tuple[int, bool]:
    log_file = log_dir / "session.jsonl"
    if not log_file.exists() or log_file.stat().st_size == 0:
        return 0, False

    # Atomic rename closes the race window: hook writes that arrive after this
    # land in a fresh LOG_FILE, not in the batch we're about to POST.
    pending = log_file.with_name(f"session.pending.{int(time.time())}.jsonl")
    try:
        log_file.rename(pending)
    except FileNotFoundError:
        return 0, False

    entries = []
    leftover_lines = []
    with open(pending, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if len(entries) >= BATCH_LIMIT:
                leftover_lines.append(line)
                continue
            try:
                entries.append(json.loads(stripped))
            except json.JSONDecodeError:
                pass  # drop unparseable line

    if not entries:
        # Nothing to send; archive whatever was there (probably junk) and bail.
        _archive(log_dir, pending)
        pending.unlink()
        print(f"[ai-log] No valid entries to submit from {log_dir}.", file=sys.stderr)
        return 0, True

    payload = json.dumps({"entries": entries}, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    req = urllib.request.Request(
        SERVER_URL,
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(
                f"[ai-log] Submitted {len(entries)} entries from {log_dir} → {resp.status}",
                file=sys.stderr,
            )
    except urllib.error.URLError as e:
        # Failure: restore the whole pending (including leftover) for next push.
        _restore_pending(log_file, pending)
        print(f"[ai-log] Submit failed: {e} — logs kept locally.", file=sys.stderr)
        return 0, True

    # Success: archive the submitted batch, then handle any leftover.
    _archive_entries(log_dir, entries)
    pending.unlink()

    if leftover_lines:
        # More than BATCH_LIMIT entries existed; put the rest back so the
        # next push picks them up.
        with open(log_file, "a", encoding="utf-8") as f:
            f.writelines(leftover_lines)
        print(
            f"[ai-log] {len(leftover_lines)} entries deferred in {log_dir}.",
            file=sys.stderr,
        )

    return len(entries), True


def main():
    if not SERVER_URL:
        print("[ai-log] AI_LOG_SERVER not set — skipping submission.", file=sys.stderr)
        sys.exit(0)

    total = 0
    found_any_log_file = False
    for log_dir in _candidate_log_dirs():
        submitted, found_log_file = _submit_log_file(log_dir)
        total += submitted
        found_any_log_file = found_any_log_file or found_log_file

    if total == 0 and not found_any_log_file:
        dirs = ", ".join(str(path) for path in _candidate_log_dirs())
        print(f"[ai-log] No logs to submit. Checked: {dirs}", file=sys.stderr)


if __name__ == "__main__":
    main()
