# 20261126-093000-ab12cd3-die

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
  - **found**: ["precheck/out"]
  - **missing**: []

## Input

- **name**: die.gds
- **sha256**: b29e915aa3a5e93cc7feea0a2418f26af54d0290d533868f9c738e50151b153d
- **bytes**: 24

## Options

- **cob**: false
- **id**: FFFFFFFF
- **slot**: 1x1
- **threads**: 2
- **top**: chip_top
- **workers**: 8

## Tools

- **klayout**: KLayout 0.30.12
- **nix**: nix (Nix) 2.28.4

## PDK revision observed

- ["open_pdks 0000000000000000000000000000000000000000"]

## Metrics

- **klayout__drc_error__count**: 0
- **magic__drc_error__count**: 0

## Wall seconds

- **precheck die.gds id=FFFFFFFF threads=2 workers=8 cob=0**: 5117

## Image

- **profile**: heavy
- **schema**: eda-batch-image/1

## Run tag

- "RUN_2026-11-26_13-44-39"

## Evidence

- [{"path": "console.log", "sha256": "ca82404bdbfae6d68f0c72c965d3048baa60a6d6d650bf48cfdea87683f58d96", "bytes": 17}, {"path": "flow/01-klayout-drc/config.json", "sha256": "4eebce483d3cc95b64573be4237e274fc753f7679bc36e3340535cea56b43d68", "bytes": 16}, {"path": "flow/01-klayout-drc/reports/drc.klayout.json", "sha256": "efe6604e8a14d9eb75525c5285c32142ef789f354ab14a17ef055c50dcb1c8c8", "bytes": 18}, {"path": "flow-files.txt", "sha256": "829f957328071f64e3b03d994e99a9cf1b3441fed95bc39c31d44f9f0a176eb5", "bytes": 77}, {"path": "harness.log", "sha256": "060ef7ef8ff4aca6f37f6e9628af19e2a9eadc31edb07ff5179ef13651c2627c", "bytes": 17}, {"path": "phases.txt", "sha256": "2db0e4dbc9340c9b9848adbb2bd685b59fbbb9210db6f9692f7abda11b3629bf", "bytes": 21}, {"path": "precheck.json", "sha256": "8bd1325abf860da2ecc59466879a8400a62364dca87f41776d4884d7704c22d9", "bytes": 768}, {"path": "run.json", "sha256": "d63589f9a568f29cc09cc12ee8c6445ea1e85551eb8e71934d66fd957696f7c2", "bytes": 259}, {"path": "status.json", "sha256": "c3ffd9b6eca3d7a0b44da0aee4bb9115147f28e38ec73ae5c038fdd1b63480f8", "bytes": 48}, {"path": "tools.json", "sha256": "3aa043589e182ac53901ee643899be6eab3c7f19a93db6ca8806370fad2391f9", "bytes": 32}]
