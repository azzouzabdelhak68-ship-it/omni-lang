# OMNISYS.video

Python reference implementation of the OMNISYS `video` module: a portable
video model — frames as JSON-friendly grids of pixel color cells, timelines
as ordered frame lists with an fps, seeking, and metadata.

- **Registry**: `OMNISYS_MODULES["video"]` — 9 pure functions (zero declared
  effects), `js_deps = ("core", "audio")`. The JS lane mirrors
  `omnisys/video.js`.
- **Import**: `from omnisys_video import frame, frame_from_ascii, set_pixel,
  timeline, add_frame, seek, frame_count, fps_of, metadata` — add
  `packages/omnisys-video/src` to `PYTHONPATH`, or rely on the monorepo
  `packages/conftest.py` bootstrap.
- **Value shapes**: VideoFrame = `{"tag": "video.frame", "width": ...,
  "height": ..., "pixels": [[color, ...], ...]}` (every cell a `"#RRGGBB"`
  string); Timeline = `{"tag": "video.timeline", "fps": ..., "frames":
  [VideoFrame, ...]}`.
- **Semantics**: mirrors `omnisys/video.js` — `frame(width, height)` builds a
  black frame with `int()`-clamped pixel grid (negative/float dims clamp/truncate;
  the stored `width`/`height` fields keep the raw arguments); `frame_from_ascii`
  maps `' '` → `#000000` and any other character → `#ffffff` (empty input → 0×0);
  `set_pixel` writes `str(color)` and panics (`omnisys_core.PanicError`) with
  `video.set_pixel: out of bounds` when `(x, y)` is outside the grid;
  `timeline(fps)` defaults to 30; `add_frame` appends a deep copy
  (`copy.deepcopy` for the JS `JSON.parse(JSON.stringify(...))`); `seek` panics
  with `video.seek: frame out of range` and otherwise returns the stored frame;
  `frame_count`/`fps_of` read the timeline; `metadata` reports
  `{frames, fps, duration, width, height}` with `duration = frames / (fps or 30)`.

Real codec decode/encode (FFmpeg, WebCodecs, OpenCV) is an **escape**: this
package is the portable semantic core those backends consume.

See [`RESEARCH.md`](RESEARCH.md) for the design gate notes and every
deviation from the JS reference.