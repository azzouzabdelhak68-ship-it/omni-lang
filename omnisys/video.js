"use strict";
/**
 * OMNISYS.video — portable video model: frames, timelines, seeking, and
 * metadata. Frames are grid-of-pixel color cells (JSON friendly). Real
 * codec decode/encode is an escape; this is the portable semantic core.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const video = (omnisys.video = omnisys.video || {});
  const core = omnisys.core;

  video.frame = function (width, height) {
    const pixels = new Array(Math.max(0, height | 0));
    for (let y = 0; y < height; y++) pixels[y] = new Array(Math.max(0, width | 0)).fill("#000000");
    return { tag: "video.frame", width: width, height: height, pixels: pixels };
  };
  video.frame_from_ascii = function (rows) {
    const pixels = rows.map((row) => Array.from(String(row)).map((ch) => (ch === " " ? "#000000" : "#ffffff")));
    return { tag: "video.frame", width: pixels[0] ? pixels[0].length : 0, height: pixels.length, pixels: pixels };
  };
  video.set_pixel = function (frame, x, y, color) {
    if (y < 0 || y >= frame.pixels.length || x < 0 || x >= frame.pixels[y].length) core.panic("video.set_pixel: out of bounds");
    frame.pixels[y][x] = String(color);
    return frame;
  };
  video.timeline = function (fps) {
    return { tag: "video.timeline", fps: fps || 30, frames: [] };
  };
  video.add_frame = function (timeline, frame) {
    timeline.frames.push(JSON.parse(JSON.stringify(frame)));
    return timeline;
  };
  video.seek = function (timeline, index) {
    if (index < 0 || index >= timeline.frames.length) core.panic("video.seek: frame out of range");
    return timeline.frames[index];
  };
  video.frame_count = function (timeline) {
    return timeline.frames.length;
  };
  video.fps_of = function (timeline) {
    return timeline.fps;
  };
  video.metadata = function (timeline) {
    const first = timeline.frames[0];
    return {
      frames: timeline.frames.length,
      fps: timeline.fps,
      duration: timeline.frames.length / (timeline.fps || 30),
      width: first ? first.width : 0,
      height: first ? first.height : 0,
    };
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);