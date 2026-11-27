# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14", "klayout-tools==0.9.2"]
# ///
"""Measure the small-signal capacitance of every extracted MIM bank via klt sim."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile

from build import HERE
from verify import KLT, check_toolchain, run

SPECIMENS = (
    (452, "AreaMIMC1"),
    (453, "AreaMIMC2"),
    (454, "PeriMIMC1"),
    (455, "PeriMIMC2"),
)
CORNERS = ("mimcap_ff", "mimcap_typical", "mimcap_ss")
BIASES_V = (0, 1.65, 3.3)
TEMPS_C = (-40, 25, 125)
PDK_REVISION = "open_pdks f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7"
MODELS = {
    "design.ngspice": "7e222f050318388f37543a64fbd0be55cc15e4b93f57501a09f7c159c4c9e561",
    "sm141064.ngspice": "f6f4a96e18fc5ad11270ad3451aaecc7ac37fc81eb61e15b0d7d94c7bc594a24",
    "sm141064_mim.ngspice": "9b85cd009968d9aeb6b61046b24a63f39d6a463c4e4aee3949c8fd183c06666f",
}
RECORDS_DIR = HERE / "records"


def latest_record_dir():
    candidates = sorted(p.parent for p in RECORDS_DIR.glob("*/manifest.json"))
    if not candidates:
        raise FileNotFoundError(f"No recorded klt sim evidence under {RECORDS_DIR}")
    return candidates[-1]


def mint_record_dir():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    sha = subprocess.check_output(
        ["git", "-C", HERE, "rev-parse", "--short=7", "HEAD"], text=True
    ).strip()
    target = RECORDS_DIR / f"{stamp}-{sha}-ac"
    target.mkdir(parents=True, exist_ok=False)
    return target


def build_sim_inputs(work, pdk, verified, expected_identity=None, backend="batch"):
    tb_lines = [
        "* GF180D extracted MIM specimen admittance bench (10 kHz, 10 mV AC)",
    ]
    specimen_meta = {}
    measurements = []
    for code, nist_id in SPECIMENS:
        key = str(code)
        gds = HERE / f"mim_{code}.gds"
        gds_sha = hashlib.sha256(gds.read_bytes()).hexdigest()
        if gds_sha != verified[key]["sha256"]:
            raise ValueError(
                f"GDS stream digest mismatch against verification.json for mim_{code}.gds"
            )
        tb_lines.append(f"* {nist_id} (code {code}): mim_{code}.gds sha256={gds_sha}")

    tb_lines.extend([
        ".param sw_stat_global=0",
        "Vbias bias 0 DC 0",
    ])
    for code, nist_id in SPECIMENS:
        key = str(code)
        name = f"mim_{code}"
        spice_path = work / f"{name}.spice"
        run(
            [
                "extract",
                HERE / f"{name}.gds",
                "--top",
                name,
                "--deck",
                "gf180mcu",
                "--pdk",
                "gf180mcuD",
                "--pdk-root",
                pdk.parent,
                "--deck-option",
                "metal_top=11K",
                "--pins",
                "top,bot",
                "--rename-declared-pins",
                "-o",
                spice_path,
            ]
        )
        spice_sha = hashlib.sha256(spice_path.read_bytes()).hexdigest()
        src = f"vdrive_{code}"
        node = f"top_{code}"
        tb_lines.extend([
            f'.include "{name}.spice"',
            f"Vdrive_{code} {node} bias DC 0 AC 0.01",
            f"Xbank_{code} {node} 0 {name}",
        ])
        area_pf = 0.002 * verified[key]["total_plate_area_um2"]
        measurements.append({
            "name": nist_id,
            "spec_row": key,
            "expr": f"real(-imag(i({src}))/(2*pi*10000*0.01)*1e12)",
            "unit": "pF",
            "limits": {
                "min": round(0.85 * area_pf, 6),
                "max": round(1.25 * area_pf, 6),
            },
        })
        specimen_meta[nist_id] = {
            "select_code": code,
            "cell": name,
            "gds_sha256": verified[key]["sha256"],
            "extracted_spice_sha256": spice_sha,
            "units": verified[key]["units"],
            "unit_side_um": verified[key]["unit_side_um"],
            "total_plate_area_um2": verified[key]["total_plate_area_um2"],
            "total_plate_perimeter_um": verified[key]["total_plate_perimeter_um"],
        }

    (work / "tb.spice").write_text("\n".join(tb_lines) + "\n")
    request = {
        "netlist": "tb.spice",
        "netlist_source": "extracted",
        "engine": "ngspice",
        "backend": backend,
        "models": {
            "pdk": "gf180mcuD",
            "lib": "libs.tech/ngspice/sm141064.ngspice",
            "param_file": "libs.tech/ngspice/design.ngspice",
        },
        "corners": {
            "process": list(CORNERS),
            "supply_v": {"vbias": list(BIASES_V)},
            "temperature_c": list(TEMPS_C),
        },
        "analysis": {"kind": "ac", "args": "lin 1 10k 10k"},
        "measurements": measurements,
        "options": {
            "ngspice_init": ["set numdgt=12"],
            "stage_model_inputs": True,
            "pdk_revision": PDK_REVISION,
            "timeout_s": 60,
        },
    }
    if backend == "batch":
        request["batch"] = {"capacity_wait_s": 600}
    if expected_identity is not None:
        request["expect_netlist_identity"] = expected_identity
    req_path = work / "request.json"
    req_path.write_text(json.dumps(request, indent=2) + "\n")
    return req_path, specimen_meta


def extract_rows(envelope):
    expected_corners = len(CORNERS) * len(BIASES_V) * len(TEMPS_C)
    if (
        envelope.get("status") != "pass"
        or envelope.get("corner_count") != expected_corners
        or envelope.get("failed") != 0
        or envelope.get("errored") != 0
        or envelope.get("inconclusive") != 0
        or envelope.get("diagnostic_counts", {}).get("by_severity", {}).get("error", 0) != 0
    ):
        raise ValueError(
            f"klt sim sweep did not pass cleanly: status={envelope.get('status')!r}"
        )
    by_point = {}
    for corner in envelope["corners"]:
        if corner["status"] != "pass":
            raise ValueError(f"Corner {corner['corner_id']} did not pass")
        proc = corner["process"]
        temp = corner["temperature_c"]
        bias = corner["supply_v"]["vbias"]
        bias_key = int(bias) if float(bias).is_integer() else bias
        temp_key = int(temp) if float(temp).is_integer() else temp
        vals = {m["name"]: m["value"] for m in corner["measurements"]}
        for code, nist_id in SPECIMENS:
            val = vals.get(nist_id)
            if val is None or not math.isfinite(val) or not (0 < val < 1e6):
                raise ValueError(f"Invalid capacitance for {nist_id} at {corner['corner_id']}")
            by_point[(code, proc, temp_key, bias_key)] = (nist_id, val)

    rows = []
    for code, nist_id in SPECIMENS:
        for proc in CORNERS:
            for temp in TEMPS_C:
                for bias in BIASES_V:
                    _, cap_pf = by_point[(code, proc, temp, bias)]
                    rows.append({
                        "code": code,
                        "nist_id": nist_id,
                        "mim_corner": proc,
                        "temp_c": temp,
                        "bias_v": bias,
                        "capacitance_pf": cap_pf,
                    })
    return rows


def check_against_csv(rows):
    with (HERE / "measurements.csv").open() as stream:
        saved = list(csv.DictReader(stream))
    if len(saved) != len(rows):
        raise ValueError("AC coverage changed relative to measurements.csv")
    for prior, fresh in zip(saved, rows):
        if any(
            str(fresh[k]) != prior[k]
            for k in ("code", "mim_corner", "temp_c", "bias_v")
        ) or not math.isclose(
            fresh["capacitance_pf"], float(prior["capacitance_pf"]), rel_tol=1e-5
        ):
            raise ValueError(f"AC point differs from measurements.csv: {fresh}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", required=True, type=Path)
    parser.add_argument(
        "--backend",
        default=os.getenv("KLT_SIM_BACKEND", "batch") or "batch",
        help="klt sim execution backend (default: $KLT_SIM_BACKEND or batch)",
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="write a new append-only klt sim evidence record under layout/mim/records/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate extraction, netlist identity and klt sim staging without running SPICE",
    )
    args = parser.parse_args()
    pdk = args.pdk.resolve()
    check_toolchain(KLT, pdk)
    models = pdk / "libs.tech/ngspice"
    for file, sha in MODELS.items():
        if hashlib.sha256((models / file).read_bytes()).hexdigest() != sha:
            raise ValueError(f"Unexpected model {file}")

    verified = json.loads((HERE / "verification.json").read_text())
    prior_manifest = None
    expected_identity = None
    if not args.record and RECORDS_DIR.exists():
        rec_dir = latest_record_dir()
        prior_manifest = json.loads((rec_dir / "manifest.json").read_text())
        expected_identity = prior_manifest["netlist_identity"]

    with tempfile.TemporaryDirectory() as scratch:
        work = Path(scratch)
        req_path, specimen_meta = build_sim_inputs(
            work,
            pdk,
            verified,
            expected_identity=expected_identity,
            backend=args.backend,
        )
        cmd = [KLT, "sim", req_path, "--backend", args.backend, "--format", "json"]
        if args.backend == "batch":
            cmd.extend(["--wait-for-capacity", "600"])
        if args.dry_run:
            cmd.append("--dry-run")
        report_copy = work / "sim.envelope.json"
        if not args.dry_run:
            cmd.extend(["--report-out", report_copy])

        env = dict(os.environ, PDK_ROOT=str(pdk.parent))
        proc = subprocess.run(cmd, env=env, text=True, capture_output=True)
        if proc.returncode != 0:
            raise ValueError(
                f"klt sim exited {proc.returncode}: {proc.stdout[-1000:]} {proc.stderr[-600:]}"
            )
        envelope = json.loads(proc.stdout)
        if args.dry_run:
            print(
                f"Validated klt sim request ({envelope['unit_count']} corners, backend={envelope['backend']})."
            )
            return

        rows = extract_rows(envelope)
        check_against_csv(rows)

        if args.record:
            rec_dir = mint_record_dir()
            envelope_bytes = report_copy.read_bytes()
            (rec_dir / "sim.envelope.json").write_bytes(envelope_bytes)
            by_nist = {}
            for row in rows:
                entry = by_nist.setdefault(
                    row["nist_id"],
                    {**specimen_meta[row["nist_id"]], "points": []},
                )
                entry["points"].append({
                    "mim_corner": row["mim_corner"],
                    "temp_c": row["temp_c"],
                    "bias_v": row["bias_v"],
                    "capacitance_pf": row["capacitance_pf"],
                })
            manifest = {
                "schema_version": 1,
                "record_id": rec_dir.name,
                "stimulus": {"frequency_hz": 10000, "ac_amplitude_v": 0.01},
                "pdk_revision": PDK_REVISION,
                "models_sha256": MODELS,
                "netlist_identity": envelope["environment"]["netlist_identity"],
                "envelope_file": "sim.envelope.json",
                "envelope_sha256": hashlib.sha256(envelope_bytes).hexdigest(),
                "backend": envelope["environment"]["backend"],
                "remote_job_id": (envelope["environment"].get("remote") or {}).get("job_id"),
                "structures": by_nist,
            }
            (rec_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            print(
                f"Recorded {len(rows)} extracted AC measurements in {rec_dir.relative_to(HERE.parents[1])} "
                f"(backend={args.backend}, remote_job_id={manifest['remote_job_id']})."
            )
            return

        if prior_manifest is not None:
            prior_env = json.loads((latest_record_dir() / prior_manifest["envelope_file"]).read_text())
            prior_rows = extract_rows(prior_env)
            for saved_row, fresh_row in zip(prior_rows, rows):
                if not math.isclose(
                    fresh_row["capacitance_pf"], saved_row["capacitance_pf"], rel_tol=1e-5
                ):
                    raise ValueError(f"AC point differs from recorded envelope: {fresh_row}")
        print(
            f"Replayed {len(rows)} extracted AC measurements via klt sim ({args.backend}) at 10 kHz and 10 mV."
        )


if __name__ == "__main__":
    main()
