# /// script
# requires-python = ">=3.10,<3.11"
# dependencies = ["glayout @ git+https://github.com/ReaLLMASIC/gLayout.git@97276267411c193037f9844716f376fcb126c3e6"]
# ///
"""Generate GF180D option-B capacitor units in the pinned gLayout runtime."""

import argparse
from pathlib import Path

from glayout.pdk.gf180_mapped.gf180_mapped import gf180_mapped_pdk
from glayout.primitives.mimcap import mimcap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for side in (5, 10, 40):
        cap = mimcap(
            gf180_mapped_pdk, size=(side, side), option="B", with_extension=False
        )
        cap.name = f"mim_{side}"
        cap.write_gds(args.output / f"{side}.gds")


if __name__ == "__main__":
    main()
