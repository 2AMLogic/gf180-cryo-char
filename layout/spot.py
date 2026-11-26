"""Submit, collect and record the layout/ Spot jobs (issue #4).

Two heavy runs live here. Both run on the Spot batch fleet as ``repo-script``
jobs on the heavy image, never on the submitting host:

  build      the pinned wafer.space template -> chip_top.gds  (layout/build.sh)
  precheck   the pinned wafer.space precheck on one GDS        (layout/precheck/run.sh)

Each is driven in separate steps so no single command outlives a shell:

  <runner> --check             validate the pins and the pinned klt commands
  <runner> submit [...]        stage one tarball and launch it
  <runner> collect <group>     wait for the group and pull its outputs back
  <runner> record <shard dir>  verify what came back, write one append-only record

The tarball is ``git archive`` of a committed HEAD plus the upstream trees at
their pinned commits (``layout/vendor/``) and, for a precheck, the GDS under
test (``layout/precheck/in/``). Scratch never enters git: it all lives under
``layout/_work/``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from layout import records, toolchain_pin

LAYOUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = LAYOUT_DIR.parent
WORK_DIR = LAYOUT_DIR / "_work"
RUNS_DIR = WORK_DIR / "runs"
REPO_SLUG = "2AMLogic/gf180-cryo-char"
ISSUE = "4"
CAPACITY_WAIT = "600"
SUBMITTER = Path(
    os.environ.get("REPO_SCRIPT_SUBMIT")
    or Path.home() / "GitHub/2am/infra/aws/repo-script-submit.py"
)
VENDOR = "layout/vendor"
ARTIFACTS = LAYOUT_DIR / "artifacts.json"
DIE = LAYOUT_DIR / "die.json"
STAGES = {
    "build": {
        "script": "layout/jobs/build.sh",
        "output": "build/out",
        "records": LAYOUT_DIR / "build" / "records",
        "schema": records.SCHEMA_BUILD,
        "upstream": "template",
    },
    "precheck": {
        "script": "layout/jobs/precheck.sh",
        "output": "precheck/out",
        "records": LAYOUT_DIR / "precheck" / "records",
        "schema": records.SCHEMA_PRECHECK,
        "upstream": "precheck",
    },
}


class DriverError(RuntimeError):
    """The driver refuses to proceed; nothing was submitted or written."""


def say(message: str) -> None:
    print(f"[layout] {message}", flush=True)


def now() -> dt.datetime:
    return dt.datetime.now(dt.UTC).replace(microsecond=0)


def git(*args: str, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise DriverError(
            f"git {' '.join(args)} in {cwd} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def load_json(path: Path, default=None):
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text())
    except ValueError as exc:
        raise DriverError(f"{path} is not valid JSON: {exc}") from exc


def check_pins() -> dict:
    if toolchain_pin.main(["--check"]) != 0:
        raise DriverError(
            "toolchain check failed (see the errors above); nothing was submitted"
        )
    return toolchain_pin.load()


def head_and_clean() -> str:
    """HEAD's sha, after refusing a tree with uncommitted layout/ changes."""
    if git("status", "--porcelain", "--", "layout", "verification").strip():
        raise DriverError(
            "layout/ or verification/ has uncommitted changes: the job runs the "
            "committed tree, so commit first"
        )
    return git("rev-parse", "HEAD")


def upstream(key: str, pins: dict) -> tuple[Path, str]:
    """A checkout holding the pinned commit of ``wafer_space.<key>``."""
    spec = pins["wafer_space"][key]
    clone = WORK_DIR / "upstream" / spec["repo"].rsplit("/", 1)[-1]
    if not (clone / ".git").exists():
        clone.mkdir(parents=True, exist_ok=True)
        git("init", "-q", cwd=clone)
        git("remote", "add", "origin", spec["repo"], cwd=clone)
    present = ["git", "cat-file", "-e", spec["commit"] + "^{commit}"]
    if subprocess.run(present, cwd=clone, capture_output=True).returncode != 0:
        say(f"fetching {spec['repo']} @ {spec['commit'][:7]}")
        shallow = ["git", "fetch", "-q", "--depth", "1", "origin", spec["commit"]]
        if subprocess.run(shallow, cwd=clone, capture_output=True).returncode != 0:
            git("fetch", "-q", "origin", cwd=clone)
    git("cat-file", "-e", spec["commit"] + "^{commit}", cwd=clone)
    return clone, spec["commit"]


def stage_tarball(commit: str, vendors: dict, extra: dict, dest: Path) -> str:
    """HEAD's tree plus ``vendors`` (prefix -> (clone, sha)) and ``extra``
    (archive name -> path), gzipped to ``dest``; returns its sha256."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        bare = Path(tmp) / "source.tar"
        git("archive", "--format=tar", "-o", str(bare), commit, "layout")
        with tarfile.open(bare, "a") as tar:
            for prefix, (clone, sha) in vendors.items():
                data = subprocess.run(
                    ["git", "-C", str(clone), "archive", "--format=tar", sha],
                    check=True,
                    stdout=subprocess.PIPE,
                ).stdout
                with tarfile.open(fileobj=io.BytesIO(data)) as source:
                    for member in source.getmembers():
                        member.name = f"{prefix}/{member.name}"
                        stream = source.extractfile(member) if member.isfile() else None
                        tar.addfile(member, stream)
            for name, path in extra.items():
                tar.add(path, arcname=name)
        with (
            open(bare, "rb") as source,
            open(dest, "wb") as raw,
            gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=6, mtime=0) as out,
        ):
            shutil.copyfileobj(source, out, 1 << 20)
    return records.sha256_file(dest)


def submitter_command(*args: str) -> list[str]:
    if not SUBMITTER.is_file():
        raise DriverError(
            f"repo-script-submit.py not found at {SUBMITTER}; set REPO_SCRIPT_SUBMIT"
        )
    return [sys.executable, str(SUBMITTER), *args]


def cmd_submit(stage: str, args: argparse.Namespace) -> int:
    pins = check_pins()
    commit = head_and_clean()
    spec = STAGES[stage]
    group = args.group or f"cryo4-{stage}-{now():%Y%m%dT%H%M%SZ}"
    vendors = {f"{VENDOR}/{spec['upstream']}": upstream(spec["upstream"], pins)}
    extra: dict = {}
    job_args: list[str] = []
    staged = {
        "stage": stage,
        "group": group,
        "commit": commit,
        "submitted_utc": now().isoformat(),
    }
    if stage == "precheck":
        gds = Path(args.gds).resolve()
        if not gds.is_file():
            raise DriverError(f"no GDS at {gds}")
        if len(args.id) != 8 or any(c not in "0123456789ABCDEF" for c in args.id):
            raise DriverError(
                "--id must be exactly 8 upper-case hex characters (precheck.py's rule)"
            )
        name = f"layout/precheck/in/{args.label}{gds.suffix}"
        extra[name] = gds
        job_args = [name, "--id", args.id]
        if args.cob:
            job_args.append("--cob")
        for flag in ("threads", "workers"):
            if getattr(args, flag):
                job_args += [f"--{flag}", getattr(args, flag)]
        staged["input"] = {
            "label": args.label,
            "sha256": records.sha256_file(gds),
            "bytes": gds.stat().st_size,
        }
    tarball = WORK_DIR / "tarballs" / f"{group}.tar.gz"
    staged["tarball_sha256"] = stage_tarball(commit, vendors, extra, tarball)
    staged["tarball_bytes"] = tarball.stat().st_size
    staged["pins"] = pins
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{group}.submit.json").write_text(
        json.dumps(staged, indent=2, sort_keys=True) + "\n"
    )
    say(
        f"staged {tarball} ({staged['tarball_bytes']} bytes, sha256 {staged['tarball_sha256'][:12]})"
    )
    command = submitter_command(
        *submitter_args(
            tarball=tarball,
            commit=commit,
            group=group,
            script=spec["script"],
            output=spec["output"],
            job_args=["--probe"] if stage == "build" and args.probe else job_args,
            timeout=args.timeout,
            dry_run=args.dry_run,
            wait=args.wait,
        )
    )
    return subprocess.run(command, cwd=REPO_ROOT).returncode


def submitter_args(
    *,
    tarball: Path,
    commit: str,
    group: str,
    script: str,
    output: str,
    job_args: list[str],
    timeout: int,
    dry_run: bool,
    wait: int,
) -> list[str]:
    """The submitter's argv. A shard's argument list is one option value
    (``--shard=...``): a list that starts with ``--`` would otherwise be read
    as the submitter's own flag."""
    argv = [
        "--tarball",
        str(tarball),
        "--commit",
        commit,
        "--repo",
        REPO_SLUG,
        "--issue",
        ISSUE,
        "--script",
        script,
        "--output",
        output,
        "--wait-for-capacity",
        CAPACITY_WAIT,
        "--out",
        str(RUNS_DIR),
        "--group",
        group,
        "--requirements",
        "",
    ]
    if job_args:
        argv.append(f"--shard={shlex.join(job_args)}")
    if timeout:
        argv += ["--timeout", str(timeout)]
    argv += ["--dry-run"] if dry_run else []
    argv += ["--wait", str(wait)] if wait else ["--no-wait"]
    return argv


def cmd_collect(args: argparse.Namespace) -> int:
    command = submitter_command(
        "--collect", args.group, "--out", str(RUNS_DIR), "--wait", str(args.wait)
    )
    return subprocess.run(command, cwd=REPO_ROOT).returncode


def shard_result(shard: Path) -> dict:
    run = load_json(shard / "run.json", {}) or {}
    status = load_json(shard / "status.json", {}) or {}
    outputs = run.get("outputs") or {}
    found = outputs.get("found") or []
    present = bool(found) and all((shard / "files" / name).exists() for name in found)
    state = status.get("state") or "unknown"
    return {
        "state": state,
        "ok": state == "done"
        and run.get("exit_code") == 0
        and not outputs.get("missing")
        and present,
        "exit_code": run.get("exit_code"),
        "failure_reason": status.get("failure_reason"),
        "wall_seconds": run.get("wall_seconds"),
        "instance_type": run.get("instance_type"),
        "image_id": run.get("image_id"),
        "retry_count": run.get("retry_count"),
        "started_at": run.get("started_at"),
        "outputs": outputs,
    }


def copy_evidence(bundle: Path, sources: dict) -> None:
    for name, path in sources.items():
        if path is None or not path.exists():
            continue
        target = bundle / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, target)
        else:
            shutil.copy2(path, target)


def klt(*args: str) -> dict:
    result = subprocess.run(["klt", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise DriverError(
            f"klt {' '.join(args)} exited {result.returncode}: {result.stderr.strip()}"
        )
    return json.loads(result.stdout)


def die_check(gds: Path, pins: dict) -> dict:
    """Read the built die back with klt and compare it to the pinned slot."""
    die = pins["die"]
    cells = klt("cells", "--format", "json", str(gds))
    stats = klt("stats", "--format", "json", "--geometry-digest", str(gds))
    box = stats["bbox_um"]
    checks = {
        "single_top_cell": cells["top_cell_count"] == 1,
        "top_cell_is_pinned": stats["top_cell"] == die["top"],
        "origin_at_zero": box["left"] == 0 and box["bottom"] == 0,
        "size_matches_slot": box["width"] == die["width_um"]
        and box["height"] == die["height_um"],
        "dbu_matches": stats["dbu_um"] == die["dbu_um"],
    }
    return {
        **checks,
        "die_matches_pin": all(checks.values()),
        "top_cell": stats["top_cell"],
        "dbu_um": stats["dbu_um"],
        "bbox_um": box,
        "geometry_digest": stats["geometry_digest"],
    }


def artifact_put(gds: Path, name: str, tool: str) -> dict:
    command = [
        "klt",
        "artifact",
        "put",
        "--format",
        "json",
        "--manifest",
        str(ARTIFACTS),
        "--name",
        name,
        "--producer-tool",
        tool,
        str(gds),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise DriverError(
            f"klt artifact put exited {result.returncode}: {result.stderr.strip()}"
        )
    return json.loads(result.stdout)["entries"][0]


def staged_group(group: str, stage: str):
    staged = load_json(RUNS_DIR / f"{group}.submit.json")
    if not staged or staged.get("group") != group or staged.get("stage") != stage:
        raise DriverError(
            f"no {stage} submit record for group {group} under {RUNS_DIR}"
        )
    return staged


def write_or_discard(stage: str, label: str, staged: dict, fill) -> tuple[Path, dict]:
    """Reserve a bundle, let ``fill(bundle) -> record`` build the record,
    write it once. A failed fill leaves no half-record behind."""
    rid = records.record_id(now(), staged["commit"][:7], label)
    bundle = records.reserve(STAGES[stage]["records"], rid)
    try:
        record = fill(bundle)
        record["evidence"] = records.evidence(bundle)
        return records.write_record(bundle, record), record
    except BaseException:
        shutil.rmtree(bundle)
        raise


def cmd_record_build(args: argparse.Namespace) -> int:
    shard = Path(args.shard).resolve()
    group = args.group or shard.parent.name
    staged = staged_group(group, "build")
    result = shard_result(shard)
    out = shard / "files" / "build" / "out"
    job = load_json(out / "build.json", {}) or {}
    gds = out / "chip_top.gds"

    def fill(bundle: Path) -> dict:
        record = {
            "schema": records.SCHEMA_BUILD,
            "record_id": bundle.name,
            "created_utc": now().isoformat(),
            "repo_commit": staged["commit"],
            "pins": staged["pins"],
            "source_tarball_sha256": staged["tarball_sha256"],
            "job": {"group": group, "shard": shard.name, **result},
            "make": job.get("make"),
            "target": job.get("target"),
            "tools": job.get("tools"),
            "metrics": job.get("metrics"),
        }
        if result["ok"] and gds.is_file():
            record["gds"] = {
                "name": "chip_top.gds",
                "sha256": records.sha256_file(gds),
                "bytes": gds.stat().st_size,
            }
            record["checks"] = die_check(gds, staged["pins"])
            passed = record["checks"]["die_matches_pin"] and job.get("pass") is True
            record["status"] = "pass" if passed else "fail"
            if passed and not args.no_artifact:
                record["artifact"] = artifact_put(
                    gds, f"build/{bundle.name}/chip_top.gds", "librelane"
                )
        else:
            record["status"] = "fail" if result["state"] == "done" else "error"
        copy_evidence(
            bundle,
            {
                "console.log": out / "console.log",
                "build.json": out / "build.json",
                "tools.json": out / "tools.json",
                "phases.txt": out / "phases.txt",
                "metrics.json": out / "metrics.json",
                "run.json": shard / "run.json",
                "status.json": shard / "status.json",
                "harness.log": shard / "harness.log",
            },
        )
        return record

    path, record = write_or_discard("build", args.label, staged, fill)
    say(f"wrote {path}: status {record['status']}")
    if record["status"] == "pass" and args.as_die:
        if "artifact" not in record:
            raise DriverError(
                "--as-die needs the GDS in the artifact store: drop --no-artifact"
            )
        previous = load_json(DIE, {}) or {}
        same = previous.get("gds", {}).get("sha256") == record["gds"]["sha256"]
        DIE.write_text(
            json.dumps(
                {
                    "schema": "gf180-cryo-char.layout.die/1",
                    "gds": record["gds"],
                    "artifact": {
                        "manifest": "layout/artifacts.json",
                        "name": record["artifact"]["name"],
                    },
                    "build_record": record["record_id"],
                    "precheck_record": previous.get("precheck_record")
                    if same
                    else None,
                },
                indent=2,
            )
            + "\n"
        )
        say(
            f"layout/die.json names build {record['record_id']}"
            + (
                " and its precheck record"
                if same and previous.get("precheck_record")
                else "; it has no precheck record yet"
            )
        )
    return 0 if record["status"] == "pass" else 1


def cmd_record_precheck(args: argparse.Namespace) -> int:
    shard = Path(args.shard).resolve()
    group = args.group or shard.parent.name
    staged = staged_group(group, "precheck")
    result = shard_result(shard)
    out = shard / "files" / "precheck" / "out"

    def fill(bundle: Path) -> dict:
        job = load_json(out / "precheck.json")
        record = {
            "schema": records.SCHEMA_PRECHECK,
            "record_id": bundle.name,
            "created_utc": now().isoformat(),
            "repo_commit": staged["commit"],
            "pins": staged["pins"],
            "source_tarball_sha256": staged["tarball_sha256"],
            "job": {"group": group, "shard": shard.name, **result},
        }
        if job is None:
            record["status"] = "error"
        else:
            if job["input"]["sha256"] != staged["input"]["sha256"]:
                raise DriverError(
                    "the job prechecked a different GDS than the one staged"
                )
            record["status"] = (
                "pass" if result["ok"] and job.get("pass") is True else "fail"
            )
            for key in (
                "input",
                "options",
                "tools",
                "pdk_open_pdks_observed",
                "metrics",
                "wall_seconds",
                "image",
                "run_tag",
            ):
                record[key] = job.get(key)
        copy_evidence(
            bundle,
            {
                "console.log": out / "console.log",
                "precheck.json": out / "precheck.json",
                "tools.json": out / "tools.json",
                "phases.txt": out / "phases.txt",
                "flow": out / "flow",
                "flow-files.txt": out / "flow-files.txt",
                "run.json": shard / "run.json",
                "status.json": shard / "status.json",
                "harness.log": shard / "harness.log",
            },
        )
        return record

    label = staged.get("input", {}).get("label", "precheck")
    path, record = write_or_discard("precheck", label, staged, fill)
    say(f"wrote {path}: status {record['status']}")
    if record["status"] == "pass" and args.is_die:
        die = load_json(DIE)
        if not die:
            raise DriverError("there is no layout/die.json to point at this record")
        if die["gds"]["sha256"] != record["input"]["sha256"]:
            raise DriverError(
                "the die in layout/die.json is not the GDS this record prechecked"
            )
        die["precheck_record"] = record["record_id"]
        DIE.write_text(json.dumps(die, indent=2) + "\n")
        say(f"layout/die.json names precheck {record['record_id']}")
    return 0 if record["status"] == "pass" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="layout.spot", description=__doc__.split("\n\n")[0]
    )
    sub = parser.add_subparsers(dest="stage", required=True)
    for stage in STAGES:
        stage_p = sub.add_parser(stage)
        stage_sub = stage_p.add_subparsers(dest="action", required=True)
        stage_sub.add_parser(
            "check", help="validate the pins and the pinned klt commands"
        )
        submit_p = stage_sub.add_parser(
            "submit", help="stage one tarball and launch it"
        )
        submit_p.add_argument("--group", default="")
        submit_p.add_argument(
            "--dry-run",
            action="store_true",
            help="stage the tarball only: touch no AWS, launch nothing",
        )
        submit_p.add_argument(
            "--timeout",
            type=int,
            default=0,
            help="per-job cap in seconds (default: the image profile's)",
        )
        if stage == "build":
            submit_p.add_argument(
                "--probe", action="store_true", help="stop after the bootstrap"
            )
        submit_p.add_argument(
            "--wait",
            type=int,
            default=0,
            help="poll this many seconds after launch instead of returning",
        )
        if stage == "precheck":
            submit_p.add_argument("--gds", required=True)
            submit_p.add_argument("--label", required=True)
            submit_p.add_argument("--cob", action="store_true")
            submit_p.add_argument("--id", default="FFFFFFFF")
            submit_p.add_argument("--threads", default="")
            submit_p.add_argument("--workers", default="")
        collect_p = stage_sub.add_parser(
            "collect", help="wait for the group and collect it"
        )
        collect_p.add_argument("group")
        collect_p.add_argument("--wait", type=int, default=540)
        record_p = stage_sub.add_parser(
            "record", help="verify a collected shard, write one record"
        )
        record_p.add_argument("shard")
        record_p.add_argument("--group", default="")
        if stage == "build":
            record_p.add_argument("--label", default="template")
            record_p.add_argument("--no-artifact", action="store_true")
            record_p.add_argument("--as-die", action="store_true")
        else:
            record_p.add_argument("--is-die", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action == "check":
            return toolchain_pin.main(["--check"])
        if args.action == "submit":
            return cmd_submit(args.stage, args)
        if args.action == "collect":
            return cmd_collect(args)
        if args.action == "record":
            return (
                cmd_record_build(args)
                if args.stage == "build"
                else cmd_record_precheck(args)
            )
    except (
        DriverError,
        records.RecordExists,
        toolchain_pin.PinError,
        ValueError,
        OSError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 2


if __name__ == "__main__":
    sys.exit(main())
