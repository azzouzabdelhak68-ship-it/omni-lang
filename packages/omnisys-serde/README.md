# OMNISYS.serde (Python)

Python reference implementation of the OMNISYS `serde` module: JSON, CSV, hex,
base64, and schema validation.

- **Contract:** `OMNISYS_MODULES["serde"].functions` in
  `omni_compiler/omnisys_registry.py` — all nine functions are pure.
- **Dependency:** `omnisys_core` (per the registry `js_deps`); the
  implementation itself is stdlib-only (`json`, `base64`, `binascii`).
- **Reference:** mirrors the JS implementation in `omnisys/serde.js`.
- **Design notes:** see [`RESEARCH.md`](RESEARCH.md) for the research gate.

Functions: `json_encode`, `json_decode`, `csv_encode`, `csv_decode`, `to_hex`,
`from_hex`, `base64_encode`, `base64_decode`, `schema_validate`.

Key semantics: JSON uses `ensure_ascii=False`; hex/base64 are UTF-8 based;
`csv_decode` trims cells and skips blank lines; `schema_validate` is a
recursive dict-schema validator. Invalid input raises (documented per
function), mirroring the JS throwing model.