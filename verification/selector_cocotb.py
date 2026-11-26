"""Exercise the switch-control pins against the independently maintained map."""
import os
from pathlib import Path

import cocotb
from cocotb.triggers import Timer


def selections():
    rows = {}
    for line in (Path(__file__).resolve().parents[1] / "spec/structure-map.md").read_text().splitlines():
        fields = [field.strip() for field in line.strip("|").split("|")]
        if len(fields) != 7 or not fields[0].isdigit():
            continue
        code = int(fields[0])
        assert code not in rows
        rows[code] = (fields[1].split("!")[0], fields[-1].startswith(("Dropped", "Cut")))
    assert set(rows) == set(range(1, 494))
    allowed = {510, 511}
    rings = []
    for code, (sheet, excluded) in sorted(rows.items()):
        if excluded:
            continue
        allowed.add(code)
        if sheet in ("PrRES", "ROSC"):
            allowed.add(code + 512)
        if sheet == "ROSC":
            rings.append(code)
    # Ring enables have a stable identity even if a physical specimen is cut.
    ring_ports = [482, 483, 484, 487]
    assert set(rings) <= set(ring_ports)
    ring_ports += [code + 512 for code in ring_ports]
    cuts = {int(code) for code in os.environ["SELECTOR_CUTS"].split(",") if code}
    return allowed - cuts, ring_ports


async def tick(dut):
    await Timer(4, unit="ns")
    dut.clk.value = 1
    await Timer(4, unit="ns")
    dut.clk.value = 0
    await Timer(2, unit="ns")


@cocotb.test()
async def check_switch_controls(dut):
    allowed, ring_ports = selections()

    def check(address=None, run=False):
        active = address in allowed
        expected = (
            int(active),
            (1 << (address >> 4)) if active else 0,
            (1 << (address & 15)) if active else 0,
            (1 << ring_ports.index(address)) if active and run and address in ring_ports else 0,
        )
        actual = tuple(int(pin.value) for pin in
                       (dut.ready, dut.bank_enable, dut.member_enable, dut.ring_enable))
        assert actual == expected, f"address={address} RO_EN={run}, got {actual}, expected {expected}"

    dut.clk.value = 0
    dut.addr.value = 0
    dut.ro_en.value = 1
    dut.meas_en.value = 0
    dut.rst_n.value = 0
    await tick(dut)
    check()
    dut.rst_n.value = 1
    dut.meas_en.value = 1
    # An odd stride visits every 10-bit address once, changing banks repeatedly.
    for index in range(1024):
        address = (index * 173 + 1) % 1024
        dut.addr.value = address
        await tick(dut)
        check()
        await tick(dut)
        check(address, run=True)
        await tick(dut)
        check(address, run=True)

    for address in (482, 995, 510, 511, 1):
        dut.addr.value = address
        await tick(dut)
        check()
        await tick(dut)
        check(address, run=True)
        dut.ro_en.value = 0
        await Timer(7, unit="ns")
        check(address)
        dut.ro_en.value = 1
        dut.addr.value = 496
        await Timer(5, unit="ns")
        check(address, run=True)  # A stopped clock holds the registered selection.
        for clear in (dut.meas_en, dut.rst_n):
            clear.value = 0
            await Timer(2, unit="ns")
            check()
            clear.value = 1
            dut.addr.value = address
            await Timer(2, unit="ns")
            check()  # A pulse with no intervening clock must still disarm.
            await tick(dut)
            check()
            await tick(dut)
            check(address, run=True)

    for address in (3, 4, 3, 4):
        dut.addr.value = address
        await tick(dut)
        check()  # The address never remains stable over the blank interval.
    await tick(dut)
    check(4, run=True)
