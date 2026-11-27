# /// script
# requires-python = ">=3.11,<3.12"
# dependencies = ["klayout==0.30.14", "gdsfactory==7.27.2"]
# ///
"""Check the physical well and body-contact geometry for the eight isolated NFETs."""

import argparse
from contextlib import chdir
import re
import sys
import tempfile
from pathlib import Path

import klayout.db as db
from gdsfactory.config import CONF

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdk", type=Path, required=True)
    args = parser.parse_args()
    library = args.pdk.resolve() / "libs.tech/klayout/tech/pymacros"
    sys.path.insert(0, str(library))
    from cells.fet import nfet

    # The PDK places abutting N+ and P+ masks by connecting rectangle ports
    # on different implant layers. Keep the warning and check the actual masks.
    CONF.on_layer_missmatch = "warn"
    with tempfile.TemporaryDirectory() as scratch, chdir(scratch):
        verify(nfet)


def verify(nfet):
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
            device = nfet()
            pcell = layout.register_pcell("nfet", device)
            requested = dict(
                w_gate=float(width),
                l_gate=float(length),
                ld=0.52,
                nf=1,
                grw=0.38,
                bulk="Bulk Tie",
                con_bet_fin=True,
                sd_con_col=1,
                gate_con_pos="top",
                volt="3.3V" if model == "nfet_03v3" else "6V",
                deepnwell=isolated,
                pcmpgr=isolated,
            )
            declaration = device.get_parameters()
            names = [parameter.name for parameter in declaration]
            values = [requested.get(p.name, p.default) for p in declaration]
            coerced = device.coerce_parameters(layout, values)
            if any(coerced[names.index(k)] != v for k, v in requested.items()):
                raise ValueError(
                    f"The foundry PCell changes the mapped geometry at {code}"
                )
            cell = layout.cell(layout.add_pcell_variant(pcell, coerced))

            def mask(layer):
                return db.Region(cell.begin_shapes_rec(layout.layer(layer, 0))).merged()

            well, deep, active, implant, contacts = (
                mask(n) for n in (204, 12, 22, 31, 33)
            )
            gate = (active & mask(30)).merged()
            if (
                gate.count() != 1
                or gate.bbox().width() != round(float(length) / layout.dbu)
                or gate.bbox().height() != round(float(width) / layout.dbu)
            ):
                raise ValueError(
                    f"Drawn gate W/L differs from the workbook port at {code}"
                )
            if int(code) in (401, 403):
                # The negative control requests the original, too-narrow source width.
                original = list(values)
                original[names.index("w_gate")] = 0.36
                if (
                    device.coerce_parameters(layout, original)[names.index("w_gate")]
                    != 0.42
                ):
                    raise ValueError(f"Missing body-tie width clamp at {code}")
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
