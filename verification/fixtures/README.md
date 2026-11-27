# verification/fixtures

Golden output of `layout.spot <stage> record`, compared byte for byte by
`ShardRecordTests` in `../test_layout_toolchain.py`.

`build-pass.record.{json,md}` and `precheck-pass.record.{json,md}` are what the
writer produced for a synthetic collected shard with `spot.now()` frozen at
`2026-11-26T09:30:00Z`, before issue #38 deduplicated `cmd_record_build` and
`cmd_record_precheck` into `cmd_record` (writer at `aca3e92`). They exist to
prove the refactor changed no record: `record.json` is the sorted dump, and
`record.md` follows the record's key insertion order, so both files pin the
structure, not just the content.

Do not edit these by hand. A record format change is a new schema version and
regenerates them from a writer that is known good, in the same commit. Every
value is deterministic: the shard files are fixed bytes written by the test,
and `klt` is stubbed.
