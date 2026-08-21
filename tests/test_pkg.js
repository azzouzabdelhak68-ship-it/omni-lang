"use strict";
/**
 * Standalone tests for the OMNISYS.pkg JS lane (omnisys/pkg.js).
 *
 * Usage: node tests/test_pkg.js
 *
 * Mirrors the Python reference lane (packages/omnisys-pkg/tests/test_pkg.py):
 * checksums, `*` constraints, transitive registry deps, and install-time
 * lockfile checksum verification.
 */

const assert = require("assert");
const nodeFs = require("fs");
const nodePath = require("path");
const os = require("os");

const omnisys = require("../omnisys/runtime.js");
const pkg = omnisys.pkg;

const tests = [];

function test(name, fn) {
  tests.push({ name, fn });
}

// ---------------------------------------------------------------------------
// Checksums
// ---------------------------------------------------------------------------

test("resolve_versions produces a real sha256 checksum, not sha256:0", () => {
  const registry = {
    app: {
      "1.0.0": { name: "app", version: "1.0.0", dependencies: {} },
    },
  };
  const resolution = pkg.resolve_versions([new pkg.PackageSpec("app", "1.0.0", {})], registry);
  const checksum = resolution.packages[0].checksum;
  assert.match(checksum, /^sha256:[0-9a-f]{64}$/, "checksum is a full sha256 hex: " + checksum);
  assert.notStrictEqual(checksum, "sha256:0");
});

test("resolve_versions checksum is deterministic and matches compute_checksum", () => {
  const registry = {
    app: {
      "1.0.0": { name: "app", version: "1.0.0", dependencies: {} },
    },
  };
  const r1 = pkg.resolve_versions([new pkg.PackageSpec("app", "1.0.0", {})], registry);
  const r2 = pkg.resolve_versions([new pkg.PackageSpec("app", "1.0.0", {})], registry);
  assert.strictEqual(r1.packages[0].checksum, r2.packages[0].checksum);
  const expected = pkg.compute_checksum(JSON.stringify(registry.app["1.0.0"]));
  assert.strictEqual(r1.packages[0].checksum, expected);
});

// ---------------------------------------------------------------------------
// `*` constraint
// ---------------------------------------------------------------------------

test("satisfies('*') matches any version", () => {
  assert.strictEqual(pkg.satisfies("1.0.0", "*"), true);
  assert.strictEqual(pkg.satisfies("2.5.3", "*"), true);
  assert.strictEqual(pkg.satisfies("0.0.1", "*"), true);
});

test("* constraint resolves to the highest available version", () => {
  const registry = {
    app: {
      "1.0.0": { name: "app", version: "1.0.0", dependencies: {} },
      "2.0.0": { name: "app", version: "2.0.0", dependencies: {} },
      "2.1.0": { name: "app", version: "2.1.0", dependencies: {} },
    },
  };
  const resolution = pkg.resolve_versions([{ name: "app" }], registry);
  assert.strictEqual(resolution.packages.length, 1);
  assert.strictEqual(resolution.packages[0].version, "2.1.0");
  assert.strictEqual(resolution.warnings.length, 0);
});

test("* constraint works through the legacy resolve() BFS lane", () => {
  const registry = {
    app: {
      "1.0.0": { name: "app", version: "1.0.0", dependencies: {} },
      "2.0.0": { name: "app", version: "2.0.0", dependencies: {} },
    },
  };
  const order = pkg.resolve("app", "*", registry);
  assert.strictEqual(order.length, 1);
  assert.strictEqual(order[0].version, "2.0.0");
});

// ---------------------------------------------------------------------------
// Transitive dependencies
// ---------------------------------------------------------------------------

test("transitive deps declared in the spec resolve (deps first, highest match)", () => {
  const registry = {
    app: {
      "1.0.0": { name: "app", version: "1.0.0", dependencies: { lib: "^2.0.0" } },
    },
    lib: {
      "2.0.0": { name: "lib", version: "2.0.0", dependencies: {} },
      "2.1.0": { name: "lib", version: "2.1.0", dependencies: {} },
      "3.0.0": { name: "lib", version: "3.0.0", dependencies: {} },
    },
  };
  const resolution = pkg.resolve_versions(
    [new pkg.PackageSpec("app", "1.0.0", { lib: "^2.0.0" })],
    registry
  );
  assert.strictEqual(resolution.packages.length, 2);
  assert.strictEqual(resolution.packages[0].name, "lib");
  assert.strictEqual(resolution.packages[0].version, "2.1.0");
  assert.strictEqual(resolution.packages[1].name, "app");
  assert.deepStrictEqual(resolution.packages[1].dependencies, { lib: "2.1.0" });
});

test("transitive deps declared only on the registry entry resolve", () => {
  const registry = {
    app: {
      "1.0.0": { name: "app", version: "1.0.0", dependencies: { lib: "^2.0.0" } },
    },
    lib: {
      "2.0.0": { name: "lib", version: "2.0.0", dependencies: {} },
      "2.1.0": { name: "lib", version: "2.1.0", dependencies: {} },
      "3.0.0": { name: "lib", version: "3.0.0", dependencies: {} },
    },
  };
  const resolution = pkg.resolve_versions([new pkg.PackageSpec("app", "1.0.0", {})], registry);
  assert.strictEqual(resolution.packages.length, 2);
  assert.strictEqual(resolution.packages[0].name, "lib");
  assert.strictEqual(resolution.packages[0].version, "2.1.0");
  assert.strictEqual(resolution.packages[1].name, "app");
  assert.deepStrictEqual(resolution.packages[1].dependencies, { lib: "2.1.0" });
});

test("diamond dependencies are deduplicated and ordered deps-first", () => {
  const registry = {
    app: {
      "1.0.0": {
        name: "app",
        version: "1.0.0",
        dependencies: { left: "1.0.0", right: "1.0.0" },
      },
    },
    left: {
      "1.0.0": { name: "left", version: "1.0.0", dependencies: { shared: "1.0.0" } },
    },
    right: {
      "1.0.0": { name: "right", version: "1.0.0", dependencies: { shared: "1.0.0" } },
    },
    shared: {
      "1.0.0": { name: "shared", version: "1.0.0", dependencies: {} },
    },
  };
  const resolution = pkg.resolve_versions(
    [new pkg.PackageSpec("app", "1.0.0", { left: "1.0.0", right: "1.0.0" })],
    registry
  );
  const names = resolution.packages.map((p) => p.name);
  assert.strictEqual(names.filter((n) => n === "shared").length, 1);
  assert.ok(names.indexOf("shared") < names.indexOf("left"));
  assert.ok(names.indexOf("shared") < names.indexOf("right"));
  assert.strictEqual(names[names.length - 1], "app");
});

// ---------------------------------------------------------------------------
// Install with lockfile checksum verification
// ---------------------------------------------------------------------------

function makeRegistry() {
  return {
    app: {
      "1.0.0": { name: "app", version: "1.0.0", dependencies: { lib: "1.0.0" } },
    },
    lib: {
      "1.0.0": { name: "lib", version: "1.0.0", dependencies: {} },
    },
  };
}

function tempDir() {
  return nodeFs.mkdtempSync(nodePath.join(os.tmpdir(), "omnisys-pkg-test-"));
}

test("install writes .pkg.json files when lockfile checksums match", () => {
  const registry = makeRegistry();
  const resolution = pkg.resolve_versions(
    [new pkg.PackageSpec("app", "1.0.0", { lib: "1.0.0" })],
    registry
  );
  const dir = tempDir();
  try {
    const result = pkg.install(dir, registry, resolution.lockfile);
    assert.strictEqual(result.tag, "install");
    assert.strictEqual(result.count, 2);
    assert.ok(nodeFs.existsSync(nodePath.join(dir, "app-1.0.0.pkg.json")));
    assert.ok(nodeFs.existsSync(nodePath.join(dir, "lib-1.0.0.pkg.json")));
  } finally {
    nodeFs.rmSync(dir, { recursive: true, force: true });
  }
});

test("install without a lockfile keeps legacy behavior", () => {
  const registry = makeRegistry();
  const dir = tempDir();
  try {
    const result = pkg.install(dir, registry);
    assert.strictEqual(result.count, 2);
    assert.ok(nodeFs.existsSync(nodePath.join(dir, "app-1.0.0.pkg.json")));
  } finally {
    nodeFs.rmSync(dir, { recursive: true, force: true });
  }
});

test("install fails when the registry content was tampered", () => {
  const registry = makeRegistry();
  const resolution = pkg.resolve_versions(
    [new pkg.PackageSpec("app", "1.0.0", { lib: "1.0.0" })],
    registry
  );
  registry.app["1.0.0"].dependencies = { evil: "1.0.0" };
  const dir = tempDir();
  try {
    assert.throws(
      () => pkg.install(dir, registry, resolution.lockfile),
      /checksum mismatch for app@1\.0\.0/
    );
    assert.ok(!nodeFs.existsSync(nodePath.join(dir, "app-1.0.0.pkg.json")));
  } finally {
    nodeFs.rmSync(dir, { recursive: true, force: true });
  }
});

test("install fails when the lockfile has no entry for a package", () => {
  const registry = makeRegistry();
  const resolution = pkg.resolve_versions(
    [new pkg.PackageSpec("app", "1.0.0", { lib: "1.0.0" })],
    registry
  );
  registry.extra = {
    "1.0.0": { name: "extra", version: "1.0.0", dependencies: {} },
  };
  const dir = tempDir();
  try {
    assert.throws(
      () => pkg.install(dir, registry, resolution.lockfile),
      /no lockfile checksum for extra@1\.0\.0/
    );
  } finally {
    nodeFs.rmSync(dir, { recursive: true, force: true });
  }
});

// ---------------------------------------------------------------------------
// Runner
// ---------------------------------------------------------------------------

let failed = 0;
for (const t of tests) {
  try {
    t.fn();
    console.log("ok - " + t.name);
  } catch (e) {
    failed += 1;
    console.error("FAIL - " + t.name);
    console.error((e && e.stack ? e.stack : e).toString());
  }
}
if (failed) {
  console.error(failed + " of " + tests.length + " tests failed");
  process.exit(1);
}
console.log("all " + tests.length + " tests passed");
process.exit(0);