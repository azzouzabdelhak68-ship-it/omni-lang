"use strict";
/**
 * OMNISYS.graphics — portable 2D canvas model. Operations are recorded as a
 * deterministic command list, renderable to HTML5 canvas (browser escape) or
 * serialized to JSON. Pure, testable in Node.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const graphics = (omnisys.graphics = omnisys.graphics || {});

  graphics.canvas = function (width, height) {
    return { tag: "canvas", width: width, height: height, ops: [], fillColor: null, strokeColor: null };
  };
  graphics.clear = function (canvas, color) {
    canvas.ops.push({ op: "clear", color: color });
    return canvas;
  };
  graphics.fill = function (canvas, color) {
    canvas.fillColor = color;
    return canvas;
  };
  graphics.stroke = function (canvas, color) {
    canvas.strokeColor = color;
    return canvas;
  };
  graphics.line = function (canvas, x1, y1, x2, y2, color) {
    canvas.ops.push({ op: "line", x1: x1, y1: y1, x2: x2, y2: y2, color: color || canvas.strokeColor });
    return canvas;
  };
  graphics.rect = function (canvas, x, y, w, h, color) {
    canvas.ops.push({ op: "rect", x: x, y: y, w: w, h: h, color: color || canvas.fillColor });
    return canvas;
  };
  graphics.circle = function (canvas, cx, cy, r, color) {
    canvas.ops.push({ op: "circle", cx: cx, cy: cy, r: r, color: color || canvas.fillColor });
    return canvas;
  };
  graphics.polygon = function (canvas, points, color) {
    canvas.ops.push({ op: "polygon", points: points, color: color || canvas.fillColor });
    return canvas;
  };
  graphics.text = function (canvas, content, x, y, color) {
    canvas.ops.push({ op: "text", content: String(content), x: x, y: y, color: color || canvas.fillColor });
    return canvas;
  };
  graphics.render = function (canvas) {
    return canvas.ops.slice();
  };
  graphics.to_json = function (canvas) {
    return { tag: "canvas", width: canvas.width, height: canvas.height, ops: canvas.ops.slice() };
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);