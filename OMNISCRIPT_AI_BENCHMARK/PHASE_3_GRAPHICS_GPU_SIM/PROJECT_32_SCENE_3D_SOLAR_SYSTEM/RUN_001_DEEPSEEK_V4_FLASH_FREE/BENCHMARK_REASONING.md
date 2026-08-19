# BENCHMARK_REASONING — Project 3.2 Interactive 3D Solar System (RUN_001_DEEPSEEK_V4_FLASH_FREE)

Live investigation ledger. Entries appended in chronological order. NOT retroactively edited.

## 2026-08-17 — Entry 0: Initial context

Read (in order):
- `C:\Users\tiamat\AppData\Local\Temp\opencode\V7_PHASE3_REFERENCE.md` (verified ecosystem reference)
- `...\PROJECT_32_SCENE_3D_SOLAR_SYSTEM\TASK.md` (task brief)

Key task constraints from TASK.md:
- 3D solar system: central star + planets, moon (hierarchical), light, camera.
- Orbital/hierarchical motion math as PURE functions (no scene runtime).
- Interaction: camera orbit + body highlight.
- Animation: continuous orbital motion over time (simulated via tick advancing).
- Verification: `omni check` exit 0, `omni build --target js` runnable artifact, all pytest pass.

Key reference claims (to VERIFY, not assume):
- `import OMNISYS.scene` is IMPOSSIBLE (scene = reserved keyword token; import parser requires IDENTIFIER).
- scene: block exists (box/sphere/cylinder/plane/light/camera; attrs size/color/pos/rotation/scale/type/intensity/texture/click; {var} slots allowed).
- No `and`/`or`/`not`; no `x[i]` indexing; no map literals; text building only via interpolation.

## 2026-08-17 — Entry 1: Compiler source inspection

Inspected: `omni_compiler/lexer.py`, `parser.py`, `checker.py`, `emitter.py`, `mir.py`, `omnisys_registry.py`, `omnisys/*.js`.

Verified facts from source:
- lexer.py line 29: `SCENE = "scene"` keyword; keyword_map line 88 maps `"scene"` -> TokenType.SCENE.
- parser.py parse_import (line 340-346): after `IMPORT`, consumes only `TokenType.IDENTIFIER` (path parts). Since `scene` lexes as SCENE (a keyword token, not IDENTIFIER), `import OMNISYS.scene` must raise SyntaxError at parse time. CONFIRMED the reference claim structurally.
- parser.py parse_scene_block (line 410): shapes from SHAPE_TOKEN_TYPES (box/sphere/cylinder/plane/light/camera); attrs consumed as IDENTIFIER then ASSIGN then value = LBRACE-slot | TEXT | NUMBER. Attribute names are IDENTIFIER tokens (color/pos/size/... are NOT keywords).
- parser.py parse_comparison (line 457): `is`, `is not`, `greater than`, `less than`, `greater or equal`, `less or equal`. NO `and`/`or`/`not` binary ops (they ARE lexed as AND/OR/NOT keyword tokens but parse_comparison/parse_term/parse_factor never consume them -> `a and b` would raise SyntaxError "Unexpected token").
- parser.py parse_primary: function calls `name(...)` with positional args; `[a, b]` list literal; `(expr)` parens. Dotted calls: `omnisys.collections.list_get(...)` -> FunctionCall with dotted_name.
- checker.py: BUILTIN_CAPABILITIES (network/filesystem/database/secrets), BUILTIN_FUNCTIONS = {join}. omnisys.* calls checked against imported_modules (E-IMPORT-003 if module not imported). omnisys_effects() gives declared effects; omnisys.collections.* and omnisys.core.* are pure (empty effects).
- Scene checker: SCENE_SHAPES {box,sphere,cylinder,plane,light,camera}; SCENE_ATTRIBUTES {size,color,pos,rotation,scale,type,intensity,texture,click}; SCENE_TEXT_ATTRS {color,pos,texture,click} reject NUMBER literals (E-SCENE-003). Slots bypass the text/number check (checked via analyze_expr of slot expr).
- emitter.py `_js_scene` (line 184): builds Three.js block. KEY DISCOVERY: `pos` attrs are split at BUILD time: `_js_attr_value(pos).strip('"').split(",")` — only LITERAL `pos="x,y,z"` yields a `position.set(x,y,z)`; a `{var}` slot renders to a JS identifier, then `.split(",")` produces length-1 -> NO position.set emitted. So dynamic pos via slots does NOT reach the emitted scene. `color="{var}"` slots DO work (rendered as `{ color: varName }` runtime reference).
- Scene emission loads three.min.js via document.createElement("script") at top level and calls initScene() in onload. In Node with the reference stub document (no createElement), this top-level line CRASHES -> the reference test-harness stub must be augmented for scene-bearing programs (add createElement/head/body) so Node runs the program to completion. initScene never runs in Node (onload never fires).
- emitter.py `_js_stmt`: show -> console.log(expr); assignment -> `name = expr;` at whatever scope; for -> `for (const v of iterable)`. Module-scope `let` declared for every assigned name (functions + entry point) minus param names.
- lexer.py TEXT pattern (line 150) does NOT allow nested unescaped quotes; `#` at line start/outside text = COMMENT; `#` inside a quoted TEXT literal is consumed by the TEXT pattern (safe for colors).
- omnisys/core.js: NO cos/sin (only abs/ceil/clamp/floor/max/min/round/sqrt/length/type_of/option wrappers/panic...). omnisys/collections.js has list_get/list_index_of/list_join/list_push/list_set etc. -> planet trig must be implemented as pure Taylor functions in source.
- omnisys_registry.py line 289: module "scene" IS registered (omnisys/scene.js, new_scene=...), BUT it is UNREACHABLE because import OMNISYS.scene dies at the parser. Ecosystem finding: registry advertises a module the parser cannot import.

## 2026-08-17 — Entry 2: Environment

- `python -m omni_compiler.cli --version` -> `omni, version 0.1.0` (workdir E:\simualtion).
- `node --version` -> `v24.17.0`.
- Run dir created:
  `E:\simualtion\OMNISCRIPT_AI_BENCHMARK\PHASE_3_GRAPHICS_GPU_SIM\PROJECT_32_SCENE_3D_SOLAR_SYSTEM\RUN_001_DEEPSEEK_V4_FLASH_FREE\`
  with `source/` and `tests/`.
- No other RUN dirs exist under PROJECT_31..34; no prior test harness to copy.

## 2026-08-17 — Entry 3: Probe P1 — `import OMNISYS.scene`

Hypothesis: parser raises SyntaxError because `scene` lexes as keyword token.

Probe source `probe_import_scene.omni` (temp):
```
import OMNISYS.scene

when app starts:
    show 1
end
```

Command: `python -m omni_compiler.cli check probe_import_scene.omni` (from temp dir)
Expected: exit != 0, SyntaxError JSON with "Unexpected token".

RESULT — CONFIRMED:
```
{
  "schema": "omni.diagnostic", "version": "1.0",
  "code": "E-SYNTAX-001", "category": "syntax", "severity": "error",
  "message": "Syntax error.",
  "details": "Expected token type TokenType.IDENTIFIER, got TokenType.SCENE ('scene') at line 1, col 16",
  ...
}
```
`check` exit code 1. The parser's `parse_import` demands IDENTIFIER tokens after `OMNISYS.`; `scene` is a SCENE keyword token -> `import OMNISYS.scene` is structurally impossible. The registry DOES list a `scene` module (omnisys/scene.js, omnisys_registry.py:289) — advertised but unreachable via `import`. Use the built-in `scene:` block instead. DECISION: built-in scene block + pure math functions; no scene import.

## 2026-08-17 — Entry 4: Probe P2 — language basics runtime

Probe `probe_basics.omni`: `advance_angle` (comparisons + wrap), `list_get`, `list_index_of`, `list_join`, text interpolation, `for` loop over list literal.

`check` -> exit 0. `build --target js` -> exit 0.
Node run (reference stub document, no scene in this probe) stdout:
```
a=6.25
x=20
idx=1
joined=sun,earth,moon
tick=0 a=6.25
tick=1 a=6.25
tick=2 a=6.25
```
exit 0. All constructs work: comparisons (`greater or equal`, `less than`), module functions, interpolation, for-loop iteration. `show "x={x}"` on a Number -> JS number interpolation, `console.log` prints raw float.

## 2026-08-17 — Entry 5: Probe P3 — scene block + Node harness stub

Probe `probe_scene.omni`: app block assigns `star_color`, shows output; `scene:` block with `sphere size color="{star_color}" pos="0,0,0"`, a second sphere with literal color/pos, `light type="directional" intensity="2" color="#ffffff"`, `camera pos="0,8,20"`.

`check` exit 0 (scene block + slot passes semantic analysis; slot expr `star_color` resolves because app-block defines it first and SymbolTable retains definitions across scopes). `build` exit 0.

Node run with the REFERENCE stub (`document = {getElementById, querySelectorAll}`):
```
star_color=#fbbf24
scene ok
TypeError: document.createElement is not a function   <-- CRASH after stdout
```
CONFIRMED ISSUE: the reference harness stub lacks `createElement`; the emitted scene code calls `document.createElement("script")` at top level. For scene-bearing programs the stub MUST be augmented.

Node run with AUGMENTED stub (adds `createElement: () => ({src:"", onload:null})`, `head:{appendChild(){}}`, `body:{appendChild(){}}`):
```
star_color=#fbbf24
scene ok
```
exit 0. `initScene()` never runs under Node (three.onload never fires) so no Three.js API is touched. The augmented stub is the test-harness recipe for scene-bearing programs.

Scene emission inspection (emitted JS):
- `new THREE.MeshStandardMaterial({ color: star_color })` — `{var}` color slot renders as a runtime variable reference; WORKS.
- `new THREE.MeshStandardMaterial({ color: "#9ca3af" })` — literal color works.
- `sphere_1.position.set(1.5, 0, 0);` — literal `pos="x,y,z"` emitted.
- `camera.position.set(0, 8, 20);` — literal camera pos emitted.
- `const light_2 = new THREE.DirectionalLight("#ffffff", 2.0);` — emitted.
- DECISION for source: use literal `pos="..."` and literal colors in the scene block (slots work for color but NOT for pos; a pos slot renders an identifier which `.split(",")` at build time turns into length-1 -> no position.set emitted — verified in emitter.py source, Entry 1). Motion/positions are shown via the app block's pure-math output instead.

## 2026-08-17 — Entry 6: Design decisions for solar_system.omni

- No cos/sin in omnisys.core -> implement `sin_approx`/`cos_approx` as pure Taylor polynomials (fixed terms, `+ - * /` only).
- Parameters chosen so all printed angles stay in [-0, 1.3] rad -> Taylor error < ~5e-6, so tests can compare against Python `math.cos`/`math.sin` with abs tolerance 1e-3.
  - dt = 0.25; ticks 0..4 (5 instants).
  - mercury: r=1.5, speed=1.2, a0=0.0  -> max a = 1.2
  - venus:   r=2.2, speed=0.9, a0=0.3  -> max a = 1.2
  - earth:   r=3.0, speed=0.6, a0=0.6  -> max a = 1.2
  - mars:    r=3.9, speed=0.4, a0=0.9  -> max a = 1.3
  - moon:    r=0.6, speed=2.0, a0=0.1  -> max a = 2.1 (hierarchical offset added to earth pos)
  - camera:  dist=10, height=4, speed=0.8, a0=0.0 -> max a = 0.8
- `orbital_position(radius, angle) -> List` = [r*cos, 0, r*sin].
- `advance_angle(angle, speed, dt)` wraps via two nested ifs (no modulo).
- `moon_position(planet_angle, planet_radius, moon_angle, moon_radius)` = planet pos + moon offset (uses list_get).
- `camera_orbit(angle)` = [10*cos, 4, 10*sin].
- `highlight_body(bodies, name)` = omnisys.collections.list_index_of (selection logic; returns index, -1 if absent).
- `color_of(name)` nested ifs to pick a hex color per body (no and/or/not).
- App block prints labeled lines:
  - scene/body composition markers (counts + order via list_join)
  - colors per body via color_of
  - per-tick planet positions `tick=N mercury=x,z`
  - per-tick moon position `tick=N moon=x,z`
  - per-tick camera `tick=N camera=x,z`
  - highlight results `highlight earth idx=2`, `highlight pluto idx=-1`
- Test harness: build -> extract <script> -> prepend AUGMENTED stub -> node -> parse stdout lines; compare positions to Python math-based expectations.

## 2026-08-17 — Entry 7: Wrote source/solar_system.omni