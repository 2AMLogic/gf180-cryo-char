# /// script
# requires-python = ">=3.10"
# dependencies = ["klayout==0.30.14", "klayout-tools==0.9.2"]
# ///
"""Measure full-core Metal5 conductors against each Kelvin macro's LEF obstructions."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile


def union_intervals(intervals):
    merged = []
    for lo, hi in sorted(intervals):
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return merged


def minimum_crossings(bands, low, high, size):
    if not 0 < size <= high - low:
        raise ValueError("Obstruction must fit in the tested dimension of the core")
    # An overlap count changes only at a band endpoint. Touching edges are legal.
    starts = {low, high - size}
    for bottom, top in bands:
        starts.update(x for x in (top, bottom - size) if low <= x <= high - size)
    return min(sum(bottom < start + size and top > start for bottom, top in bands)
               for start in starts)


def main():
    import klayout.db as db
    from verify_kelvin import HERE, check_toolchain, read_abstract

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--die", type=Path, required=True)
    parser.add_argument("--build-record", type=Path, required=True)
    parser.add_argument("--pdk", type=Path, required=True)
    args = parser.parse_args()
    build_bytes = args.build_record.read_bytes()
    build = json.loads(build_bytes)
    if build["schema"] != "gf180-cryo-char.layout.build-record/1" or build["status"] != "pass":
        parser.error("Expected a passing cryo layout build record")
    with args.die.open("rb") as stream:
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != build["gds"]["sha256"]:
        parser.error("Die stream differs from the build record")
    pdk = args.pdk.resolve()
    check_toolchain(Path(sys.executable).with_name("klt"), pdk, require_openroad=True)
    with tempfile.TemporaryDirectory() as tmp:
        sizes, _, obstructions = read_abstract(pdk, Path(tmp).resolve())

    layout = db.Layout()
    layout.read(str(args.die))
    chip = layout.top_cell()
    if layout.dbu != 0.001 or chip is None or chip.name != "chip_top":
        parser.error("Expected one chip_top on the LEF's 1 nm coordinate grid")
    core = db.DBox(*map(float, build["metrics"]["design__core__bbox"].split())).to_itype(layout.dbu)
    if core.empty() or (core & chip.bbox()) != core:
        parser.error("Recorded core lies outside the die")
    bands = []
    for shape in chip.shapes(layout.layer(81, 0)).each():
        if not (shape.is_box() or (shape.is_polygon() and shape.polygon.is_box())
                or (shape.is_path() and shape.path.polygon().is_box())):
            continue
        box = shape.bbox()
        if box.left <= core.left and box.right >= core.right:
            lo, hi = max(box.bottom, core.bottom), min(box.top, core.top)
            if lo < hi:
                bands.append((lo, hi))
    bands = union_intervals(bands)
    boundaries = [core.bottom, *(y for band in bands for y in band), core.top]
    gap = max(hi - lo for lo, hi in zip(boundaries[::2], boundaries[1::2]))
    result = {}
    for name, size in sorted(sizes.items()):
        # Project each connected obstruction polygon onto both axes. A conductor
        # spanning the entire core intersects any obstruction at an overlapping y.
        boxes = [poly.bbox() for poly in obstructions[name]["Metal5"].each_merged()]
        if (union_intervals((b.bottom, b.top) for b in boxes) != [[0, size.height()]]
                or union_intervals((b.left, b.right) for b in boxes) != [[0, size.width()]]):
            raise ValueError(f"Metal5 obstruction projection does not cover {name}'s outline")
        result[name] = {
            "size_nm": [size.width(), size.height()],
            "minimum_crossings_native_orientation": minimum_crossings(
                bands, core.bottom, core.top, size.height()),
            "minimum_crossings_quarter_turn": minimum_crossings(
                bands, core.bottom, core.top, size.width()),
        }
    report = {
        "build_record": build["record_id"],
        "build_record_sha256": hashlib.sha256(build_bytes).hexdigest(),
        "gds_sha256": digest.hexdigest(),
        "lef_sha256": hashlib.sha256((HERE / "mim_kelvin.lef").read_bytes()).hexdigest(),
        "core_nm": [core.left, core.bottom, core.right, core.top],
        "full_width_metal5_bands_nm": bands,
        "largest_gap_nm": gap,
        "macros": result,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
