# OMNISYS.scene

## Purpose

3D scene graph model: scene composition, primitives, transforms, cameras,
lights. Referenced by §17.6.3 and §17.7 Phase 3.

## Public API surface

```omni
import OMNISYS.scene

scene:
    box size=1,1,1 color="#e11d48" pos=0,0,0
    camera fov=60
    light type=ambient
end
```

## Dependencies

- `core`
- `graphics` (rendering backend)

## Effects/capabilities used

- `uses GPU`

## Status

planned

## Open Questions

- Scene serialization/interchange format
- Editor tooling integration

<!-- CAPABILITIES: scene; GPU -->