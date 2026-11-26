"""Identify the GF180D model release used for a T4 leakage measurement."""

from hashlib import sha256

PAD_FILE = "libs.ref/gf180mcu_fd_io/spice/gf180mcu_fd_io.spice"
DESIGN_DIGEST = "7e222f050318388f37543a64fbd0be55cc15e4b93f57501a09f7c159c4c9e561"
PAD_DIGEST = "710732fd6a69e165caa2c29e4cdf81b11af41da32705fcd860b7ecfb09630dd1"
RELEASES = {
    "open_pdks f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7": "f6f4a96e18fc5ad11270ad3451aaecc7ac37fc81eb61e15b0d7d94c7bc594a24",
    "open_pdks 792ef67037d74c8c51811eab3ce23cf793491296": "69a7ab877344a6d477fdd11440457f64e7ad88a624504a737a161da463de8bc8",
}


def check_inputs(pdk, *, include_pad):
    release = (pdk / "SOURCES").read_text().strip()
    if release not in RELEASES:
        raise ValueError(f"Unrecognized GF180D release: {release}")
    model_digest = RELEASES[release]
    pins = {
        "libs.tech/ngspice/design.ngspice": DESIGN_DIGEST,
        "libs.tech/ngspice/sm141064.ngspice": model_digest,
        "libs.tech/ngspice/sm141064.spice": model_digest,
    }
    if include_pad:
        pins[PAD_FILE] = PAD_DIGEST
    for filename, expected in pins.items():
        if sha256((pdk / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Unexpected {filename} for {release}")
