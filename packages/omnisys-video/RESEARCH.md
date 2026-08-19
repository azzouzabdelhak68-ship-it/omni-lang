# OMNISYS.video — Research Gate

Deliverable per `docs/architecture/19-quality-gates.md` §6 and the video
module design notes. Grounded in the JS reference `omnisys/video.js` and the
compiler registry `OMNISYS_MODULES["video"]`.

## 1. Ecosystems studied

- **FFmpeg** — the de-facto decode/encode toolkit (libavcodec/libavformat).
  Frame data is raw planar/nv12 pixel buffers on a time base; timelines are
  container-level (durations, pts/dts, fps from the stream metadata). Pattern
  kept: a timeline as an ordered sequence of frames plus an fps; everything
  else (real codecs, containers) is an escape.
- **WebCodecs / HTMLVideoElement** — `VideoFrame` objects with `codedWidth`/
  `codedHeight` and an `ImageBitmap`-like pixel surface; playheads seek by
  timestamp across a frame sequence. Pattern kept: a `VideoFrame` value with
  width/height and a seekable ordered timeline.
- **OpenCV** — `cv::Mat` grids (rows × cols) of pixel scalars, `imread`/
  `imwrite` for decode/encode, `VideoCapture` with `get(CAP_PROP_FPS)`.
  Pattern kept: frames as grids of pixel cells; fps read off the capture
  source.
- **This repo's JS lane** — `omnisys/video.js` defines the portable semantic
  API that every lane must mirror.

## 2. What was adopted

- One `VideoFrame` value `{"tag": "video.frame", "width", "height",
  "pixels"}` where `pixels` is a list-of-lists of `"#RRGGBB"` color strings
  (JSON friendly — the AI-native mandate).
- One `Timeline` value `{"tag": "video.timeline", "fps", "frames"}`.
- `frame(width, height)` builds a black grid; dimensions are clamped with
  `max(0, int(...))` while the stored `width`/`height` fields keep the raw
  arguments (JS returns `width: width, height: height`).
- `frame_from_ascii(rows)` maps `' '` → `#000000`, everything else →
  `#ffffff`, per `String(row)`; width is the first row's length (0 when
  empty).
- `add_frame` deep-copies before appending (JS `JSON.parse(JSON.stringify(...))`
  → Python `copy.deepcopy`).
- Out-of-bounds `set_pixel` and `seek` panic with the exact JS messages
  through `omnisys_core.panic` (raises `PanicError`).

## 3. Strengths / weaknesses of the studied ecosystems

- FFmpeg: universal codec coverage; heavy native dependency, buffer-centric
  (not JSON).
- WebCodecs: zero-copy browser decoding; browser-only, no scriptable core.
- OpenCV: fast grid math; C++-centric, native dependency.

OMNISYS keeps the portable *semantic* core only: a timeline of JSON pixel
grids with fps and metadata. FFmpeg/WebCodecs/OpenCV are escapes that consume
the same model.

## 4. Performance

- `frame` is O(width × height) for the pixel grid; `add_frame` is O(n) on
  frame size for the deep copy; `seek` is O(1) index access; `frame_count`,
  `fps_of`, `metadata` are O(1) with `metadata` O(1) plus the first-frame
  peek. No locking in the single-threaded script model.

## 5. Type-system interaction / portability

- Registry types: `fn(Number, Number) -> VideoFrame`, `fn(List) ->
  VideoFrame`, `fn(VideoFrame, Number, Number, Text) -> VideoFrame`,
  `fn(Number) -> Timeline`, `fn(Timeline, VideoFrame) -> Timeline`,
  `fn(Timeline, Number) -> VideoFrame`, `fn(Timeline) -> Number` ×2,
  `fn(Timeline) -> Map`. Python typing uses `VideoFrame`/`Timeline` aliases
  over `dict[str, Any]`; coercion inputs (`width`, `height`, `rows`, `color`,
  `fps`, `index`) are `Any` to mirror JS's runtime coercion
  (`| 0`, `String(...)`, `||`).

## 6. Lifecycle / error / concurrency model

- Frames and timelines are mutable dict values; frames own their pixel grids,
  timelines own their frame lists. `add_frame` copies, `seek` returns the
  stored (deep-copied-as-added) reference, `set_pixel` mutates in place.
- Errors: `set_pixel` out of bounds raises `omnisys_core.PanicError`
  (`video.set_pixel: out of bounds`); `seek` out of range raises
  `PanicError` (`video.seek: frame out of range`). No other paths raise.

## 7. AI usability

- Frames and timelines are pure JSON: an agent can allocate frames, draw via
  `set_pixel`, build timelines, add/seek, and read `metadata` with no runtime
  and no codec dependency — the whole model is directly inspectable.

## 8. Interop requirements

- Future escapes: FFmpeg/WebCodecs/OpenCV adapters decode into `VideoFrame`
  grids and encode grids back out; `metadata` gives the codec the fps and
  dimensions it needs. These are escapes only — the registry surface
  (`video` module, 9 pure functions) stays codec-free.

## 9. Deviation table (JS → Python)

| # | JS (`omnisys/video.js`) | Python (this package) | Reason |
|---|--------------------------|-----------------------|--------|
| 1 | `JSON.parse(JSON.stringify(...))` deep copy | `copy.deepcopy` | Same result for JSON-able values |
| 2 | `Math.max(0, width \| 0)` / `new Array(...)` | `max(0, int(width))` | Same for ints; `int` truncates like `\| 0` |
| 3 | `fps \|\| 30` | `fps or 30` | Same truthiness fallback |
| 4 | `frame` row loop `for (let y = 0; y < height; y++)` | `range(max(0, int(height)))` | JS quirk grows a 3-length array to 4 rows on `height = 3.9`; spec pins `int(height)` rows |
| 5 | `core.panic(...)` throws | `omnisys_core.panic(...)` raises `PanicError` | Same abort semantics, Python exception |
| 6 | `Array.from(String(row)).map(...)` | `['#000000' if ch == ' ' else '#ffffff' for ch in str(row)]` | Same per-char mapping |

## 10. Verification

- `python -m pytest packages/omnisys-video/tests -q -W error` — all tests
  pass, zero warnings.
- Coverage: `packages/omnisys-video/src` **100% branch**.
- `mypy --strict packages/omnisys-video/src` — clean.
- `ruff check` + `ruff format --check` on `packages/omnisys-video` — clean.