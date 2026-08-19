# OMNISYS.error

Structured, machine-readable runtime errors for OmniScript's Python lane.

Error values are plain dicts — `{"tag": "error", "message": ..., "code": ..., "context": {...}}` —
so they serialize to JSON, cross process and backend boundaries, and stay inspectable by AI tooling.
The module is pure and stdlib-only; it depends on `omnisys_core` (registry `js_deps = ("core",)`) and
inherits core's error-as-value philosophy: errors are values you can build, inspect, and extend, not
bare host exceptions.

**`OmniError` vs `omnisys_core.PanicError`:** a panic is a programmer error — an invariant
violation that "should never happen" and is not meant to be recovered from (`PanicError`, raised by
`omnisys_core.panic`). `OmniError` is a *structured runtime error* raised by `throw_error`; it
carries `message`, `code`, and `context` attributes so callers can match on codes instead of string
messages.

API: `error`, `error_code`, `error_message`, `error_code_of`, `error_with_context`,
`error_has_context`, `error_to_dict`, `throw_error`, `is_error`, and the `OmniError` exception.

See [RESEARCH.md](RESEARCH.md) for the ecosystem survey, the eleven design questions, and the
deviations from the JS reference.