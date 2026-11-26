"""Append-only evidence records under ``layout/``.

A record is a directory ``layout/<stage>/records/<record-id>/`` holding
``record.json`` (the structured record), ``record.md`` (the same record
rendered for reading) and the evidence files it names, each by sha256. It is
created exclusively: an id can be reserved once, and once written a record
cannot be rewritten (:class:`RecordExists`). A result is never superseded by
deleting its record; a later record supersedes it and says why.

The bundle carries an ``INCOMPLETE`` marker from reservation until
:func:`write_record`, so a crash mid-write is distinguishable from a record
that was never started.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

SCHEMA_BUILD = "gf180-cryo-char.layout.build-record/1"
SCHEMA_PRECHECK = "gf180-cryo-char.layout.precheck-record/1"
INCOMPLETE_MARKER = "INCOMPLETE"
RECORD_JSON = "record.json"
RECORD_MD = "record.md"
STATUSES = ("pass", "fail", "error")

_LABEL_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,39}\Z")
_RESERVED = {RECORD_JSON, RECORD_MD, INCOMPLETE_MARKER}


class RecordExists(RuntimeError):
    """The record id is already written; evidence is never overwritten."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record_id(when: dt.datetime, short_sha: str, label: str) -> str:
    """``<YYYYMMDD>-<HHMMSS>-<short-sha>-<label>``, as under ``sim/``."""
    if not _LABEL_RE.fullmatch(label):
        raise ValueError(f"label {label!r} must match {_LABEL_RE.pattern}")
    return f"{when:%Y%m%d-%H%M%S}-{short_sha}-{label}"


def reserve(records_dir: Path, rid: str) -> Path:
    """Create ``records_dir/<rid>/`` exclusively, marked ``INCOMPLETE``."""
    bundle = records_dir / rid
    bundle.parent.mkdir(parents=True, exist_ok=True)
    bundle.mkdir()
    (bundle / INCOMPLETE_MARKER).write_text("reserved; no record written yet\n")
    return bundle


def mark_incomplete(bundle: Path, reason: str) -> None:
    (bundle / INCOMPLETE_MARKER).write_text(f"{reason}\n")


def evidence(bundle: Path) -> list[dict]:
    """Every evidence file in ``bundle`` as ``{path, sha256, bytes}``."""
    out = []
    for path in sorted(
        p for p in bundle.rglob("*") if p.is_file() and p.name not in _RESERVED
    ):
        out.append(
            {
                "path": path.relative_to(bundle).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    return out


def _render(value, depth: int) -> list[str]:
    pad = "  " * depth
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, dict) and item:
                lines.append(f"{pad}- **{key}**:")
                lines += _render(item, depth + 1)
            elif (
                isinstance(item, list)
                and item
                and all(isinstance(i, dict) for i in item)
            ):
                lines.append(f"{pad}- **{key}**:")
                for entry in item:
                    lines.append(
                        f"{pad}  - " + ", ".join(f"{k}: {v}" for k, v in entry.items())
                    )
            else:
                lines.append(
                    f"{pad}- **{key}**: {item if isinstance(item, str) else json.dumps(item)}"
                )
        return lines
    return [f"{pad}- {json.dumps(value)}"]


_TITLES = {
    "created_utc": "Created (UTC)",
    "repo_commit": "Repo commit",
    "source_tarball_sha256": "Source tarball SHA-256",
    "pdk_open_pdks_observed": "PDK revision observed",
}


def render_markdown(record: dict) -> str:
    lines = [f"# {record['record_id']}", "", f"**Status**: {record['status']}", ""]
    for key, value in record.items():
        if key in ("record_id", "status", "schema"):
            continue
        title = _TITLES.get(key, key.replace("_", " ").capitalize())
        lines.append(f"## {title}")
        lines.append("")
        lines += _render(value, 0)
        lines.append("")
    return "\n".join(lines)


def write_record(bundle: Path, record: dict) -> Path:
    """Write ``record.json`` and ``record.md`` once, then drop ``INCOMPLETE``."""
    target = bundle / RECORD_JSON
    if target.exists() or (bundle / RECORD_MD).exists():
        raise RecordExists(
            f"{bundle} already holds a record; write a new record that "
            f"supersedes it instead"
        )
    if record.get("status") not in STATUSES:
        raise ValueError(
            f"status {record.get('status')!r} is not one of {', '.join(STATUSES)}"
        )
    target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    path = bundle / RECORD_MD
    path.write_text(render_markdown(record))
    (bundle / INCOMPLETE_MARKER).unlink(missing_ok=True)
    return path


def load_record(bundle: Path) -> dict:
    return json.loads((bundle / RECORD_JSON).read_text())


def check_intact(bundle: Path) -> list[str]:
    """Why ``bundle``'s record cannot be trusted; empty when it can."""
    problems = []
    if (bundle / INCOMPLETE_MARKER).exists():
        problems.append(
            f"{bundle / INCOMPLETE_MARKER} still present: the record was never finalized"
        )
    try:
        record = load_record(bundle)
    except (OSError, ValueError) as exc:
        return [f"cannot read {bundle / RECORD_JSON}: {exc}"]
    if record.get("status") not in STATUSES:
        problems.append(
            f"status {record.get('status')!r} is not one of {', '.join(STATUSES)}"
        )
    listed = set()
    for entry in record.get("evidence") or []:
        path = bundle / entry["path"]
        listed.add(entry["path"])
        if not path.is_file():
            problems.append(f"evidence file missing: {entry['path']}")
            continue
        if (
            path.stat().st_size != entry["bytes"]
            or sha256_file(path) != entry["sha256"]
        ):
            problems.append(
                f"evidence file changed after the record was written: {entry['path']}"
            )
    for path in sorted(p for p in bundle.rglob("*") if p.is_file()):
        name = path.relative_to(bundle).as_posix()
        if name not in listed and name not in _RESERVED and name != RECORD_MD:
            problems.append(f"evidence file not named by the record: {name}")
    return problems
