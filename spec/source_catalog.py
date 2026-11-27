"""Read the NIST MPW-5 workbook and check the source columns in the structure map."""

import argparse
import hashlib
import io
import re
from pathlib import Path
from zipfile import ZipFile

from openpyxl import load_workbook


ARCHIVE_SHA = "3a2cd00d40a059ade77b36afbeb45bc819e77ca80858668226809e3e932a03e3"
BOOK_SHA = "656e5c42855336081882e8cec04236caf87850556e5ed69931d0afeb31ef243c"
FET_MODULES = ["nthin", "pthin", "nthin_lvt", "pthin_lvt", "nthick", "pthick", "nnative"]
PREFIX = {
    "ISOFETs": "ISOFet", "MOSCAPs": "MOSCAP", "MOSCAPOVLs": "MOSCAPOVL",
    "AreaDiodes": "AreaDiode", "AreaMIMC": "AreaMIMC", "PeriMIMC": "PeriMIMC",
    "PrRES": "PRES", "ResMet": "Restmet", "VDaisy": "VDAISY",
}


def catalog(archive_path):
    """Yield sheet, source cell(s), identifier, device, geometry and terminal wiring."""
    archive = Path(archive_path).read_bytes()
    if hashlib.sha256(archive).hexdigest() != ARCHIVE_SHA:
        raise ValueError("unexpected MPW-5 archive checksum")
    with ZipFile(io.BytesIO(archive)) as z:
        book = z.read("MPW-5 Test Tile/Module Layout Coding.xlsx")
    if hashlib.sha256(book).hexdigest() != BOOK_SHA:
        raise ValueError("unexpected layout workbook checksum")
    workbook = load_workbook(io.BytesIO(book), data_only=True)

    for sheet in workbook:
        group = offset = 0
        for row in sheet.iter_rows():
            if len(row) < 2 or row[1].value is None:
                continue
            first, desc = row[0].value, str(row[1].value).strip()
            cell = row[1].coordinate
            if first in ("Device", "Device Name"):
                group += 1
                device = desc
                continue
            if desc.startswith("devices in module"):
                match = re.search(r"\+(\d+)", str(first))
                offset = int(match[1]) if match else 0
                continue
            contacts = [(c.column - 2, str(c.value)) for c in row[2:] if c.value is not None]
            pins = " ".join(f"{n}={value}" for n, value in contacts)
            if sheet.title == "FETModules":
                if first is not None:
                    bank = int(first) + offset
                drain = next(n for n, value in contacts if value == "D")
                ident = f"{FET_MODULES[group-1]}/{bank}_{drain-3}"
                yield sheet.title, cell, ident, device, desc, pins
            elif sheet.title in ("ISOFETs", "PrRES"):
                # Two separately probeable devices share a worksheet row.
                for number, width, length in re.findall(r"R(\d+): W=([\d.]+), L=([\d.]+)", desc):
                    ident = f"{PREFIX[sheet.title]}{group}/R{number}"
                    own_pins = " ".join(f"{n}={v}" for n, v in contacts if number in v)
                    yield sheet.title, cell, ident, device, f"W={width} L={length}", own_pins
            elif sheet.title == "ROSC":
                # Two pin rows describe the n- and p-device of one inverter loop.
                if first == 2:
                    top_cell, top_desc, top_pins = cell, desc, pins
                elif first == 1:
                    yield sheet.title, f"{top_cell},{cell}", device, device, f"{top_desc}, {desc}", f"R2 {top_pins}; R1 {pins}"
                else:
                    raise ValueError(f"unexpected oscillator row: {cell}")
            else:
                name = PREFIX[sheet.title] + str(group)
                if sheet.title == "MOSCAPOVLs":
                    name += f"/R{first}"
                yield sheet.title, cell, name, device, desc, pins


def source_columns(rows):
    for address, (sheet, cell, ident, device, geom, pins) in enumerate(rows, start=1):
        # Stable select codes survive dropped structures and individual freeze cuts.
        yield f"| {address} | {sheet}!{cell} | {ident} | {device} | {geom} | {pins} |"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--check", type=Path, help="check every source row in the reviewed Markdown map")
    args = parser.parse_args()
    expected = list(source_columns(catalog(args.archive)))
    if args.check is None:
        print("\n".join(expected))
        return
    mapped = [line for line in args.check.read_text().splitlines() if re.match(r"^\| \d+ \|", line)]
    if len(mapped) != len(expected):
        raise SystemExit(f"expected {len(expected)} map rows, found {len(mapped)}")
    for prefix, line in zip(expected, mapped):
        if not line.startswith(prefix + " "):
            raise SystemExit(f"source columns disagree at {prefix}")
    print(f"{len(mapped)} rows match the pinned workbook")


if __name__ == "__main__":
    main()
