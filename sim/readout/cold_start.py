"""Replay the published reference measurements against the wafer.space PDK."""
import hashlib
import math
import os
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen


HERE = Path(__file__).resolve().parent
REVISION = "ac7d8696de96a4d708e768b607ae37f02207a354"
BASE = f"https://raw.githubusercontent.com/wafer-space/gf180mcu/{REVISION}/gf180mcuD/"
MODEL_FILES = {
    "libs.tech/ngspice/design.ngspice": "091cb530bf85160a1f07878fb81f789ca367d018991c8ab41a584cd1a85c6692",
    "libs.tech/ngspice/sm141064.ngspice": "6edba54d23b38a2c60f8ffdbaa3eb75a7568c615e4820808969bd1121b77b1aa",
    "libs.ref/gf180mcu_fd_io/spice/gf180mcu_fd_io.spice": "710732fd6a69e165caa2c29e4cdf81b11af41da32705fcd860b7ecfb09630dd1",
}


def copy_models(directory):
    source = os.environ.get("CRYO_SHUTTLE_PDK")
    for name, expected in MODEL_FILES.items():
        if source:
            data = (Path(source) / name).read_bytes()
        else:
            with urlopen(BASE + name, timeout=30) as response:
                data = response.read()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"shuttle PDK checksum mismatch for {name}")
        target = directory / "pdk" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def simulate(directory, template, **values):
    text = template.read_text()
    for key, value in values.items():
        text = text.replace(f"@{key}@", str(value))
    deck = directory / "bench.cir"
    deck.write_text(text)
    cmd = [os.environ.get("NGSPICE", "ngspice"), "-n", "-b", deck.name]
    proc = subprocess.run(cmd, cwd=directory, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode or "Error:" in proc.stdout:
        hint = ""
        if template.name == "pad.spice" and "unknown parameter (e9)" in proc.stdout:
            hint = "Set NGSPICE to ngspice 46. Version 47 rejects the pinned pad model’s rail capacitor. "
        raise RuntimeError(f"{hint}{template.name} {values} failed:\n{proc.stdout}")
    return proc.stdout


def in_range(name, value, low, high):
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name}: got {value}, expected {low} to {high}")


def current_sweep(directory, filename, columns, count, first, step):
    output = directory / filename
    rows = [list(map(float, line.split())) for line in output.read_text().splitlines()]
    output.unlink()  # A later simulation must supply its own sweep.
    if len(rows) != count or any(len(row) != columns for row in rows):
        raise ValueError(f"incomplete {filename}, expected {count} rows of {columns} values")
    for i, row in enumerate(rows):
        if not all(map(math.isfinite, row)) or not math.isclose(row[0], first + i * step, abs_tol=1e-7):
            raise ValueError(f"invalid bias point or current at row {i} of {filename}")
    return rows


def open_switch(directory):
    out = simulate(directory, HERE.parents[1] / "spec/switch-reference.spice")
    readings = [float(match) * 1e15 for match in re.findall(r"^i\(vsense\)\s*=\s*(\S+)", out, re.M)]
    if len(readings) != 2:
        raise ValueError(f"expected both far-terminal controls, got {readings}")
    in_range("full-bias open switch (fA)", readings[0], 67, 69)
    in_range("zero-bias open switch (fA)", readings[1], 62, 65)
    print(f"Single open switch: {readings[0]:.3f} / {readings[1]:.3f} fA at far=3.3 / 0 V")


def check_guard_bias(rows, far, error):
    for requested, _, far_voltage, tracking_error, sense_voltage in rows:
        for name, actual, expected in (
            ("far terminal", far_voltage, far),
            ("guard tracking error", tracking_error, error),
            ("sense terminal", sense_voltage, requested),
        ):
            if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-8):
                raise ValueError(f"{name}: measured {actual} V, requested {expected} V")


def guarded_switch(directory):
    for gmin, low, high in [("1e-12", 1.9, 2.4), ("1e-15", 0.10, 0.18), ("1e-19", 0.10, 0.18)]:
        peak = 0.0
        for far in (0, 3.3):
            for error in (-0.001, 0, 0.001):
                simulate(directory, HERE / "guard.spice", GMIN=gmin, FAR=far, ERROR=error)
                rows = current_sweep(directory, "guard.dat", 5, 201, 0.001, 0.01649)
                check_guard_bias(rows, far, error)
                peak = max(peak, max(abs(row[1]) for row in rows) * 1e15)
        in_range("single guarded branch max (fA)", peak, low, high)
        print(f"Guarded branch: {peak:.4f} fA max over 1,206 points at gmin={gmin}")


def analog_pad(directory):
    for gmin in ("1e-12", "1e-15", "1e-18", "1e-19"):
        out = simulate(directory, HERE / "pad.spice", GMIN=gmin)
        cap = re.search(r"^cpad\s*=\s*(\S+)", out, re.M)
        open_cap = re.search(r"^copen\s*=\s*(\S+)", out, re.M)
        if not cap or not open_cap or float(open_cap[1]) != 0:
            raise ValueError("missing 10 kHz measurement or nonzero disconnected AC control")
        cap_ff = float(cap[1]) * 1e15
        in_range("pad capacitance (fF)", cap_ff, 870, 880)
        rows = current_sweep(directory, "raw-pad.dat", 3, 67, 0, 0.05)
        if any(row[2] != 0 for row in rows):
            raise ValueError("nonzero ideal disconnected control")
        peak_fa = max(abs(row[1]) for row in rows) * 1e15
        # Only the large default numerical shunt is a quantified DC check.
        # The tight-gmin residual depends on solver precision.
        if gmin == "1e-12":
            in_range("default-shunt pad current (fA)", peak_fa, 3200, 3400)
        else:
            in_range("tight-shunt numerical control (fA)", peak_fa, 0, 10)
        print(f"Unconnected pad: {cap_ff:.2f} fF, {peak_fa:.2f} fA max at gmin={gmin}")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp:
        work = Path(temp)
        copy_models(work)
        open_switch(work)
        guarded_switch(work)
        analog_pad(work)
