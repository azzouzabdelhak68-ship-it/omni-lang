# BENCHMARK_REASONING.md

## Project 1.3: Serialization/Config Exporter

### Investigation Log

#### 2026-08-17 - Initial Investigation

**Task Understanding:**
- Implement a configuration loading and export tool using OmniScript
- Parse structured configuration documents (JSON, CSV, etc.)
- Validate against a schema with typed fields
- Export normalized structured values
- Use OMNISYS.serde module (v6) for JSON/CSV/hex/base64/schema_validate

**Repository Exploration:**
1. Found OMNISYS.serde in `packages/omnisys-serde/` with Python reference implementation
2. Module registry in `omni_compiler/omnisys_registry.py` shows serde functions:
   - `json_encode` - fn(any) -> Text
   - `json_decode` - fn(Text) -> any
   - `csv_encode` - fn(List) -> Text
   - `csv_decode` - fn(Text) -> List
   - `to_hex` - fn(Text) -> Text
   - `from_hex` - fn(Text) -> Text
   - `base64_encode` - fn(Text) -> Text
   - `base64_decode` - fn(Text) -> Text
   - `schema_validate` - fn(any, Map) -> Boolean

3. Schema validation supports:
   - Types: any, text, number, boolean, list, map
   - Nested fields validation via `fields` key
   - Required field checking

**OmniScript Language Features Discovered:**
- `import OMNISYS.serde` for importing serde module
- Custom types with `type Name = { field: Type, ... }`
- Functions with `fn name(params) -> ReturnType:` syntax
- Effects system: `uses filesystem`, `pure`, etc.
- `when app starts:` block for entry point
- List literal: `[1, 2, 3]`
- Map literal: `{key: value, ...}`
- String interpolation: `"{variable}"`
- Control flow: `if/else/end`, `for/end`

**Initial Hypotheses:**
1. Need to import OMNISYS.serde and OMNISYS.fs (for file reading)
2. Define schema as a Map structure for schema_validate
3. Parse JSON config files using json_decode
4. Validate against schema
5. Export validated config using json_encode

**Questions to Investigate:**
1. How to read files in OmniScript? (OMNISYS.fs.read_file)
2. How to handle validation errors and classify them?
3. What's the exact Map syntax for schema definition?
4. Can we return structured error information?
5. How to handle multiple config formats (JSON, CSV)?

#### 2026-08-17 - Probe Testing

**Testing OmniScript Compiler:**
- CLI: `python -m omni_compiler.cli <cmd>`
- Commands: check, run, build

**First Probe - Basic Import Test:**
```omni
import OMNISYS.serde
import OMNISYS.fs

when app starts:
    show "test"
end
```

Let me test this...