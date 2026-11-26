# 0001 — GF180 port of the NIST MPW-5 characterization tile

Status: RATIFIED on merge

The rows below take effect on merge after independent EE and market review and operator approval of the same revision. A push starts those reviews over.

## Decision

Build a GF180MCU-D full-slot characterization die on the wafer.space template. Preserve the source structure identifiers so that a measurement on the GF180 die can be joined to the NIST reference by identifier, geometry, bias and temperature. Device technology, legal drawn dimensions and well connections differ between processes. Report those differences with the result. The source geometry is derived from the published workbook and module descriptions. Use only the GF180 PDK and generators for the new layout.

| Row | Bound on ratification | Verification before delivery |
|---|---|---|
| T1. Die | 3,932 × 5,122 µm, origin (0,0), GF180MCU-D, 74 pinned template pad locations. | Check top, bounds, pad locations and full official precheck on the submitted stream. |
| T2. Coverage | Account for all 493 primary workbook entries. The proposed map ports 372 and records a process-specific reason for each of 121 drops. Preserve the documented placements selected with the replica bit. | Regenerate the source columns from the checksum-pinned NIST workbook. Run DRC/LVS and a pin-access test for each integrated structure. Publish any additional freeze cuts by ID. |
| T3. Selection | Choose one structure at a time. Expose separate force/sense paths where the DUT supports them. Open all paths on reset, deselect, invalid address or a disabled replica. | Verify the decoder and the break-before-make sequence, each registered selection's physical connectivity, and independent Kelvin force/sense terminals. |
| T4. Measurement error | For FET and diode DC, target at most 5 fA of raw aggregate switch loading per selected terminal. Qualify a stated current range using the measured pad/fixture/instrument floor, calibrated current recovery and uncertainty for that path. The reference-scale detection claim requires a 10 fA calibrated challenge in each claimed polarity. Aggregate loading must be below the smallest current claimed. A larger substitute release range needs a separate numeric ratification. The readout record specifies the other class limits. | Before freeze, sweep extracted loading and record design-target misses. Qualify a DC range only when matched blanks and independent current standards pass the [measured-floor criterion](selection-readout.md#fet-and-diode-dc-qualification). Publish unresolved ranges and their evidence. |
| T5. Delivery | Freeze December 9, 2026. Deliver precheck-clean GDS, SHA-256 and log by December 16 to the slot holder. | Verify the published bytes and log against the final tagged commit. |

The mapping, pin assignments and numeric budgets are part of this decision. Stretch work on additional devices requires a later decision and independent evidence. The target is room-temperature modelling and comparison; cryogenic behaviour is a future silicon measurement. The single-gate simulation exceeds the 5 fA design target before pad contributions. The complete multiplexer and the sensitivity of the physical measurement path still await verification. A cut to meet the shuttle date stays visible in the Bronze tracker.

[Structure map and source reconciliation](structure-map.md) · [Selection and leakage budgets](selection-readout.md) · [Pad and die plan](die-plan.md)
