"use strict";
/**
 * OMNISYS runtime aggregator (Node lane).
 *
 * Loads every OMNISYS module into the shared global `omnisys` namespace in
 * dependency order and exports it. The JS emitter inlines the same module
 * sources directly (omni_compiler/emitter.py::_omnisys_runtime), so behavior
 * is identical whether a program is required() here or runs in the browser.
 */

require("./core.js");
require("./collections.js");
require("./error.js");
require("./serde.js");
require("./async.js");
require("./fs.js");
require("./test.js");
require("./ui.js");
require("./db.js");
require("./net.js");
require("./http.js");
require("./graphics.js");
require("./gpu.js");
require("./scene.js");
require("./sim.js");
require("./audio.js");
require("./video.js");
require("./platform.js");
require("./crypto.js");
require("./auth.js");
require("./observability.js");
require("./tool.js");
require("./ai.js");
require("./pkg.js");

module.exports = globalThis.omnisys;