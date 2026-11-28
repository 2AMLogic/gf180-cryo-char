"""Drive the layout/ Spot job scripts against a stub toolchain (issue #4).

The job scripts cannot run on a dispatch host: they install Nix and run
LibreLane, which belong on the Spot fleet. What is checked here is their
plumbing, with ``nix``, ``make``, the EDA binaries and ``precheck.py``
replaced by stubs: every pinned Makefile variable and precheck option reaches
the tool, the PDK revision gate stops the job, and the harvested outputs and
verdict follow the tool's exit code.
"""

import hashlib
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from layout import spot, toolchain_pin

REPO = Path(__file__).resolve().parents[1]
LAYOUT = REPO / "layout"
PINS = json.loads((LAYOUT / "toolchain.json").read_text())
TEMPLATE = PINS["wafer_space"]["template"]
PDK_COMMIT = PINS["wafer_space"]["pdk"]["open_pdks_commit"]

NIX = f"""#!/usr/bin/env bash
set -euo pipefail
case "${{1:-}}" in
	--version) echo "nix (Nix) {PINS["nix"]["version"]}" ;;
	develop) shift 4; exec "$@" ;;
	*) echo "stub nix: unexpected arguments $*" >&2; exit 99 ;;
esac
"""

MAKE = """#!/usr/bin/env bash
set -euo pipefail
echo "$PWD $*" >> "$STUB_LOG"
target=""
for arg in "$@"; do case "$arg" in *=*) ;; *) target="$arg" ;; esac; done
case "$target" in
	clone-pdk)
		mkdir -p gf180mcu/gf180mcuD
		printf '# stub\\nopen_pdks %s https://stub\\n' "$STUB_PDK_COMMIT" > gf180mcu/gf180mcuD/SOURCES
		;;
	librelane-condensed)
		[ -z "${STUB_FAIL_FLOW:-}" ] || { echo "FlowError: stub failure"; exit 1; }
		mkdir -p final/gds librelane/runs/STUBTAG/final
		cp "$STUB_GDS" final/gds/chip_top.gds
		echo '{"design__instance__area__uturn": 1}' > librelane/runs/STUBTAG/final/metrics.json
		;;
	*) echo "stub make: no rule for $target" >&2; exit 2 ;;
esac
"""

PRECHECK = """#!/usr/bin/env python3
import argparse
import json
import os
import sys

parser = argparse.ArgumentParser()
for flag in ("input", "top", "dir", "slot", "id", "threads", "workers"):
    parser.add_argument("--" + flag)
parser.add_argument("--cob", action="store_true")
args = parser.parse_args()
assert os.environ["PDK_ROOT"] and os.environ["PDK"] == "gf180mcuD"
assert os.environ["PDK_ROOT"].endswith("/layout/vendor/precheck/gf180mcu"), os.environ["PDK_ROOT"]
assert os.path.isdir(args.dir), f"DESIGN_DIR does not exist: {args.dir}"
final = os.path.join(args.dir, "runs", "STUBTAG", "final")
os.makedirs(final, exist_ok=True)
with open(os.path.join(final, "metrics.json"), "w") as handle:
    json.dump(vars(args), handle)
with open(os.path.join(final, "checker.log"), "w") as handle:
    handle.write("stub step log\\n")
sys.exit(int(os.environ.get("STUB_PRECHECK_RC", "0")))
"""


class SubmitterArgsTests(unittest.TestCase):
    def args(self, **job_args):
        options = {
            "tarball": Path("source.tar.gz"),
            "commit": "c" * 40,
            "group": "g",
            "script": "layout/jobs/build.sh",
            "output": "build/out",
            "timeout": 0,
            "job_args": [],
            "dry_run": True,
            "wait": 0,
        }
        return spot.submitter_args(**{**options, **job_args})

    def test_shard_arguments_travel_as_one_option_value(self):
        argv = self.args(job_args=["--probe"], timeout=1500)
        self.assertNotIn("--shard", argv)
        self.assertIn("--shard=--probe", argv)
        self.assertEqual(argv[argv.index("--timeout") + 1], "1500")
        self.assertEqual(argv[argv.index("--wait-for-capacity") + 1], "600")
        self.assertIn("--no-wait", argv)

    def test_a_precheck_option_list_is_shell_split_by_the_submitter(self):
        argv = self.args(
            job_args=["layout/precheck/in/die.gds", "--id", "DEADBEEF", "--cob"]
        )
        self.assertIn("--shard=layout/precheck/in/die.gds --id DEADBEEF --cob", argv)

    def test_spot_is_the_default_capacity_and_on_demand_is_an_opt_in(self):
        self.assertNotIn("--capacity", self.args())
        argv = self.args(on_demand=True)
        self.assertEqual(argv[argv.index("--capacity") + 1], "on-demand")


class SubmitTests(unittest.TestCase):
    """What ``submit`` hands the fleet submitter, with staging stubbed out."""

    def submit(self, *options):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            gds = work / "die.gds"
            gds.write_bytes(b"stub gds bytes\n")
            argv_out = work / "submitter-argv.json"
            submitter = work / "repo-script-submit.py"
            submitter.write_text(
                "import json, os, sys\n"
                'json.dump(sys.argv[1:], open(os.environ["STUB_ARGV_OUT"], "w"))\n'
            )
            shipped = {}

            def fake_tarball(commit, vendors, extra, dest):
                shipped.update(extra)
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(b"tarball\n")
                return "a" * 64

            replacements = {
                "REPO_ROOT": work,
                "WORK_DIR": work,
                "RUNS_DIR": work / "runs",
                "SUBMITTER": submitter,
                "check_pins": lambda: toolchain_pin.load(),
                "head_and_clean": lambda: "c" * 40,
                "upstream": lambda key, pins: (work / "upstream", "d" * 40),
                "stage_tarball": fake_tarball,
                "say": lambda message: None,
            }
            with (
                mock.patch.dict(os.environ, {"STUB_ARGV_OUT": str(argv_out)}),
                ExitStack() as stack,
            ):
                for name, value in replacements.items():
                    stack.enter_context(mock.patch.object(spot, name, value))
                args = spot.build_parser().parse_args(
                    [
                        "precheck",
                        "submit",
                        "--gds",
                        str(gds),
                        "--label",
                        "die",
                        "--group",
                        "g",
                        "--cob",
                        "--id",
                        "DEADBEEF",
                        "--threads",
                        "3",
                        *options,
                    ]
                )
                self.assertEqual(spot.cmd_submit("precheck", args), 0)
            staged = json.loads((work / "runs" / "g.submit.json").read_text())
            return json.loads(argv_out.read_text()), staged, shipped

    def test_the_job_gets_the_gds_then_its_declared_output_directory(self):
        """The shard arguments are layout/jobs/precheck.sh's ``GDS OUTDIR ...``:
        without OUTDIR the job exited 2 on the fleet (unknown argument)."""
        argv, staged, shipped = self.submit()
        self.assertEqual(list(shipped), ["layout/precheck/in/die.gds"])
        self.assertEqual(argv[argv.index("--script") + 1], "layout/jobs/precheck.sh")
        self.assertEqual(argv[argv.index("--output") + 1], "precheck/out")
        self.assertEqual(
            [a for a in argv if a.startswith("--shard=")],
            [
                "--shard=layout/precheck/in/die.gds precheck/out --id DEADBEEF "
                "--cob --threads 3"
            ],
        )
        self.assertEqual(argv[argv.index("--wait-for-capacity") + 1], "600")
        self.assertIn("--no-wait", argv)
        self.assertNotIn("--capacity", argv)
        self.assertEqual(staged["capacity"], "spot")
        self.assertEqual(staged["input"]["label"], "die")
        self.assertEqual(
            staged["input"]["sha256"], hashlib.sha256(b"stub gds bytes\n").hexdigest()
        )

    def test_on_demand_is_passed_to_the_submitter_and_recorded(self):
        """For a job Spot reclaimed, or one that cannot be sharded to fit
        between reclaims: the fleet's own ruling for on-demand capacity."""
        argv, staged, _ = self.submit("--on-demand")
        self.assertEqual(argv[argv.index("--capacity") + 1], "on-demand")
        self.assertEqual(staged["capacity"], "on-demand")

    def test_forwarded_options_reach_the_job_and_the_submitter(self):
        argv, _, _ = self.submit("--workers", "2", "--timeout", "1500", "--wait", "540")
        self.assertEqual(
            [a for a in argv if a.startswith("--shard=")],
            [
                "--shard=layout/precheck/in/die.gds precheck/out --id DEADBEEF "
                "--cob --threads 3 --workers 2"
            ],
        )
        self.assertEqual(argv[argv.index("--timeout") + 1], "1500")
        self.assertEqual(argv[argv.index("--wait") + 1], "540")
        self.assertNotIn("--no-wait", argv)


def klt_help_listing(*present: str) -> str:
    """``klt --help``'s subcommand block, listing only ``present``."""
    return "positional arguments:\n" + "".join(
        f"    {command}\n" for command in present
    )


class CheckPinsTests(unittest.TestCase):
    """``submit``'s pin check: one read of ``toolchain.json``, and a missing
    ``klt`` command stops the submit before anything is staged."""

    def test_check_pins_reads_the_pin_file_once(self):
        pins = toolchain_pin.load()
        help_text = klt_help_listing(*pins["klt_required_commands"])
        with (
            mock.patch.object(toolchain_pin, "load", wraps=toolchain_pin.load) as load,
            mock.patch.object(toolchain_pin, "klt_help", return_value=help_text),
            redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(spot.check_pins(), pins)
        self.assertEqual(load.call_count, 1)

    def test_submit_stops_with_exit_1_when_a_pinned_command_is_missing(self):
        missing, *rest = PINS["klt_required_commands"]
        err = io.StringIO()
        with (
            mock.patch.object(
                toolchain_pin, "klt_help", return_value=klt_help_listing(*rest)
            ),
            mock.patch.object(
                spot, "head_and_clean", side_effect=AssertionError("past the pins")
            ) as next_step,
            redirect_stderr(err),
        ):
            rc = spot.main(["build", "submit", "--dry-run"])
        self.assertEqual(rc, 1)
        next_step.assert_not_called()
        self.assertIn(f"error: klt '{missing}' is required by", err.getvalue())
        self.assertIn("uv tool install " + PINS["klt_install"], err.getvalue())
        self.assertIn(
            "error: toolchain check failed (see the errors above); nothing was submitted",
            err.getvalue(),
        )


class JobScriptTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        stubs = self.root / "stub-bin"
        stubs.mkdir()
        (stubs / "nix").write_text(NIX)
        (stubs / "make").write_text(MAKE)
        for tool in ("klayout", "magic", "yosys", "openroad"):
            (stubs / tool).write_text(f"#!/bin/sh\necho '{tool} stub 1.0'\n")
        for stub in stubs.iterdir():
            stub.chmod(stub.stat().st_mode | 0o755)
        jobs = self.root / "layout" / "jobs"
        jobs.mkdir(parents=True)
        for script in (LAYOUT / "jobs").iterdir():
            if script.is_file():
                (jobs / script.name).write_bytes(script.read_bytes())
        (self.root / "layout" / "toolchain.json").write_bytes(
            (LAYOUT / "toolchain.json").read_bytes()
        )
        (self.root / "layout" / "vendor" / "template").mkdir(parents=True)
        precheck = self.root / "layout" / "vendor" / "precheck"
        precheck.mkdir()
        (precheck / "precheck.py").write_text(PRECHECK)
        self.stub_gds = self.root / "stub.gds"
        self.stub_gds.write_bytes(b"stub gds bytes\n")
        self.log = self.root / "stub.log"
        self.env = {
            **os.environ,
            "PATH": f"{stubs}:{os.environ['PATH']}",
            "STUB_LOG": str(self.log),
            "STUB_GDS": str(self.stub_gds),
            "STUB_PDK_COMMIT": PDK_COMMIT,
        }

    def run_job(self, script, *args, **env):
        return subprocess.run(
            ["bash", f"layout/jobs/{script}", *args],
            cwd=self.root,
            env={**self.env, **env},
            capture_output=True,
            text=True,
            timeout=300,
        )

    def out(self, *parts):
        return json.loads((self.root.joinpath(*parts)).read_text())

    def test_build_passes_every_pin_to_make_and_records_the_gds(self):
        result = self.run_job("build.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        out = self.root / "build" / "out"
        self.assertEqual(
            (out / "chip_top.gds").read_bytes(), self.stub_gds.read_bytes()
        )
        build = self.out("build", "out", "build.json")
        self.assertTrue(build["pass"])
        self.assertEqual(build["target"], "librelane-condensed")
        self.assertEqual(
            build["make"],
            {
                "SLOT": TEMPLATE["slot"],
                "SCL": TEMPLATE["scl"],
                "PAD": TEMPLATE["pad"],
                "SRAM": TEMPLATE["sram"],
            },
        )
        self.assertEqual(
            build["gds"],
            {
                "name": "chip_top.gds",
                "bytes": self.stub_gds.stat().st_size,
                "sha256": hashlib.sha256(self.stub_gds.read_bytes()).hexdigest(),
            },
        )
        self.assertEqual(build["tools"]["nix"], "nix (Nix) " + PINS["nix"]["version"])
        self.assertEqual(
            build["pdk"]["open_pdks_commit_observed"],
            [f"open_pdks {PDK_COMMIT} https://stub"],
        )
        self.assertEqual(
            self.out("build", "out", "metrics.json"),
            {"design__instance__area__uturn": 1},
        )
        invokes = [line.split(" ", 1)[1] for line in self.log.read_text().splitlines()]
        self.assertEqual(
            invokes,
            [
                "clone-pdk SLOT=1x1 SCL=gf180mcu_fd_sc_mcu7t5v0 PAD=gf180mcu_fd_io SRAM=gf180mcu_fd_ip_sram",
                "librelane-condensed SLOT=1x1 SCL=gf180mcu_fd_sc_mcu7t5v0 PAD=gf180mcu_fd_io SRAM=gf180mcu_fd_ip_sram",
            ],
        )

    def test_probe_stops_before_the_flow(self):
        result = self.run_job("build.sh", "--probe")
        self.assertEqual(result.returncode, 0, result.stderr)
        build = self.out("build", "out", "build.json")
        self.assertEqual((build["pass"], build["probe"]), (False, True))
        self.assertNotIn("librelane-condensed", self.log.read_text())

    def phase_names(self, *parts):
        """Every phase phases.txt names but the closing `done` line, which the
        job writes after the record."""
        text = self.root.joinpath(*parts, "phases.txt").read_text()
        names = [line.split(" ", 2)[2].strip() for line in text.splitlines()]
        return [name for name in names if not name.startswith("done")]

    def test_build_wall_seconds_cover_the_flow_itself(self):
        """The last phase has no successor when build.json is written, and it
        is the flow: the phase that takes the hour on the fleet."""
        self.run_job("build.sh")
        wall = self.out("build", "out", "build.json")["wall_seconds"]
        self.assertEqual(set(wall), set(self.phase_names("build", "out")))
        self.assertTrue(all(seconds >= 0 for seconds in wall.values()), wall)

    def test_a_failed_flow_is_a_failed_shard_without_a_gds(self):
        result = self.run_job("build.sh", STUB_FAIL_FLOW="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "build" / "out" / "chip_top.gds").exists())
        self.assertIn(
            "FlowError: stub failure",
            (self.root / "build" / "out" / "console.log").read_text(),
        )
        self.assertIn("FAILED", result.stderr)

    def test_a_pdk_at_another_revision_stops_the_job(self):
        result = self.run_job("build.sh", STUB_PDK_COMMIT="0" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not pin open_pdks", result.stderr)
        self.assertNotIn("librelane-condensed", self.log.read_text())

    def test_precheck_records_the_options_and_the_verdict(self):
        result = self.run_job(
            "precheck.sh",
            "stub.gds",
            "precheck/out",
            "--cob",
            "--id",
            "DEADBEEF",
            "--threads",
            "3",
            "--workers",
            "2",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = self.root / "precheck" / "out"
        verdict = self.out("precheck", "out", "precheck.json")
        self.assertTrue(verdict["pass"])
        self.assertEqual(
            verdict["options"],
            {
                "top": PINS["die"]["top"],
                "slot": PINS["die"]["slot"],
                "id": "DEADBEEF",
                "cob": True,
                "threads": 3,
                "workers": "2",
            },
        )
        seen = self.out("precheck", "out", "flow", "final", "metrics.json")
        self.assertEqual(
            (seen["cob"], seen["id"], seen["threads"], seen["workers"]),
            (True, "DEADBEEF", "3", "2"),
        )
        self.assertEqual(seen["top"], PINS["die"]["top"])
        self.assertEqual(
            verdict["input"],
            {
                "name": "stub.gds",
                "bytes": self.stub_gds.stat().st_size,
                "sha256": hashlib.sha256(self.stub_gds.read_bytes()).hexdigest(),
            },
        )
        self.assertTrue((out / "flow" / "final" / "checker.log").is_file())

    def test_precheck_default_workers_are_bounded_and_the_id_defaults(self):
        self.run_job("precheck.sh", "stub.gds", "precheck/out")
        options = self.out("precheck", "out", "precheck.json")["options"]
        self.assertEqual(
            (options["cob"], options["id"], options["threads"]), (False, "FFFFFFFF", 2)
        )
        self.assertTrue(1 <= int(options["workers"]) <= 8, options["workers"])

    def test_precheck_wall_seconds_cover_the_flow_itself(self):
        self.run_job("precheck.sh", "stub.gds", "precheck/out")
        wall = self.out("precheck", "out", "precheck.json")["wall_seconds"]
        self.assertEqual(set(wall), set(self.phase_names("precheck", "out")))
        self.assertTrue(all(seconds >= 0 for seconds in wall.values()), wall)

    def test_a_failing_precheck_is_a_failing_verdict_with_its_evidence(self):
        result = self.run_job(
            "precheck.sh", "stub.gds", "precheck/out", STUB_PRECHECK_RC="1"
        )
        self.assertEqual(result.returncode, 1)
        verdict = self.out("precheck", "out", "precheck.json")
        self.assertEqual((verdict["pass"], verdict["exit_code"]), (False, 1))
        self.assertTrue(
            (
                self.root / "precheck" / "out" / "flow" / "final" / "metrics.json"
            ).is_file()
        )

    def test_nix_env_tools_records_stub_toolchain(self):
        result = self.run_job("nix-env.sh", "tools")
        self.assertEqual(result.returncode, 0, result.stderr)
        tools = json.loads(result.stdout)
        self.assertEqual(tools["nix"], "nix (Nix) " + PINS["nix"]["version"])
        self.assertEqual(tools["klayout"], "klayout stub 1.0")
        self.assertTrue(tools["paths"]["klayout"].endswith("/stub-bin/klayout"))

    def test_setup_ignores_subdirectories_under_layout_jobs(self):
        layout_copy = self.root / "layout-with-cache"
        (layout_copy / "jobs" / "__pycache__").mkdir(parents=True)
        for script in (LAYOUT / "jobs").iterdir():
            if script.is_file():
                (layout_copy / "jobs" / script.name).write_bytes(script.read_bytes())
        (layout_copy / "toolchain.json").write_bytes(
            (LAYOUT / "toolchain.json").read_bytes()
        )
        probe = JobScriptTests("test_nix_env_tools_records_stub_toolchain")
        with mock.patch(f"{__name__}.LAYOUT", layout_copy):
            try:
                probe.setUp()
            finally:
                probe.doCleanups()

    def test_jobs_delegate_to_shared_helper_without_inline_python_heredocs(self):
        for name in ("nix-env.sh", "build.sh", "precheck.sh"):
            text = (LAYOUT / "jobs" / name).read_text()
            self.assertNotIn("<<'PY'", text, name)
            self.assertNotIn("<<PY", text, name)
        helper = self.root / "layout" / "jobs" / "summary.py"
        self.assertTrue(helper.is_file())
        result = subprocess.run(
            ["python3", str(helper), "pin", "wafer_space.template.target"],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "librelane-condensed")


if __name__ == "__main__":
    unittest.main()
