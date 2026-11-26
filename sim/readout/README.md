# Measurement-path reference benches

Run `python3 sim/readout/cold_start.py` from a clean checkout with Python 3.12 and ngspice 46. Install ngspice with your package manager or set `NGSPICE` to the path of its executable. The script downloads three SHA-256-checked model files (about 1.5 MB) from the [shuttle PDK](https://github.com/wafer-space/gf180mcu/tree/ac7d8696de96a4d708e768b607ae37f02207a354/gf180mcuD). For offline use, set `CRYO_SHUTTLE_PDK` to that checkout’s `gf180mcuD` directory. The script checks the same hashes before simulation. ngspice 47 rejects the full pad’s rail capacitor with `unknown parameter (e9)`. Use a compatible binary for the full-cell replay.

All circuits use the typical GF180MCU-D models at 25 °C and 3.3 V. The output currents include the switch junctions. The bounds in the runner detect changes to these recorded controls. They do not establish an operating range for the die.

| Circuit | Stimulus | Reference result |
|---|---|---|
| Single open transmission gate | Measured port at 0 V, far terminal at 3.3 V and 0 V | 68.197 fA and 63.532 fA. Either exceeds the proposed 5 fA aggregate switch budget. |
| Two open transmission gates with driven midpoint and isolated instrument-side bodies | Sweep the sense node from 1 mV to 3.299 V, far terminal at either rail, guard tracking error −1, 0 or +1 mV | One branch reaches 2.1351, 0.1371 and 0.1351 fA at gmin of 1e-12, 1e-15 and 1e-19 S. Each maximum covers six sweeps of 201 bias points. |
| Foundry analog pad with both supply domains held by ideal sources | Sweep the unloaded pad 0–3.3 V. Measure AC admittance at 1.65 V and 10 kHz with an ideal disconnected terminal as control. | 874.24 fF for one pad, or 549.30 pA RMS at 10 mV RMS. With ngspice 46 the largest absolute DC reading changes from 3,303 fA at the default shunt to 0.89 fA at gmin=1e-19 S. The disconnected terminal reads zero. |

The guard is an ideal tracking source with a 1 kΩ link to the midpoint. The per-branch number excludes other branches, the driver and well implementation. The pad model includes both ESD diodes and its supply-to-supply circuit. Its AC result puts a matched-open calibration requirement on the fixture. Its tiny DC residual depends on simulator precision. The complete path still needs extracted all-branch loading, pad/fixture calibration and instrument-resolution evidence. [Experiment and controls](https://github.com/2AMLogic/gf180-cryo-char/issues/2#issuecomment-7185325327)
