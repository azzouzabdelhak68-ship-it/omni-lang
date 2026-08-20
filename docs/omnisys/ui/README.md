# OMNISYS.ui

## Purpose

Cross-platform UI framework designed from first principles for OmniScript
(SwiftUI/WPF/Qt/web principles), mapping a semantic UI model onto Windows,
Linux, macOS, browser, and mobile targets. Reactive state via `state_set`
automatically triggers re-render.

## Public API surface

```omni
import OMNISYS.ui

UI:
<view layout="row">
    <label>Hello</label>
    <button click="on_click">Go</button>
</view>
end
```

## Dependencies

- `core` (result/option types)
- `collections`

## Effects/capabilities used

- `uses screen`
- `uses input`
- `uses dom`

## Status

stable

## Open Questions

- Retained vs. immediate mode default
- Accessibility model ownership

<!-- CAPABILITIES: screen; input; dom -->