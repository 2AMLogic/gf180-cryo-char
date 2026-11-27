# 20261126-093000-ab12cd3-template

**Status**: pass

## Created (UTC)

- "2026-11-26T09:30:00+00:00"

## Repo commit

- "ab12cd3000000000000000000000000000000000"

## Pins

- **die**:
  - **top**: chip_top
  - **slot**: 1x1
  - **width_um**: 3932
  - **height_um**: 5122
  - **dbu_um**: 0.001
- **klt_install**: git+https://github.com/2AMLogic/klayout-tools@0000000000000000000000000000000000000000

## Source tarball SHA-256

- "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"

## Job

- **group**: g
- **shard**: s00
- **state**: done
- **ok**: true
- **exit_code**: 0
- **failure_reason**: null
- **wall_seconds**: 6533
- **instance_type**: m6i.4xlarge
- **image_id**: ami-08688417b66e0c74d
- **retry_count**: 0
- **started_at**: 2026-11-26T09:20:01Z
- **outputs**:
  - **found**: ["build/out"]
  - **missing**: []

## Make

- **PAD**: gf180mcu_fd_io
- **SCL**: gf180mcu_fd_sc_mcu7t5v0
- **SLOT**: 1x1
- **SRAM**: gf180mcu_fd_ip_sram

## Target

- "librelane-condensed"

## Tools

- **librelane**: 3.1.0.dev3
- **nix**: nix (Nix) 2.28.4

## Metrics

- **design__instance__count**: 251807
- **design__violations**: 0

## Gds

- **name**: chip_top.gds
- **sha256**: b29e915aa3a5e93cc7feea0a2418f26af54d0290d533868f9c738e50151b153d
- **bytes**: 24

## Checks

- **single_top_cell**: true
- **top_cell_is_pinned**: true
- **origin_at_zero**: true
- **size_matches_slot**: true
- **dbu_matches**: true
- **die_matches_pin**: true
- **top_cell**: chip_top
- **dbu_um**: 0.001
- **bbox_um**:
  - **left**: 0.0
  - **bottom**: 0.0
  - **right**: 3932.0
  - **top**: 5122.0
  - **width**: 3932.0
  - **height**: 5122.0
- **geometry_digest**: sha256:1111111111111111111111111111111111111111111111111111111111111111

## Artifact

- **sha256**: b29e915aa3a5e93cc7feea0a2418f26af54d0290d533868f9c738e50151b153d
- **size**: 24
- **kind**: evidence
- **producer**:
  - **tool**: librelane
  - **version**: 0.9.3.dev5655
  - **loom.repo**: 2AMLogic/gf180-cryo-char
  - **commit**: ab12cd3000000000000000000000000000000000
- **uri**: artifact:evidence/2AMLogic__gf180-cryo-char/b2/b29e915aa3a5e93cc7feea0a2418f26af54d0290d533868f9c738e50151b153d
- **name**: build/20261126-093000-ab12cd3-template/chip_top.gds

## Evidence

- [{"path": "build.json", "sha256": "f4ca1e37b8e846d5236c513bd180cea4b347d27690db423d5c04ee13a296faef", "bytes": 357}, {"path": "console.log", "sha256": "ca82404bdbfae6d68f0c72c965d3048baa60a6d6d650bf48cfdea87683f58d96", "bytes": 17}, {"path": "harness.log", "sha256": "060ef7ef8ff4aca6f37f6e9628af19e2a9eadc31edb07ff5179ef13651c2627c", "bytes": 17}, {"path": "metrics.json", "sha256": "c8798a30eee1bee4c6af86bf511050e736c9bf90f25dcec0036eec25afb8443e", "bytes": 30}, {"path": "phases.txt", "sha256": "2db0e4dbc9340c9b9848adbb2bd685b59fbbb9210db6f9692f7abda11b3629bf", "bytes": 21}, {"path": "run.json", "sha256": "aa1a916c561e2fe6ad1e4bdbc6510795f4cfc21658679b49e8115bc6a248fa60", "bytes": 256}, {"path": "status.json", "sha256": "c3ffd9b6eca3d7a0b44da0aee4bb9115147f28e38ec73ae5c038fdd1b63480f8", "bytes": 48}, {"path": "tools.json", "sha256": "3aa043589e182ac53901ee643899be6eab3c7f19a93db6ca8806370fad2391f9", "bytes": 32}]
