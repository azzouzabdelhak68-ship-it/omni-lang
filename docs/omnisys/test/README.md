# OMNISYS.test

## Purpose

Testing framework: assertions, mocking, property-based testing, benchmarking.

## Public API surface

```omni
import OMNISYS.test

fn assert(condition: Bool) -> Result
fn property(body: fn) -> Result
fn mock(spec: MockSpec) -> Result
fn bench(body: fn) -> Result
```

## Dependencies

- `core`

## Effects/capabilities used

- None

## Status

planned

## Open Questions

- Property-generation strategy integration
- Coverage instrumentation model

<!-- CAPABILITIES: test -->