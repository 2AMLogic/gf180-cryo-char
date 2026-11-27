"""The one shared layout/ toolchain-pin check (``layout/toolchain.json``).

Every layout/ runner imports this module instead of re-deriving the check:
``layout/build.sh --check``, ``layout/precheck/run.sh --check`` and
``verification/test_layout_toolchain.py``. Before a runner does anything it

1. validates the pin file -- a closed key set, full commit SHAs, a sha256
   for the Nix installer, and no key declared twice (the stdlib decoder
   would silently keep only the last value);
2. looks every ``klt_required_commands`` entry up in ``klt --help``'s
   subcommand list.

A missing command is an error (exit 1) that names the command and the
install command that fixes it, never a silently-skipped check.

The die gate in ``verification/test_layout_toolchain.py`` adds
:func:`moved_precheck_pins`: a precheck record is only evidence for the
precheck and PDK commits it names, so a pin that has moved since needs a
new record.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

LAYOUT_DIR = Path(__file__).resolve().parent
PINS_FILENAME = "toolchain.json"

_COMMAND_RE = re.compile(r"[a-z][a-z0-9-]*\Z")
_SHA1_RE = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_VERSION_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*\Z")
_URL_RE = re.compile(r"https://\S+\Z")
_SUBCOMMAND_RE = re.compile(r"^ {4}([a-z][a-z0-9-]*)(?:\s{2,}|\s*$)")

_STR, _POS, _SHA1, _SHA256, _VERSION, _COMMANDS = (
    "str",
    "pos",
    "sha1",
    "sha256",
    "version",
    "commands",
)

_SCHEMA = {
    "klt_install": _STR,
    "klt_required_commands": _COMMANDS,
    "klt_last_verified_commit": _SHA1,
    "klayout_package_min": _VERSION,
    "die": {
        "top": _STR,
        "slot": _STR,
        "width_um": _POS,
        "height_um": _POS,
        "dbu_um": _POS,
    },
    "wafer_space": {
        "pdk": {"name": _STR, "open_pdks_commit": _SHA1, "delivered_by": _STR},
        "template": {
            "repo": _STR,
            "commit": _SHA1,
            "target": _STR,
            "slot": _STR,
            "scl": _STR,
            "pad": _STR,
            "sram": _STR,
        },
        "precheck": {"repo": _STR, "commit": _SHA1},
    },
    "nix": {"version": _VERSION, "url": _STR, "sha256": _SHA256},
}

PRECHECK_PINS = (
    ("wafer_space", "precheck", "commit"),
    ("wafer_space", "pdk", "open_pdks_commit"),
)


class PinError(RuntimeError):
    """The pin file exists but cannot be used."""


def _no_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON object key {key!r}")
        out[key] = value
    return out


def _check(value, kind, where):
    ok = {
        _STR: lambda v: isinstance(v, str) and v.strip() != "",
        _POS: lambda v: (
            not isinstance(v, bool) and isinstance(v, (int, float)) and v > 0
        ),
        _SHA1: lambda v: isinstance(v, str) and _SHA1_RE.fullmatch(v),
        _SHA256: lambda v: isinstance(v, str) and _SHA256_RE.fullmatch(v),
        _VERSION: lambda v: isinstance(v, str) and _VERSION_RE.fullmatch(v),
        _COMMANDS: lambda v: (
            isinstance(v, list)
            and len(v) > 0
            and all(isinstance(c, str) and _COMMAND_RE.fullmatch(c) for c in v)
            and len(set(v)) == len(v)
        ),
    }[kind]
    if not ok(value):
        wanted = {
            "sha1": "a full 40-hex commit sha",
            "sha256": "a 64-hex sha256",
            "pos": "a positive number",
            "version": "a dotted version",
            "commands": "a non-empty list of unique klt subcommand names",
        }[kind]
        raise PinError(f"{where}: expected {wanted}, got {value!r}")


def _validate(value, schema, where):
    for key, kind in schema.items():
        if key not in value:
            raise PinError(f"{where}: missing required key {key!r}")
        if isinstance(kind, dict):
            if not isinstance(value[key], dict):
                raise PinError(
                    f"{where}.{key}: expected an object, got {type(value[key]).__name__}"
                )
            _validate(value[key], kind, f"{where}.{key}")
        else:
            _check(value[key], kind, f"{where}.{key}")


def validate(pins, source: str = "pins") -> dict:
    """Validate a pin mapping and return it without the ``_`` commentary.

    ``source`` names the origin and prefixes every :class:`PinError`.
    """
    if not isinstance(pins, dict):
        raise PinError(f"{source}: must contain a JSON object")
    for key in pins:
        if key.startswith("_"):
            continue
        if key not in _SCHEMA:
            raise PinError(
                f"{source}: unknown pin key {key!r} (expected one of "
                f"{', '.join(_SCHEMA)}; prefix a comment key with '_')"
            )
    _validate(pins, _SCHEMA, source)
    at = pins["klt_install"].rpartition("@")[2]
    if _SHA1_RE.fullmatch(at) and at != pins["klt_last_verified_commit"]:
        raise PinError(
            f"{source}: klt_install pins {at} but klt_last_verified_commit is "
            f"{pins['klt_last_verified_commit']}; update both together"
        )
    return {k: v for k, v in pins.items() if not k.startswith("_")}


def load(layout_dir: Path | None = None) -> dict:
    """Read and validate ``layout/toolchain.json``."""
    path = (layout_dir or LAYOUT_DIR) / PINS_FILENAME
    try:
        pins = json.loads(path.read_text(), object_pairs_hook=_no_duplicate_keys)
    except ValueError as exc:
        raise PinError(f"{path} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise PinError(f"{path} cannot be read: {exc}") from exc
    return validate(pins, str(path))


def klt_subcommands(help_text: str) -> set[str]:
    """The subcommand names ``klt --help`` lists under ``<command>``.

    A subcommand line is indented by exactly four spaces; argparse indents a
    wrapped description line by the column the names end at, so no
    description word is ever taken for a command.
    """
    found: set[str] = set()
    in_block = False
    for line in help_text.splitlines():
        if line.strip() == "positional arguments:":
            in_block = True
            continue
        if not in_block:
            continue
        if line.strip() == "options:" or not line.startswith(" "):
            break
        match = _SUBCOMMAND_RE.match(line)
        if match:
            found.add(match.group(1))
    return found


def missing_klt_commands(pins: dict, help_text: str) -> list[str]:
    """Every pinned ``klt`` command this install does not list, in pin order."""
    present = klt_subcommands(help_text)
    return [c for c in pins["klt_required_commands"] if c not in present]


def _at(pins, path: tuple[str, ...]) -> object | None:
    """What ``pins`` holds at ``path``; ``None`` when nothing is held there."""
    for key in path:
        if not isinstance(pins, dict) or key not in pins:
            return None
        pins = pins[key]
    return pins


def moved_precheck_pins(record_pins: dict | None, pins: dict) -> list[str]:
    """Where the pins a precheck verdict depends on have moved since a record.

    A precheck record's verdict belongs to the precheck tree and the PDK it
    ran -- the DRC decks ship inside the PDK -- so once either has moved the
    record no longer describes what ``pins`` would do, and the GDS has to be
    prechecked again. That is :data:`PRECHECK_PINS` and nothing else: a moved
    template or ``klt`` pin cannot change a verdict already recorded, and
    demanding a new record for it would be a needless re-run.

    ``record_pins`` is the record's ``pins`` block and ``pins`` the validated
    pin file. Each entry names a pin by its dotted path under
    ``layout/toolchain.json``; a record that does not name a pin is reported
    rather than taken as matching.
    """
    moved = []
    for path in PRECHECK_PINS:
        name = ".".join(path)
        recorded = _at(record_pins, path)
        current = _at(pins, path)
        if recorded is None:
            moved.append(f"{name}: the record does not name it")
        elif recorded != current:
            moved.append(
                f"{name} moved: the record holds {recorded}, "
                f"the pin file holds {current}"
            )
    return moved


def klt_help(klt: str = "klt", pins: dict | None = None) -> str:
    """``klt --help``'s output, or a :class:`PinError` naming the fix."""
    try:
        result = subprocess.run([klt, "--help"], capture_output=True, text=True)
    except OSError as exc:
        raise PinError(
            f"cannot run `{klt} --help` ({exc}). {_install_hint(pins)}"
        ) from exc
    if result.returncode != 0:
        raise PinError(
            f"`{klt} --help` exited {result.returncode}. {_install_hint(pins)}"
        )
    return result.stdout


def _install_hint(pins: dict | None) -> str:
    if pins and "klt_install" in pins:
        return f"Install the pinned build: uv tool install {pins['klt_install']}"
    return f"Install the pinned build: uv tool install <klt_install from {LAYOUT_DIR / PINS_FILENAME}>"


def check(
    layout_dir: Path | None = None, help_text: str | None = None, klt: str = "klt"
) -> dict:
    """Load the pins and find the pinned ``klt`` commands this install lacks.

    ``help_text`` supplies ``klt --help``'s output directly (tests); without
    it ``klt`` is run. Returns ``{"pins": ..., "missing": [...]}``.
    """
    pins = load(layout_dir)
    text = help_text if help_text is not None else klt_help(klt, pins)
    return {"pins": pins, "missing": missing_klt_commands(pins, text)}


def summary(pins: dict) -> str:
    ws = pins["wafer_space"]
    return "\n".join(
        [
            (
                f"  klt pin {pins['klt_last_verified_commit'][:7]}: required commands "
                f"{', '.join(pins['klt_required_commands'])}"
            ),
            (
                f"  die {pins['die']['top']} slot {pins['die']['slot']}: "
                f"{pins['die']['width_um']:g} x {pins['die']['height_um']:g} um"
            ),
            f"  wafer.space {ws['pdk']['name']} @ open_pdks {ws['pdk']['open_pdks_commit'][:7]} ({ws['pdk']['delivered_by']})",
            f"  template {ws['template']['commit'][:7]} ({ws['template']['target']}, slot {ws['template']['slot']})",
            f"  precheck {ws['precheck']['commit'][:7]}",
            f"  nix {pins['nix']['version']}",
        ]
    )


def main(
    argv: list[str] | None = None,
    help_text: str | None = None,
    klt: str = "klt",
    stdout=None,
    stderr=None,
) -> int:
    """``--check``: exit 0 when the pins validate and klt has every command."""
    argv = sys.argv[1:] if argv is None else argv
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr
    if argv not in ([], ["--check"]):
        print(f"usage: {Path(sys.argv[0]).name} [--check]", file=stderr)
        return 2
    try:
        result = check(help_text=help_text, klt=klt)
    except PinError as exc:
        print(f"error: {exc}", file=stderr)
        return 1
    pins = result["pins"]
    if result["missing"]:
        for command in result["missing"]:
            print(
                f"error: klt '{command}' is required by {LAYOUT_DIR / PINS_FILENAME} "
                f"(klt_required_commands) but is not a subcommand of the installed klt. "
                f"{_install_hint(pins)}",
                file=stderr,
            )
        return 1
    print(f"{PINS_FILENAME}: OK", file=stdout)
    print(summary(pins), file=stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
