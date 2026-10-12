# Contributing

Use Python 3.14, run `scripts/setup`, and run `scripts/lint` and `pytest` before
submitting a change. Develop with `scripts/develop` in an isolated configuration.

Changes to register decoding belong in the standalone `indevolt-modbus` library.
Entity changes belong in the core overlay. Refresh this repository with
`scripts/sync.py` from the three-folder workspace, then verify the resulting diff.

For hardware reports, provide model, firmware and protocol versions, diagnostics,
expected values and redacted captures. Do not include credentials or full serials.
