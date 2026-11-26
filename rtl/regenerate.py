"""Regenerate or verify the GF180D control netlist and exercise both designs."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from importlib.metadata import version
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
LIB = "gf180mcu_fd_sc_mcu7t5v0"
CELL_DIR = f"libs.ref/{LIB}"
PDK_REVISION = "ac7d8696de96a4d708e768b607ae37f02207a354"
FILES = {
    f"lib/{LIB}__tt_025C_3v30.lib": "f9dee07cf158324934b0c59144d970a2e8313f43533ede6283ec3c136f82fe53",
    f"verilog/{LIB}.v": "9a21c5f98200acfe77d8ba52067164e0802284dc1c1e117f0e64fb6ac42eb64b",
    "verilog/primitives.v": "ccc0f447f71ce35c635e08d49eb0ed77aa2ec91cf31d8e3e45a246114d3cae92",
}


def install_library(pdk):
    offline = os.environ.get("CRYO_SHUTTLE_PDK")
    for filename, digest in FILES.items():
        relative = f"{CELL_DIR}/{filename}"
        if offline:
            data = (Path(offline) / relative).read_bytes()
        else:
            url = f"https://raw.githubusercontent.com/wafer-space/gf180mcu/{PDK_REVISION}/gf180mcuD/{relative}"
            with urlopen(url, timeout=45) as stream:
                data = stream.read()
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f"shuttle PDK checksum mismatch for {relative}")
        path = pdk / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (pdk / "libs.tech").mkdir()


def simulate(working, sources):
    image = working / "readout.vvp"
    subprocess.run(["iverilog", "-g2012", "-DFUNCTIONAL", "-s", "tb_ring_readout",
                    "-o", image, ROOT / "verification/tb_ring_readout.v", *sources], check=True)
    subprocess.run(["vvp", image], check=True)


def generate(working, check):
    for pin in ("signoff/klt-pin.txt", "rtl/synth-pin.txt"):
        package, required = (ROOT / pin).read_text().strip().split("==")
        if version(package) != required:
            raise ValueError(f"install {package}=={required} from {pin}")
    yosys = shutil.which("yowasp-yosys")
    if not yosys:
        raise ValueError("install the synthesis pin and add its executable to PATH")
    (working / "yosys").symlink_to(yosys)
    pdk = working / "models/gf180mcuD"
    install_library(pdk)
    env = dict(os.environ, PATH=str(working) + os.pathsep + os.environ["PATH"])
    rtl = working / "rtl"
    rtl.mkdir()
    request = ROOT / "rtl/synth-request.json"
    shutil.copyfile(request, rtl / request.name)
    for source in json.loads(request.read_text())["sources"]:
        shutil.copyfile(ROOT / "rtl" / source, rtl / source)
    result = subprocess.run(
        ["klt", "synthesize", "rtl/synth-request.json", "--pdk", pdk.name,
         "--pdk-root", pdk.parent, "--format", "json"],
        cwd=working, env=env, check=True, stdout=subprocess.PIPE, text=True,
    )
    report = json.loads(result.stdout)
    if (report["status"] != "ok" or report["blackbox_modules"] or
            report["structural"]["has_critical"] or report["structural"]["latches"] or
            not report["instance_count"] or
            any(not name.startswith(LIB + "__") for name in report["instance_counts_by_type"])):
        raise ValueError("controller did not fully map to the GF180 digital library")
    if report["provenance"]["deck"]["content_hash"] != "sha256:" + FILES[f"lib/{LIB}__tt_025C_3v30.lib"]:
        raise ValueError("wrong synthesis library")
    # KLT redacts absolute paths when run outside a Git checkout.
    mapped = rtl / ".klt/synthesize" / report["run_id"] / "cryo_char_ctrl_synth.v"
    if hashlib.sha256(mapped.read_bytes()).hexdigest() != report["netlist_sha256"].removeprefix("sha256:"):
        raise ValueError("synthesized netlist and KLT report differ")
    target = ROOT / "rtl/cryo_char_ctrl.gl.v"
    simulate(working, [ROOT / "rtl/selector.v", ROOT / "rtl/cryo_char_ctrl.v"])
    models = pdk / CELL_DIR / "verilog"
    simulate(working, [mapped, models / "primitives.v", models / f"{LIB}.v"])
    if check:
        if target.read_bytes() != mapped.read_bytes():
            raise ValueError(f"stale gate-level netlist: regenerate {target.name}")
    else:
        shutil.copyfile(mapped, target)
    print(f"{report['instance_count']} mapped cells, {report['area_um2']:.4f} µm² cell area")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as scratch:
        generate(Path(scratch), args.check)
