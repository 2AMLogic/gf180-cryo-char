# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14"]
# ///
"""Export origin-aligned MIM streams and the four-wire routing abstract."""

import argparse
from pathlib import Path

import klayout.db as db
from build import CODES, HERE, options


def pin_windows(width, height):
    # The 0.8 µm M3 and M5 spines form the west and east outline.
    # Open each access at the side for GF180D's horizontal M3/M5 routing.
    windows = {}
    for pair, layer, x in ((1, "Metal5", width - 800), (2, "Metal3", 0)):
        for role, y in (("F", 2000), ("S", height - 6000)):
            windows[f"{role}{pair}"] = (layer, db.Box(x, y, x + 800, y + 4000))
    return windows


def rect(box):
    return "RECT " + " ".join(f"{v / 1000:.3f}" for v in
                              (box.left, box.bottom, box.right, box.top)) + " ;"


def export(code, output):
    stem = f"mim_{code}"
    layout = db.Layout()
    layout.read(str(HERE / f"{stem}.gds"))
    child = layout.top_cell()
    if layout.dbu != 0.001 or child.name != stem:
        raise ValueError(f"Unexpected source units or top for {stem}")
    bounds = child.bbox()
    macro = layout.create_cell(f"{stem}_kelvin")
    macro.insert(db.CellInstArray(child.cell_index(), db.Trans(-bounds.left, -bounds.bottom)))
    layout.write(str(output / f"{macro.name}.gds"), options())

    outline = macro.bbox()
    width, height = outline.width(), outline.height()
    pins = pin_windows(width, height)
    lines = [
        f"MACRO {macro.name}", "  CLASS BLOCK ;", "  ORIGIN 0 0 ;",
        f"  SIZE {width / 1000:.3f} BY {height / 1000:.3f} ;",
        "  SYMMETRY X Y ;",
    ]
    for name, (layer, box) in pins.items():
        lines.extend([f"  PIN {name}", "    DIRECTION INOUT ;", "    USE SIGNAL ;",
                      "    PORT", f"      LAYER {layer} ;", f"      {rect(box)}",
                      "    END", f"  END {name}"])
    lines.append("  OBS")
    for layer in ("Metal1", "Via1", "Metal2", "Via2", "Metal3",
                  "Via3", "Metal4", "Via4", "Metal5"):
        blocked = db.Region(outline)
        for pin_layer, box in pins.values():
            if pin_layer == layer:
                # Clear 1 µm around the pin including at the outer macro edge.
                blocked -= db.Region(box.enlarged(1000))
        lines.append(f"    LAYER {layer} ;")
        for box in blocked.decompose_trapezoids_to_region().each():
            if not box.is_box():
                raise ValueError(f"Obstruction on {layer} ceased to be rectangular")
            lines.append(f"    {rect(box.bbox())}")
    lines.extend(["  END", f"END {macro.name}"])
    return "\n".join(lines)


def export_all(output):
    output.mkdir(parents=True, exist_ok=True)
    macros = [export(code, output) for code in CODES]
    header = 'VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;'
    (output / "mim_kelvin.lef").write_text("\n\n".join([header, *macros, "END LIBRARY\n"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export_all(args.output)


if __name__ == "__main__":
    main()
