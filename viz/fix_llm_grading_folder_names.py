"""Normalize human_samples/llm_example_grading/<OID>/ grading file names.

- ``N_<slug>/grading.txt`` -> ``N_<slug>_grading.txt`` at the OID root (one-time layout;
  empty model subfolders are removed).
- ``N_<slug>_grading.txt`` -> ``<N>_<slug>_grading.txt`` with ``N`` from current
  ``RUN_SPECS`` order (renumber if the spec order changed).
- ``<slug>_grading.txt`` (no leading index) -> prefixed with 1..13 from ``RUN_SPECS``.

Skips ``combination/``. Two-phase move via temp names to avoid collisions.

    python -m viz.fix_llm_grading_folder_names
"""
from __future__ import annotations

import re
import shutil
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from viz.build_llm_example_grading import PICKS, BASE_OUT, RUN_SPECS

ORDER: list[str] = [t[2] for t in RUN_SPECS]
SLUG_TO_N: dict[str, int] = {s: i + 1 for i, s in enumerate(ORDER)}


def _migrate_subfolders_to_flat(root: Path) -> list[tuple[str, str]]:
    """Move ``N_slug/grading.txt`` -> ``N_slug_grading.txt``; remove empty dirs."""
    log: list[tuple[str, str]] = []
    for p in list(root.iterdir()):
        if not p.is_dir() or p.name == "combination":
            continue
        g = p / "grading.txt"
        if not g.is_file():
            continue
        dest = root / f"{p.name}_grading.txt"
        if dest.exists():
            g.unlink()
            try:
                p.rmdir()
            except OSError:
                print(
                    f"[WARN] {root.name}/{p.name}: leftover non-empty after migrate",
                    file=sys.stderr,
                )
            continue
        shutil.move(str(g), str(dest))
        try:
            p.rmdir()
        except OSError as e:
            print(
                f"[WARN] {root.name}/{p.name}: could not rmdir after move: {e}",
                file=sys.stderr,
            )
        log.append((p.name + "/grading.txt", dest.name))
    return log


def _target_dir_name(dirname: str) -> str | None:
    """For any remaining ``N_slug`` folders (non-combination), normalize index only."""
    if dirname == "combination":
        return None
    for slug in sorted(ORDER, key=len, reverse=True):
        if dirname == slug:
            return f"{SLUG_TO_N[slug]}_{slug}"
        if dirname.startswith(slug + "_") and dirname[len(slug) + 1 :].isdigit():
            return f"{SLUG_TO_N[slug]}_{slug}"
    m = re.match(r"^(\d+)_(.+)$", dirname)
    if m:
        slug = m.group(2)
        if slug in SLUG_TO_N:
            return f"{SLUG_TO_N[slug]}_{slug}"
        return None
    return None


def _normalize_root_dirs(root: Path) -> list[tuple[str, str]]:
    log: list[tuple[str, str]] = []
    subdirs = [
        p
        for p in root.iterdir()
        if p.is_dir() and p.name != "combination"
    ]
    moves: list[tuple[Path, Path]] = []
    for p in subdirs:
        tname = _target_dir_name(p.name)
        if tname is None:
            print(f"[WARN] {root.name}/{p.name}: unknown dir pattern, skip", file=sys.stderr)
            continue
        if tname == p.name:
            continue
        dest = p.parent / tname
        if dest.exists() and not dest.samefile(p):
            print(f"[WARN] would clobber {dest}, skip {p.name}", file=sys.stderr)
            continue
        moves.append((p, dest))

    phase1: list[tuple[Path, Path, str]] = []
    for src, dst in moves:
        tmp = src.parent / f"._ren_{uuid.uuid4().hex}"
        shutil.move(str(src), str(tmp))
        phase1.append((tmp, dst, src.name))

    for tmp, dst, oldname in phase1:
        if dst.exists():
            print(f"[ERR] {dst} appeared; leave {tmp}", file=sys.stderr)
            continue
        shutil.move(str(tmp), str(dst))
        log.append((oldname, dst.name))
    return log


def _target_file_name(basename: str) -> str | None:
    m = re.match(r"^(\d+)_(.+)_grading\.txt$", basename)
    if m:
        slug = m.group(2)
        if slug in SLUG_TO_N:
            return f"{SLUG_TO_N[slug]}_{slug}_grading.txt"
        return None
    if basename.endswith("_grading.txt"):
        stem = basename[: -len("_grading.txt")]
        if stem in SLUG_TO_N:
            return f"{SLUG_TO_N[stem]}_{stem}_grading.txt"
    return None


def _normalize_root_files(root: Path) -> list[tuple[str, str]]:
    log: list[tuple[str, str]] = []
    files = [
        p
        for p in root.iterdir()
        if p.is_file() and p.name.endswith("_grading.txt")
    ]
    moves: list[tuple[Path, Path]] = []
    for p in files:
        tname = _target_file_name(p.name)
        if tname is None:
            print(f"[WARN] {root.name}/{p.name}: unknown file pattern, skip", file=sys.stderr)
            continue
        if tname == p.name:
            continue
        dest = p.parent / tname
        if dest.exists() and not dest.samefile(p):
            print(f"[WARN] would clobber {dest}, skip {p.name}", file=sys.stderr)
            continue
        moves.append((p, dest))

    phase1: list[tuple[Path, Path, str]] = []
    for src, dst in moves:
        tmp = src.parent / f"._ren_{uuid.uuid4().hex}"
        shutil.move(str(src), str(tmp))
        phase1.append((tmp, dst, src.name))

    for tmp, dst, oldname in phase1:
        if dst.exists():
            print(f"[ERR] {dst} appeared; leave {tmp}", file=sys.stderr)
            continue
        shutil.move(str(tmp), str(dst))
        log.append((oldname, dst.name))
    return log


def main() -> None:
    for oid, _tc in PICKS:
        root = BASE_OUT / oid
        if not root.is_dir():
            print(f"[SKIP] {root}", file=sys.stderr)
            continue
        m = _migrate_subfolders_to_flat(root)
        if m:
            print(f"=== {oid} migrate folder->file ({len(m)})")
            for a, b in m:
                print(f"  {a!r} -> {b!r}")
        d = _normalize_root_dirs(root)
        if d:
            print(f"=== {oid} dirs ({len(d)})")
            for a, b in d:
                print(f"  {a!r} -> {b!r}")
        f = _normalize_root_files(root)
        if f:
            print(f"=== {oid} files ({len(f)})")
            for a, b in f:
                print(f"  {a!r} -> {b!r}")
        if not m and not d and not f:
            print(f"=== {oid} (no changes)")


if __name__ == "__main__":
    main()
