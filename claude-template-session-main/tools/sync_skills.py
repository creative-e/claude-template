#!/usr/bin/env python3
"""
sync_skills.py - one-way mirror of .claude/skills/ -> .agents/skills/.

.claude/skills/ is canonical. .agents/skills/ is a DERIVED copy that other
agent runtimes read; it must never be edited by hand (your edits there will be
clobbered on the next sync). This script makes .agents/skills/ an exact mirror
of .claude/skills/: it copies new/changed files and removes anything in the
destination that no longer exists in the source.

Usage:
  python tools/sync_skills.py            Full mirror sync (manual run).
  python tools/sync_skills.py --hook     PostToolUse hook mode: read the
                                         tool-call JSON on stdin and sync only
                                         when the edited/written file lives
                                         under .claude/skills/. Always exits 0
                                         so a sync hiccup never blocks a tool.

Repo root is located from this file's path, so cwd does not matter.
"""

from __future__ import annotations

import filecmp
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".claude" / "skills"
DST = ROOT / ".agents" / "skills"


def _files_equal(a: Path, b: Path) -> bool:
    """True if both files exist and have identical content."""
    if not b.exists():
        return False
    return filecmp.cmp(a, b, shallow=False)


def mirror(src: Path, dst: Path) -> tuple[list[Path], list[Path]]:
    """Make `dst` an exact mirror of `src`. Returns (copied, removed) rel paths."""
    copied: list[Path] = []
    removed: list[Path] = []

    dst.mkdir(parents=True, exist_ok=True)

    # Pass 1: copy source -> dest (only new or changed files).
    src_rels: set[Path] = set()
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        src_rels.add(rel)
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not _files_equal(path, target):
                shutil.copy2(path, target)
                copied.append(rel)

    # Pass 2: delete dest entries with no source counterpart. Deepest first so
    # directories are empty by the time we try to remove them.
    for path in sorted(dst.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        rel = path.relative_to(dst)
        if rel in src_rels:
            continue
        if path.is_dir() and not path.is_symlink():
            # Windows can briefly hold handles on a just-emptied dir; retry.
            for attempt in range(4):
                try:
                    path.rmdir()
                    removed.append(rel)
                    break
                except OSError:
                    if attempt < 3:
                        time.sleep(0.05)
                        continue
                    print(f"[sync_skills] could not remove dir {rel.as_posix()} (locked)",
                          file=sys.stderr)
        else:
            path.unlink()
            removed.append(rel)

    return copied, removed


def _hook_should_sync() -> bool:
    """In --hook mode, decide whether this tool call touched .claude/skills/.

    Write/Edit: gate on file_path under .claude/skills/.
    Bash: gate on whether the command string mentions the skills path (catches
    rm, mv, cp, etc. on either side of the canonical/derived pair).
    """
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return False
    tool_input = payload.get("tool_input") or {}

    file_path = tool_input.get("file_path") or tool_input.get("path")
    if file_path:
        try:
            Path(file_path).resolve().relative_to(SRC.resolve())
            return True
        except (ValueError, OSError):
            return False

    command = tool_input.get("command")
    if command and (".claude/skills" in command or ".claude\\skills" in command):
        return True

    return False


def main() -> int:
    hook_mode = "--hook" in sys.argv[1:]

    if hook_mode and not _hook_should_sync():
        return 0  # nothing relevant changed

    if not SRC.exists():
        msg = f"[sync_skills] source not found: {SRC}"
        if hook_mode:
            print(msg, file=sys.stderr)
            return 0
        print(msg, file=sys.stderr)
        return 1

    copied, removed = mirror(SRC, DST)

    rel_src = SRC.relative_to(ROOT)
    rel_dst = DST.relative_to(ROOT)
    print(f"[sync_skills] {rel_src} -> {rel_dst}: "
          f"{len(copied)} copied, {len(removed)} removed")
    for rel in copied:
        print(f"  + {rel.as_posix()}")
    for rel in removed:
        print(f"  - {rel.as_posix()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
