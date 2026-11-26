# 20261126-151012-c937349-die

**Status**: pass

## Created (UTC)

- "2026-11-26T15:10:12+00:00"

## Repo commit

- "c93734974ae032e7a9ff568edffa8788b396b5d0"

## Pins

- **die**:
  - **dbu_um**: 0.001
  - **height_um**: 5122
  - **slot**: 1x1
  - **top**: chip_top
  - **width_um**: 3932
- **klayout_package_min**: 0.30
- **klt_install**: git+https://github.com/2AMLogic/klayout-tools@046ba74652fc096bd97071fc3237f7159dd40183
- **klt_last_verified_commit**: 046ba74652fc096bd97071fc3237f7159dd40183
- **klt_required_commands**: ["drc", "stats", "cells", "diff", "artifact"]
- **nix**:
  - **sha256**: 06016b9166b4461c331969df803d86a0f9781d783c443adfd2067560c8a2bab5
  - **url**: https://releases.nixos.org/nix/nix-2.28.4/nix-2.28.4-x86_64-linux.tar.xz
  - **version**: 2.28.4
- **wafer_space**:
  - **pdk**:
    - **delivered_by**: ciel
    - **name**: gf180mcuD
    - **open_pdks_commit**: 792ef67037d74c8c51811eab3ce23cf793491296
  - **precheck**:
    - **commit**: 9b4e7dab6af073d02b81ecc368069540d2f67db9
    - **repo**: https://github.com/wafer-space/gf180mcu-precheck
  - **template**:
    - **commit**: d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c
    - **pad**: gf180mcu_fd_io
    - **repo**: https://github.com/wafer-space/gf180mcu-project-template
    - **scl**: gf180mcu_fd_sc_mcu7t5v0
    - **slot**: 1x1
    - **sram**: gf180mcu_fd_ip_sram
    - **target**: librelane-condensed

## Source tarball SHA-256

- "5459a68f2c0903cd0983643c889d5b6f72ea823651fce8c85e37fe981208ba1b"

## Job

- **group**: cryo4-die-cfa2b8d
- **shard**: s00
- **state**: done
- **ok**: true
- **exit_code**: 0
- **failure_reason**: null
- **wall_seconds**: 5199
- **instance_type**: m7i.4xlarge
- **image_id**: ami-08688417b66e0c74d
- **retry_count**: 3
- **started_at**: 2026-11-26T13:43:16Z
- **outputs**:
  - **found**: ["precheck/out"]
  - **missing**: []

## Input

- **bytes**: 178401210
- **name**: die.gds
- **sha256**: 6a97d4cbd25f4feccf44ed9ac0887d6254208b83050c3e8934672e35d3e8a8a8

## Options

- **cob**: false
- **id**: FFFFFFFF
- **slot**: 1x1
- **threads**: 2
- **top**: chip_top
- **workers**: 8

## Tools

- **klayout**: KLayout 0.30.12
- **librelane**: 3.1.0.dev3
- **magic**: 8.3.677
- **nix**: nix (Nix) 2.28.4
- **openroad**: dcf36133a369abc8f3c5e5738cd4d82e4903c0e0
- **paths**:
  - **klayout**: /nix/store/pbq1kkpw4pyzsm582vz7jk2ayypzd2c0-devshell-dir/bin/klayout
  - **magic**: /nix/store/pbq1kkpw4pyzsm582vz7jk2ayypzd2c0-devshell-dir/bin/magic
  - **openroad**: /nix/store/pbq1kkpw4pyzsm582vz7jk2ayypzd2c0-devshell-dir/bin/openroad
  - **yosys**: /nix/store/pbq1kkpw4pyzsm582vz7jk2ayypzd2c0-devshell-dir/bin/yosys
- **python**: Python 3.13.13
- **yosys**: Yosys 0.69 (git sha1 9f75ca1f9834a39a863915b5dae0c7b1e33533bc, Release, Clang /nix/store/874j5xydsj6nr6i1zdrjvhln5gmxvvrr-clang-wrapper-21.1.8/bin/clang++ 21.1.8)

## PDK revision observed

- ["open_pdks 792ef67037d74c8c51811eab3ce23cf793491296"]

## Metrics

- **klayout__antenna_error__count**: 0
- **klayout__density_error__count**: 0
- **klayout__drc_error__count**: 0
- **klayout__zero_area_polygons__count**: 0
- **magic__drc_error__count**: 0

## Wall seconds

- **check the PDK revision**: 0
- **fetch the PDK (open_pdks 792ef67037d74c8c51811eab3ce23cf793491296)**: 68
- **install nix 2.28.4**: 12
- **precheck die.gds id=FFFFFFFF threads=2 workers=8 cob=0**: 5117
- **record the toolchain**: 2

## Image

- **base_ami**: ami-08b275ac6cc5dbefb
- **built_at**: 2026-11-11T19:14:18Z
- **issue**: 2am-3632
- **pin_digest**: 82dfbbbf638f934eb74099e1faff5eeca4de66352daf4cf2f89229e9f18d829f
- **profile**: heavy
- **schema**: eda-batch-image/1
- **security**:
  - **awscli_botocore**: 1.43.62 /opt/aws-cli/lib/python3.12/site-packages/awscli/botocore/__init__.py
  - **awscli_certifi**: 2026.10.19
  - **awscli_pyvenv_cfg**: include-system-site-packages=false
  - **bundles**:
    - **awscli_botocore**:
      - **certs**: 120
      - **path**: /opt/aws-cli/lib/python3.12/site-packages/certifi/cacert.pem
      - **sha256**: 50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785
    - **eda_venv**:
      - **certs**: 120
      - **path**: /opt/eda/venv/lib/python3.12/site-packages/certifi/cacert.pem
      - **sha256**: 50f79f98dac192b20dbf73f35c56f0b0c557ab267ff5199d1117cc1180b70785
    - **system**:
      - **certs**: 120
      - **path**: /etc/ssl/certs/ca-certificates.crt
      - **sha256**: e05a523d99de77c6b1f2c7b7c3af502c8378f29e6e8484358ec55f96b0972ad6
    - **system_python**:
      - **certs**: 120
      - **path**: /etc/ssl/certs/ca-certificates.crt
      - **sha256**: e05a523d99de77c6b1f2c7b7c3af502c8378f29e6e8484358ec55f96b0972ad6
  - **ca_certificates**: 20260816ubuntu0.24.04.2
  - **distrusted_root**: emSign ECC Root CA - G3|AAA Certificate Services
  - **eda_certifi**: 2026.10.19
  - **libnss3**: 2:3.98-1ubuntu0.3
- **source_commit**: 1329fd0b9
- **tools**:
  - **awscli**: 1.46.3
  - **klt**: 0.9.0
  - **klt_build**: 0.9.0
  - **openroad**: 26Q4-1310-g98c6045c72
  - **orfs_commit**: 7bf5a814e47c54ec6c64692b464d398184d99891
  - **sby**: v0.70
  - **tool_bytes**: 4209819730
  - **yosys**: 0.68
  - **z3**: 4.8.12-3.1build1

## Run tag

- "RUN_2026-11-26_13-44-39"

## Evidence

- [{"path": "console.log", "sha256": "e553b1f0fe3b5cbb57df594708e6117031dcf6a8f91a6aa8a88077ffbb90df4e", "bytes": 12749252}, {"path": "flow/01-klayout-readlayout/config.json", "sha256": "8ad9175d06850a00bac395060a6e386adc202e2e214a5346259e033113d84926", "bytes": 11076}, {"path": "flow/01-klayout-readlayout/klayout-readlayout.log", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "bytes": 0}, {"path": "flow/01-klayout-readlayout/klayout-readlayout.process_stats.json", "sha256": "2990ab00ddd1bae1d8af33e9514986dc7b27a06b63b88bd74016899b79eb9ea1", "bytes": 503}, {"path": "flow/01-klayout-readlayout/runtime.txt", "sha256": "8c7afa7063e37aa38d90c7bf373bf1653e60d17790258bdac5072c082588fa8a", "bytes": 12}, {"path": "flow/01-klayout-readlayout/state_in.json", "sha256": "8bbbb272fcbae1f9f875f02f7fae97bb73751ce58d1f651e21b7928aaf9cee9d", "bytes": 21}, {"path": "flow/01-klayout-readlayout/state_out.json", "sha256": "75efddc75956afaceac5d4b68d7e759f227d3aa2be04a186a3fc9abd14424570", "bytes": 156}, {"path": "flow/02-klayout-checktoplevel/config.json", "sha256": "bbf6ea585ff9a1f1fd5ca41180356374a36e5aa45dcc1a7b4b074d9c4c4526bd", "bytes": 11398}, {"path": "flow/02-klayout-checktoplevel/klayout-checktoplevel.log", "sha256": "e09e0c19be2732e7a61fe116a36f5b182aabddb526fd6580ff35b54117370772", "bytes": 171}, {"path": "flow/02-klayout-checktoplevel/klayout-checktoplevel.process_stats.json", "sha256": "ee622ded756eaa3acbf4f9511cc22bf2a4d5e7ef38cbceb0f29063b6b45d0323", "bytes": 504}, {"path": "flow/02-klayout-checktoplevel/runtime.txt", "sha256": "55abdfeb4cadba563d03933f3710babc7631516ee9398499907937bfa71a55b1", "bytes": 12}, {"path": "flow/02-klayout-checktoplevel/state_in.json", "sha256": "75efddc75956afaceac5d4b68d7e759f227d3aa2be04a186a3fc9abd14424570", "bytes": 156}, {"path": "flow/02-klayout-checktoplevel/state_out.json", "sha256": "75efddc75956afaceac5d4b68d7e759f227d3aa2be04a186a3fc9abd14424570", "bytes": 156}, {"path": "flow/03-klayout-checksize/config.json", "sha256": "75bbffb9385fc0a790658c8ea1414aa157e0cc9e08f9b6e775d9bc3496554647", "bytes": 11043}, {"path": "flow/03-klayout-checksize/klayout-checksize.log", "sha256": "044bfe1854e73877262598d84a95b90f126f0377f375e28c96c221ce497e7154", "bytes": 170}, {"path": "flow/03-klayout-checksize/klayout-checksize.process_stats.json", "sha256": "132b3baf7f3ed357ce95131aa0d86e3f92c158f6a2d556a01527ae7a0b257ef2", "bytes": 504}, {"path": "flow/03-klayout-checksize/runtime.txt", "sha256": "3622f1504e3f43ea3c5bcf6a367d553515a44f8a9a0685bc4e4abfd41c033bd5", "bytes": 12}, {"path": "flow/03-klayout-checksize/state_in.json", "sha256": "75efddc75956afaceac5d4b68d7e759f227d3aa2be04a186a3fc9abd14424570", "bytes": 156}, {"path": "flow/03-klayout-checksize/state_out.json", "sha256": "75efddc75956afaceac5d4b68d7e759f227d3aa2be04a186a3fc9abd14424570", "bytes": 156}, {"path": "flow/04-klayout-generateid/config.json", "sha256": "c0eba122e419bb6e4b70e75bc1565bce7d08bd094c8682a82185794df74e496e", "bytes": 11044}, {"path": "flow/04-klayout-generateid/klayout-generateid.log", "sha256": "79fd3dc1f0c441ee253d170b1ec798196baf6ac31c67d0f95b98ab80a6da2824", "bytes": 1835}, {"path": "flow/04-klayout-generateid/klayout-generateid.process_stats.json", "sha256": "e863e35752beb10acb289d6ed9e95c770b71540ffbeb1ca40f3b152fe3f773a8", "bytes": 503}, {"path": "flow/04-klayout-generateid/runtime.txt", "sha256": "6c74e9778f59c4e779eba7823ab0509a9dd9c05978830b586b2c130e959f1daf", "bytes": 12}, {"path": "flow/04-klayout-generateid/state_in.json", "sha256": "75efddc75956afaceac5d4b68d7e759f227d3aa2be04a186a3fc9abd14424570", "bytes": 156}, {"path": "flow/04-klayout-generateid/state_out.json", "sha256": "c2d09fb43d125f366c9d8073c4ade21e41cf4a4dd8de9ea55d7be0dcaac89968", "bytes": 156}, {"path": "flow/05-klayout-render/config.json", "sha256": "0ea0eccffdd407ff715f28ecfa7b8a5acde4fcd06514d9b2289838b2f85c2fad", "bytes": 11639}, {"path": "flow/05-klayout-render/klayout-render.log", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "bytes": 0}, {"path": "flow/05-klayout-render/klayout-render.process_stats.json", "sha256": "b5ccb796dc749ea8d73cdbbd159affe3721b018ae5cdb102db88a4dbc3521d87", "bytes": 496}, {"path": "flow/05-klayout-render/runtime.txt", "sha256": "5c05311d9147f0eb416b4a4ecb28c8dd5de7a6e25d24c8b70965f4e2e90d971f", "bytes": 12}, {"path": "flow/05-klayout-render/state_in.json", "sha256": "c2d09fb43d125f366c9d8073c4ade21e41cf4a4dd8de9ea55d7be0dcaac89968", "bytes": 156}, {"path": "flow/05-klayout-render/state_out.json", "sha256": "151e551e792bc4c6b1442923a57220b52177490cac165bfb0917a624565209b4", "bytes": 290}, {"path": "flow/06-klayout-density/config.json", "sha256": "016ed265137a96527e1a2f0e19ee57387b808854ed7cae433696304924bb2eac", "bytes": 11710}, {"path": "flow/06-klayout-density/klayout-density.log", "sha256": "75851072e816835817a06a96c7379f792c7fc5260433f783b558c75560b734ee", "bytes": 11354}, {"path": "flow/06-klayout-density/klayout-density.process_stats.json", "sha256": "0c31cd4248a5e57c82ffa059df47ed034f02412e69a7f3258ba39b71c66179cb", "bytes": 499}, {"path": "flow/06-klayout-density/reports/density.klayout.json", "sha256": "985cc131e7b4867a77403682d07e0a7345570015cfe8f148b96a80c5d63912f4", "bytes": 35}, {"path": "flow/06-klayout-density/runtime.txt", "sha256": "9aeb43c5eac599ce36f57be2f2e2f5380e882b5c96f5522e56f4980aec625691", "bytes": 12}, {"path": "flow/06-klayout-density/state_in.json", "sha256": "151e551e792bc4c6b1442923a57220b52177490cac165bfb0917a624565209b4", "bytes": 290}, {"path": "flow/06-klayout-density/state_out.json", "sha256": "da17efd21245be22b5a98139fb4f600ae2214d38374b430b3f43e92931c711e3", "bytes": 338}, {"path": "flow/06-klayout-density/xml_drc_report_to_json.log", "sha256": "3bcf612aebee78620e3adf6ce86d9bf59ea1b2cad857b6b43c50fe1262d405d0", "bytes": 45}, {"path": "flow/06-klayout-density/xml_drc_report_to_json.process_stats.json", "sha256": "5c47dd405a19b2a042ac8ca57460ceafa5f534099b3d9f9123045f3360958003", "bytes": 475}, {"path": "flow/07-checker-klayoutdensity/config.json", "sha256": "3ddae68eb4edec7d03a7fda68037613fc8a84d3edfb9fd6644e80fd1373c858f", "bytes": 11018}, {"path": "flow/07-checker-klayoutdensity/runtime.txt", "sha256": "5dd108c20c1a7a6c4e3e775791ef6c39feb3e7d3e3b0bfea1d0d3b0ee8ff3cbe", "bytes": 12}, {"path": "flow/07-checker-klayoutdensity/state_in.json", "sha256": "da17efd21245be22b5a98139fb4f600ae2214d38374b430b3f43e92931c711e3", "bytes": 338}, {"path": "flow/07-checker-klayoutdensity/state_out.json", "sha256": "da17efd21245be22b5a98139fb4f600ae2214d38374b430b3f43e92931c711e3", "bytes": 338}, {"path": "flow/08-klayout-zeroareapolygons/config.json", "sha256": "33bf4a8e5a7dd742722c2320f588889079438187ea0e5a28b0a3c576c7fbbdfc", "bytes": 11401}, {"path": "flow/08-klayout-zeroareapolygons/klayout-zeroareapolygons.log", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "bytes": 0}, {"path": "flow/08-klayout-zeroareapolygons/klayout-zeroareapolygons.process_stats.json", "sha256": "b3b11489fdbe8e0eda2a2f44dd47a244718afcaba097bafa9312c0cc46105211", "bytes": 499}, {"path": "flow/08-klayout-zeroareapolygons/reports/density.klayout.json", "sha256": "95713014258d4c01f8cb3b873c03699f793c34037148706362afe83ab42ceafd", "bytes": 1113}, {"path": "flow/08-klayout-zeroareapolygons/runtime.txt", "sha256": "d2b77959ba83b5e470a940ce2386f3c7f68abdba4942ee64c1f9e17ebdc674b9", "bytes": 12}, {"path": "flow/08-klayout-zeroareapolygons/state_in.json", "sha256": "da17efd21245be22b5a98139fb4f600ae2214d38374b430b3f43e92931c711e3", "bytes": 338}, {"path": "flow/08-klayout-zeroareapolygons/state_out.json", "sha256": "61dc02e814753599b63f1b4fc3571b92158700bb59a3265cd894b88eae882214", "bytes": 387}, {"path": "flow/08-klayout-zeroareapolygons/xml_drc_report_to_json.log", "sha256": "c053120105c6f8695d73d28e61f4c1686f5f4e77d76539794f37c740e982f319", "bytes": 50}, {"path": "flow/08-klayout-zeroareapolygons/xml_drc_report_to_json.process_stats.json", "sha256": "1b6944e280b7ab0913f1c7ca02eea2d87bc452d1a38cb0ebfe4e59006dfa0375", "bytes": 475}, {"path": "flow/09-checker-klayoutzeroareapolygons/config.json", "sha256": "ad33e968a64f7370486e1cace1119af620bf8a834833b61764acaee3ba9a0e56", "bytes": 11038}, {"path": "flow/09-checker-klayoutzeroareapolygons/runtime.txt", "sha256": "5dd108c20c1a7a6c4e3e775791ef6c39feb3e7d3e3b0bfea1d0d3b0ee8ff3cbe", "bytes": 12}, {"path": "flow/09-checker-klayoutzeroareapolygons/state_in.json", "sha256": "61dc02e814753599b63f1b4fc3571b92158700bb59a3265cd894b88eae882214", "bytes": 387}, {"path": "flow/09-checker-klayoutzeroareapolygons/state_out.json", "sha256": "61dc02e814753599b63f1b4fc3571b92158700bb59a3265cd894b88eae882214", "bytes": 387}, {"path": "flow/10-klayout-antenna/config.json", "sha256": "7f961142299f9225e408772a1e2b505600e4b8512a92194ed853bee259c1d0d5", "bytes": 11673}, {"path": "flow/10-klayout-antenna/klayout-antenna.log", "sha256": "4ff030eb2b1d34a9f152edf58034d45a3fa256a0913cecb37a865343b34cade9", "bytes": 14186}, {"path": "flow/10-klayout-antenna/klayout-antenna.process_stats.json", "sha256": "6840ef7b9551a3bdc7cc2accff08354b7accf36039b8f4a6393a72f2d3e919e8", "bytes": 496}, {"path": "flow/10-klayout-antenna/reports/antenna.klayout.json", "sha256": "5156c1f39453297d8adcc426452f701e40e506c505782d41e6ff98895fda04e2", "bytes": 659}, {"path": "flow/10-klayout-antenna/runtime.txt", "sha256": "cc082208f5668de03cb82bbec39fbcaba38b3c1678ee4ab2b50c614bc06d34f8", "bytes": 12}, {"path": "flow/10-klayout-antenna/state_in.json", "sha256": "61dc02e814753599b63f1b4fc3571b92158700bb59a3265cd894b88eae882214", "bytes": 387}, {"path": "flow/10-klayout-antenna/state_out.json", "sha256": "efce48cdb02ca67371d24517f83e6cb049447c1aa56c26aa6b1e9c515b631334", "bytes": 431}, {"path": "flow/10-klayout-antenna/xml_drc_report_to_json.log", "sha256": "26254726d4a247299fe7d8676612dc18541e96e27fed4de27f9c8eee8bc059cb", "bytes": 45}, {"path": "flow/10-klayout-antenna/xml_drc_report_to_json.process_stats.json", "sha256": "9a046f69121c9e655fd9a6cdf4c0348a37c80403657c62a7171bb86073b9bb2a", "bytes": 473}, {"path": "flow/11-checker-klayoutantenna/config.json", "sha256": "d74e5d501795b1c8396988996260617a68d72a4813f54bc838ed6feb29a04daf", "bytes": 11018}, {"path": "flow/11-checker-klayoutantenna/runtime.txt", "sha256": "5dd108c20c1a7a6c4e3e775791ef6c39feb3e7d3e3b0bfea1d0d3b0ee8ff3cbe", "bytes": 12}, {"path": "flow/11-checker-klayoutantenna/state_in.json", "sha256": "efce48cdb02ca67371d24517f83e6cb049447c1aa56c26aa6b1e9c515b631334", "bytes": 431}, {"path": "flow/11-checker-klayoutantenna/state_out.json", "sha256": "efce48cdb02ca67371d24517f83e6cb049447c1aa56c26aa6b1e9c515b631334", "bytes": 431}, {"path": "flow/12-magic-drc/config.json", "sha256": "1c80ad21b0df44b5c1376de7b7f333d1d95c0dff5e3132949a249dec1857cedb", "bytes": 90884}, {"path": "flow/12-magic-drc/magic-drc.process_stats.json", "sha256": "509acd2c38c061ae1e4d1b8624d330cc582bb8cc8a52e7f6159f4a6137f5071a", "bytes": 496}, {"path": "flow/12-magic-drc/reports/drc.magic.rpt", "sha256": "62913411eff229e7d8ebb93848e518efe8a14975beb31ba0a19386d17a8fbff0", "bytes": 102}, {"path": "flow/12-magic-drc/runtime.txt", "sha256": "528cef6d908dd39bf9f1415c10fe14383dd2ff290b447585cf557afadd0a9ff0", "bytes": 12}, {"path": "flow/12-magic-drc/state_in.json", "sha256": "efce48cdb02ca67371d24517f83e6cb049447c1aa56c26aa6b1e9c515b631334", "bytes": 431}, {"path": "flow/12-magic-drc/state_out.json", "sha256": "3644e8c2a41b2fdcb8bb8d506baace385c0b6b0350e4953c9628c73b4d757ca3", "bytes": 469}, {"path": "flow/13-checker-magicdrc/config.json", "sha256": "14aa2029d384493710e3fc6f3b06e362a4bc19c137b195c2b579b7265c13d981", "bytes": 11007}, {"path": "flow/13-checker-magicdrc/runtime.txt", "sha256": "5dd108c20c1a7a6c4e3e775791ef6c39feb3e7d3e3b0bfea1d0d3b0ee8ff3cbe", "bytes": 12}, {"path": "flow/13-checker-magicdrc/state_in.json", "sha256": "3644e8c2a41b2fdcb8bb8d506baace385c0b6b0350e4953c9628c73b4d757ca3", "bytes": 469}, {"path": "flow/13-checker-magicdrc/state_out.json", "sha256": "3644e8c2a41b2fdcb8bb8d506baace385c0b6b0350e4953c9628c73b4d757ca3", "bytes": 469}, {"path": "flow/14-klayout-drc/config.json", "sha256": "cabbbf3186043ccf26fbb8ea8e9cae447693631cb6028357fcd8e4e89701334f", "bytes": 11710}, {"path": "flow/14-klayout-drc/klayout-drc.log", "sha256": "bfbb69964f6ea7f7b3e9771aa1920e087138409008762a45f4bbaf43d0817954", "bytes": 97286}, {"path": "flow/14-klayout-drc/klayout-drc.process_stats.json", "sha256": "78e781a983e6261211e1e47628be2bb1433baaa27d364faab9d15bee722aec54", "bytes": 497}, {"path": "flow/14-klayout-drc/reports/drc.klayout.json", "sha256": "8e54d6e7974afb7ed706ee090d97ff2e0c4d2acb5445529f41d90f519001b907", "bytes": 14310}, {"path": "flow/14-klayout-drc/runtime.txt", "sha256": "44ca290f0b33a9467701fcd40dbc3667dc2161871ca2559c323e56ff02451f1a", "bytes": 12}, {"path": "flow/14-klayout-drc/state_in.json", "sha256": "3644e8c2a41b2fdcb8bb8d506baace385c0b6b0350e4953c9628c73b4d757ca3", "bytes": 469}, {"path": "flow/14-klayout-drc/state_out.json", "sha256": "2e835cb15c30b9e51e2d4ab18e997c94dcfc4c4687ffdd5be31f79a5c63eea43", "bytes": 509}, {"path": "flow/14-klayout-drc/xml_drc_report_to_json.log", "sha256": "d145c58244c876c4aca168707ecf2096ffe222eb25210e8ed44702961da6082a", "bytes": 41}, {"path": "flow/14-klayout-drc/xml_drc_report_to_json.process_stats.json", "sha256": "bf0c2eaa8e3181554c5811b434acdfd21bc3e2e473301c2b8efc1e6869ccb19a", "bytes": 500}, {"path": "flow/15-checker-klayoutdrc/config.json", "sha256": "5d6ae19dc079522f2e7a51f478b7688d508387f8a69575a6c65f846c3874f192", "bytes": 11010}, {"path": "flow/15-checker-klayoutdrc/runtime.txt", "sha256": "5dd108c20c1a7a6c4e3e775791ef6c39feb3e7d3e3b0bfea1d0d3b0ee8ff3cbe", "bytes": 12}, {"path": "flow/15-checker-klayoutdrc/state_in.json", "sha256": "2e835cb15c30b9e51e2d4ab18e997c94dcfc4c4687ffdd5be31f79a5c63eea43", "bytes": 509}, {"path": "flow/15-checker-klayoutdrc/state_out.json", "sha256": "2e835cb15c30b9e51e2d4ab18e997c94dcfc4c4687ffdd5be31f79a5c63eea43", "bytes": 509}, {"path": "flow/16-klayout-writelayout/config.json", "sha256": "277ae505d66ec864d3356885a433c101737633b1f95766587b1c78c61dcfc35e", "bytes": 11011}, {"path": "flow/16-klayout-writelayout/runtime.txt", "sha256": "5dd108c20c1a7a6c4e3e775791ef6c39feb3e7d3e3b0bfea1d0d3b0ee8ff3cbe", "bytes": 12}, {"path": "flow/16-klayout-writelayout/state_in.json", "sha256": "2e835cb15c30b9e51e2d4ab18e997c94dcfc4c4687ffdd5be31f79a5c63eea43", "bytes": 509}, {"path": "flow/16-klayout-writelayout/state_out.json", "sha256": "2e835cb15c30b9e51e2d4ab18e997c94dcfc4c4687ffdd5be31f79a5c63eea43", "bytes": 509}, {"path": "flow/error.log", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "bytes": 0}, {"path": "flow/final/metrics.json", "sha256": "6c3a79b2fcd586e74d2ec512994da1d45bf4b676331a2c46a96dbd2ad8c3fbab", "bytes": 197}, {"path": "flow/flow.log", "sha256": "b0ec1817e35d86d8280a8f0a33da22e1dea47e74a465848999330ebbc4455e39", "bytes": 4574}, {"path": "flow/resolved.json", "sha256": "db5f087b97f668d217b16809d753a4e6e482f1768a829b9173778a19ab439799", "bytes": 92939}, {"path": "flow/warning.log", "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "bytes": 0}, {"path": "flow-files.txt", "sha256": "625e37079213f95d03c2fcc082b7fd87f0b6b6d03cfc28bfaa62909b38d68dd3", "bytes": 5533}, {"path": "harness.log", "sha256": "5d870f1b8ae8992a4d0451896f3bbce3bccd18036be8f91dda5c3692a77ab976", "bytes": 2357}, {"path": "phases.txt", "sha256": "27363ac1a9a8c51d52c801ff07db80edd4fc58f41fce9e7302b8e87d94642696", "bytes": 399}, {"path": "precheck.json", "sha256": "2a28c03d02c05541b3e8857fd62dcf2cbe3de6dbdfb6dcf8e468980881cf7d8b", "bytes": 3911}, {"path": "run.json", "sha256": "4f99bb1f0dc13966632726d3ebea22ab19a69a23bec02d876e15d4e3e24d9cd5", "bytes": 632}, {"path": "status.json", "sha256": "f29e11a440810cb764e5b28d05c3c83b872078e1320be5be18611668e6630ee4", "bytes": 536}, {"path": "tools.json", "sha256": "bac59f9462caf1cf38d5290b235ff28496be76d2afefebe601c3369f1a7902f3", "bytes": 739}]
