# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14"]
# ///
"""Check the physical well and body-contact geometry for the eight isolated NFETs."""

import argparse
import re
import sys
from pathlib import Path

import klayout.db as db

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    args = parser.parse_args()
    library = args.pdk / "libs.tech/klayout/tech/pymacros/klayout_api_cells"
    sys.path.insert(0, str(library.resolve()))
    from draw_fet import draw_nfet

    checked = set()
    for row in (HERE / "structure-map.md").read_text().splitlines():
        if "| ISOFETs!" not in row:
            continue
        code, *_, target = (entry.strip() for entry in row.strip("|").split("|"))
        if not target.startswith("nfet_"):
            continue
        model, width, length = re.match(
            r"(nfet_\w+), ([0-9.]+) × ([0-9.]+)", target
        ).groups()
        for isolated in (True, False):
            layout = db.Layout()
            layout.dbu = 0.001
            cell = draw_nfet(
                layout,
                float(length),
                float(width),
                0.44,
                1,
                0.36,
                "Bulk Tie",
                "3.3V" if model == "nfet_03v3" else "6V",
                isolated,
                isolated,
            )

            def mask(layer):
                return db.Region(cell.begin_shapes_rec(layout.layer(layer, 0))).merged()

            well, deep, active, implant, contacts = (
                mask(n) for n in (204, 12, 22, 31, 33)
            )
            if isolated:
                if (
                    well.is_empty()
                    or deep.is_empty()
                    or not (well.sized(2500) - deep).is_empty()
                ):
                    raise ValueError(f"Missing enclosed LVPWELL at {code}")
                if (well & active & implant & contacts).is_empty():
                    raise ValueError(f"No contacted P+ body inside LVPWELL at {code}")
                if ((active & implant) - deep).is_empty():
                    raise ValueError(
                        f"No outer guard diffusion outside DNWELL at {code}"
                    )
            elif not deep.is_empty():
                raise ValueError(
                    f"Substrate-body control unexpectedly isolated at {code}"
                )
        checked.add(int(code))
    if checked != set(range(401, 405)) | set(range(409, 413)):
        raise ValueError(f"Unexpected isolated NFET map {checked}")
    print(
        "Verified eight body islands, their P+ contacts and outer guard diffusion, plus eight substrate controls."
    )


if __name__ == "__main__":
    main()
