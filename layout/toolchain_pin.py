"""Check the shared GF180 layout command inventory and the open_pdks install."""

import json
from pathlib import Path
import re
import subprocess


def check(klt, pdk, *, require_openroad=False):
    pin = json.loads(Path(__file__).with_name("toolchain.json").read_text())
    help_text = subprocess.check_output([klt, "--help"], text=True)
    for command in pin["klt_required_commands"]:
        if not re.search(r"(?m)^\s+" + re.escape(command) + r"\s", help_text):
            raise ValueError(f"Missing klt {command}. Install {pin['klt_install']}")
    sources = (pdk / "SOURCES").read_text().strip()
    if sources != "open_pdks f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7":
        raise ValueError(f"Unexpected GF180D PDK revision at {pdk}: {sources}")

    if require_openroad:
        install = f"Use the OpenROAD binary from docker pull {pin['openroad_image']}"
        try:
            version = subprocess.check_output(["openroad", "-version"], text=True).strip()
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise ValueError(f"Cannot run openroad -version. {install}") from exc
        if version != pin["openroad_version"]:
            raise ValueError(f"Expected OpenROAD {pin['openroad_version']}, got {version!r}. {install}")
