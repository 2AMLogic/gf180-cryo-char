"""Smallest nonzero recorded current or capacitance in selected MPW-5 MDM classes."""

import argparse
import hashlib
import math
from pathlib import Path
from zipfile import ZipFile


def measurement_class(path):
    directory, *rest = path.removeprefix("MPW-5 Test Tile/").split("/")
    if directory == "transistormodule":
        return "array FET", {"id", "ig", "ib"}
    if directory == "diode":
        return ("diode I–V", {"id1", "id2"}) if rest[0] == "iv" else ("diode C–V", {"cbc"})
    if directory == "cap":
        name = rest[-1].lower()
        group = "MIM" if "mim" in name else "overlap MOS" if "ovl" in name else "area MOS"
        return group, {"cbc"}
    if directory in {"pres", "resmet", "viadaisy"}:
        return directory, {"is1", "is2"}
    return None, set()


def minimum(stream, outputs):
    columns = []
    lowest = math.inf
    for line in stream:
        fields = line.decode().strip().split()
        if not fields:
            continue
        if fields[0].startswith("#"):
            columns = [i for i, name in enumerate(fields) if name.lower() in outputs]
        elif fields[0] in {"BEGIN_DB", "END_DB"}:
            columns = []
        elif columns and fields[0] != "ICCAP_VAR":
            for i in columns:
                magnitude = abs(float(fields[i]))
                if 0 < magnitude < lowest:
                    lowest = magnitude
    return lowest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    expected = "3a2cd00d40a059ade77b36afbeb45bc819e77ca80858668226809e3e932a03e3"
    if hashlib.sha256(args.archive.read_bytes()).hexdigest() != expected:
        raise SystemExit("unexpected MPW-5 archive checksum")
    smallest = {}
    with ZipFile(args.archive) as archive:
        for name in archive.namelist():
            if not name.endswith(".mdm"):
                continue
            group, outputs = measurement_class(name)
            if group is None:
                continue
            with archive.open(name) as stream:
                value = minimum(stream, outputs)
            if value < smallest.get(group, (math.inf, ""))[0]:
                smallest[group] = (value, name)
    for group, (value, source) in sorted(smallest.items()):
        print(f"{group:12s} {value:.7g}  {source}")


if __name__ == "__main__":
    main()
