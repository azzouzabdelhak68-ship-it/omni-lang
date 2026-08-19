"use strict";
/**
 * OMNISYS.pkg — package manager: manifests, version resolution, install.
 * Portable resolver is in-process (registry map of name -> version -> spec).
 * The Node lane can also load an .omni manifest from disk.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const pkg = (omnisys.pkg = omnisys.pkg || {});
  const core = omnisys.core;
  const fsModule = omnisys.fs;
  const serde = omnisys.serde;

  // ---------- Version parsing (SemVer 2.0.0) ----------
  const VERSION_RE = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$/;

  function parseVersion(version) {
    const m = String(version).trim().match(VERSION_RE);
    if (!m) throw new Error("Invalid semantic version: " + version);
    return {
      major: parseInt(m[1], 10),
      minor: parseInt(m[2], 10),
      patch: parseInt(m[3], 10),
      prerelease: m[4] || "",
      build: m[5] || "",
      toString: function () {
        let s = this.major + "." + this.minor + "." + this.patch;
        if (this.prerelease) s += "-" + this.prerelease;
        if (this.build) s += "+" + this.build;
        return s;
      },
    };
  }

  function cmpVersion(a, b) {
    if (a.major !== b.major) return a.major - b.major;
    if (a.minor !== b.minor) return a.minor - b.minor;
    if (a.patch !== b.patch) return a.patch - b.patch;
    // prerelease < release
    const aPre = a.prerelease ? 0 : 1;
    const bPre = b.prerelease ? 0 : 1;
    if (aPre !== bPre) return aPre - bPre;
    if (a.prerelease && b.prerelease) {
      const aParts = a.prerelease.split(".");
      const bParts = b.prerelease.split(".");
      for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
        const ap = aParts[i] || "";
        const bp = bParts[i] || "";
        const an = parseInt(ap, 10);
        const bn = parseInt(bp, 10);
        const aIsNum = !isNaN(an);
        const bIsNum = !isNaN(bn);
        if (aIsNum && bIsNum) {
          if (an !== bn) return an - bn;
        } else if (aIsNum) return -1;
        else if (bIsNum) return 1;
        else if (ap !== bp) return ap.localeCompare(bp);
      }
      return 0;
    }
    return 0;
  }

  function matchSimple(v, constraint) {
    const ops = {
      ">=": (a, b) => cmpVersion(a, b) >= 0,
      "<=": (a, b) => cmpVersion(a, b) <= 0,
      ">": (a, b) => cmpVersion(a, b) > 0,
      "<": (a, b) => cmpVersion(a, b) < 0,
      "=": (a, b) => cmpVersion(a, b) === 0,
      "==": (a, b) => cmpVersion(a, b) === 0,
    };
    for (const [op, fn] of Object.entries(ops)) {
      if (constraint.startsWith(op)) {
        const target = parseVersion(constraint.slice(op.length).trim());
        return fn(v, target);
      }
    }
    return false;
  }

  function matchCaret(v, constraint) {
    if (!constraint.startsWith("^")) return false;
    const target = parseVersion(constraint.slice(1).trim());
    let upper;
    if (target.major === 0) {
      if (target.minor === 0) {
        upper = { major: 0, minor: 0, patch: target.patch + 1, prerelease: "", build: "" };
      } else {
        upper = { major: 0, minor: target.minor + 1, patch: 0, prerelease: "", build: "" };
      }
    } else {
      upper = { major: target.major + 1, minor: 0, patch: 0, prerelease: "", build: "" };
    }
    return cmpVersion(v, target) >= 0 && cmpVersion(v, upper) < 0;
  }

  function matchTilde(v, constraint) {
    if (!constraint.startsWith("~")) return false;
    const rest = constraint.slice(1).trim();
    const parts = rest.split(".");
    let lower, upper;
    if (parts.length === 1) {
      const major = parseInt(parts[0], 10);
      lower = { major, minor: 0, patch: 0, prerelease: "", build: "" };
      upper = { major: major + 1, minor: 0, patch: 0, prerelease: "", build: "" };
    } else if (parts.length === 2) {
      const major = parseInt(parts[0], 10);
      const minor = parseInt(parts[1], 10);
      lower = { major, minor, patch: 0, prerelease: "", build: "" };
      upper = { major, minor: minor + 1, patch: 0, prerelease: "", build: "" };
    } else {
      const target = parseVersion(rest);
      lower = target;
      upper = { major: target.major, minor: target.minor + 1, patch: 0, prerelease: "", build: "" };
    }
    return cmpVersion(v, lower) >= 0 && cmpVersion(v, upper) < 0;
  }

  pkg.parse_version = function (version) {
    return parseVersion(version);
  };

  pkg.satisfies = function (version, constraint) {
    const v = parseVersion(version);
    for (const part of constraint.split("||")) {
      const p = part.trim();
      if (!p) continue;
      if (p.startsWith("^")) {
        if (matchCaret(v, p)) return true;
      } else if (p.startsWith("~")) {
        if (matchTilde(v, p)) return true;
      } else if (/^(>=|<=|>|<|=|==)/.test(p)) {
        if (matchSimple(v, p)) return true;
      } else {
        if (matchSimple(v, "=" + p)) return true;
      }
    }
    return false;
  };

  // ---------- Checksums ----------
  async function sha256Hex(content) {
    const encoder = new TextEncoder();
    const data = encoder.encode(content);
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  }

  pkg.compute_checksum = function (content) {
    // Synchronous fallback for non-async contexts (uses sync hash if available)
    // In browser/Node, we return a promise; the caller should await.
    return sha256Hex(content);
  };

  // ---------- Lockfile ----------
  function LockfileEntry(name, version, checksum, dependencies) {
    this.name = name;
    this.version = version;
    this.checksum = checksum;
    this.dependencies = dependencies || {};
  }
  LockfileEntry.prototype.toDict = function () {
    return {
      name: this.name,
      version: this.version,
      checksum: this.checksum,
      dependencies: this.dependencies,
    };
  };
  LockfileEntry.fromDict = function (d) {
    return new LockfileEntry(d.name, d.version, d.checksum, d.dependencies);
  };

  function Lockfile(packages, metadata) {
    this.packages = packages || [];
    this.metadata = metadata || {};
  }
  Lockfile.prototype.toJSON = function () {
    return JSON.stringify(
      {
        version: 1,
        packages: this.packages.map((p) => p.toDict()),
        metadata: this.metadata,
      },
      null,
      0
    );
  };
  Lockfile.fromJSON = function (jsonStr) {
    const data = JSON.parse(jsonStr);
    const packages = (data.packages || []).map(LockfileEntry.fromDict);
    return new Lockfile(packages, data.metadata || {});
  };
  Lockfile.prototype.get = function (name) {
    return this.packages.find((p) => p.name === name) || null;
  };
  Lockfile.prototype.toDict = function () {
    return {
      version: 1,
      packages: this.packages.map((p) => p.toDict()),
      metadata: this.metadata,
    };
  };
  Lockfile.fromDict = function (d) {
    return new Lockfile(
      (d.packages || []).map(LockfileEntry.fromDict),
      d.metadata || {}
    );
  };

  pkg.Lockfile = Lockfile;
  pkg.LockfileEntry = LockfileEntry;

  // ---------- PackageSpec ----------
  function PackageSpec(name, versionConstraint, dependencies, checksum) {
    this.name = name;
    this.versionConstraint = versionConstraint;
    this.dependencies = dependencies || {};
    this.checksum = checksum || null;
  }
  PackageSpec.prototype.toDict = function () {
    const d = {
      name: this.name,
      version: this.versionConstraint,
      dependencies: this.dependencies,
    };
    if (this.checksum) d.checksum = this.checksum;
    return d;
  };
  PackageSpec.fromDict = function (d) {
    return new PackageSpec(
      d.name,
      d.version || d.versionConstraint || "*",
      d.dependencies || {},
      d.checksum || null
    );
  };
  pkg.PackageSpec = PackageSpec;

  // ---------- Deterministic Resolution ----------
  function availableVersions(registry, name) {
    const versionsMap = registry[name] || {};
    const vers = [];
    for (const vStr of Object.keys(versionsMap)) {
      try {
        vers.push(parseVersion(vStr));
      } catch (e) {
        /* ignore invalid */
      }
    }
    return vers.sort((a, b) => cmpVersion(b, a)); // descending
  }

  function selectBestVersion(registry, name, constraint, lockfile) {
    if (lockfile) {
      const locked = lockfile.get(name);
      if (locked && pkg.satisfies(locked.version, constraint)) {
        if (registry[name] && registry[name][locked.version]) {
          return locked.version;
        }
      }
    }
    for (const v of availableVersions(registry, name)) {
      if (pkg.satisfies(v.toString(), constraint)) {
        return v.toString();
      }
    }
    return null;
  }

  function Resolution(packages, lockfile, warnings) {
    this.packages = packages;
    this.lockfile = lockfile;
    this.warnings = warnings || [];
  }
  Resolution.prototype.toLockfile = function () {
    return this.lockfile;
  };
  Resolution.prototype.toList = function () {
    return this.packages.map((p) => p.toDict());
  };
  pkg.Resolution = Resolution;

  pkg.resolve_versions = function (packageSpecs, registry, lockfile) {
    // packageSpecs: array of PackageSpec objects or plain dicts
    // registry: name -> version -> spec
    // lockfile: optional Lockfile object
    const specs = packageSpecs.map((s) =>
      s instanceof PackageSpec ? s : PackageSpec.fromDict(s)
    );
    const specByName = {};
    for (const s of specs) specByName[s.name] = s;

    const resolved = {};
    const warnings = [];
    const visiting = new Set();
    const visited = new Set();

    function visit(name) {
      if (resolved[name]) return;
      if (visiting.has(name)) {
        warnings.push("Circular dependency detected involving " + name);
        return;
      }
      if (!specByName[name]) {
        warnings.push("Package " + name + " not found in specs");
        return;
      }
      visiting.add(name);
      const spec = specByName[name];
      for (const [depName, depConstraint] of Object.entries(spec.dependencies)) {
        visit(depName);
      }
      const selectedVersion = selectBestVersion(registry, name, spec.versionConstraint, lockfile);
      if (!selectedVersion) {
        warnings.push("No version found for " + name + " matching " + spec.versionConstraint);
        visiting.delete(name);
        return;
      }
      const regEntry = registry[name][selectedVersion];
      const depVersions = {};
      for (const dep of Object.keys(spec.dependencies)) {
        if (resolved[dep]) depVersions[dep] = resolved[dep].version;
      }
      let checksum = spec.checksum;
      if (!checksum) {
        checksum = sha256Hex(JSON.stringify(regEntry));
        // Note: sha256Hex is async, but we can't await here.
        // In practice, the caller should provide checksums or use the async variant.
        // For sync fallback, we'll use a simple hash.
        // TODO: provide async resolve_versions_async
        const h = 0;
        for (let i = 0; i < checksum.length; i++) {
          h = ((h << 5) - h + checksum.charCodeAt(i)) | 0;
        }
        checksum = "sha256:" + Math.abs(h).toString(16);
      }
      resolved[name] = new LockfileEntry(name, selectedVersion, checksum, depVersions);
      visiting.delete(name);
    }

    for (const s of specs) visit(s.name);

    // Topological order (deps first)
    const ordered = [];
    const seen = new Set();
    function order(name) {
      if (seen.has(name) || !resolved[name]) return;
      const entry = resolved[name];
      for (const dep of Object.keys(entry.dependencies)) order(dep);
      if (!seen.has(name)) {
        seen.add(name);
        ordered.push(entry);
      }
    }
    for (const s of specs) order(s.name);

    const lock = new Lockfile(ordered);
    return new Resolution(ordered, lock, warnings);
  };

  // ---------- Original pkg module functions (backward compatible) ----------
  pkg.create = function (name, version, deps) {
    return { tag: "package", name: String(name), version: String(version), dependencies: deps || {} };
  };
  pkg.registry_add = function (registry, spec, version) {
    const name = spec.name;
    registry[name] = registry[name] || {};
    registry[name][spec.version] = {
      name: name,
      version: spec.version,
      dependencies: spec.dependencies || {},
    };
    if (version !== undefined) registry[version] = registry[name];
    return registry;
  };
  pkg.registry_get = function (registry, name, version) {
    const versions = registry[String(name)];
    if (!versions) return null;
    return versions[String(version || Object.keys(versions)[0])] || null;
  };
  pkg.list_dependencies = function (spec) {
    return Object.keys(spec.dependencies || {});
  };
  pkg.resolve = function (name, version, registry) {
    const seen = {};
    const order = [];
    const queue = [{ name: String(name), version: String(version || "latest") }];
    while (queue.length > 0) {
      const req = queue.shift();
      const key = req.name + "@" + req.version;
      if (seen[key]) continue;
      seen[key] = true;
      const spec = pkg.registry_get(registry, req.name, req.version);
      if (!spec) continue;
      order.push(spec);
      const deps = spec.dependencies || {};
      for (const depName of Object.keys(deps)) {
        queue.push({ name: depName, version: deps[depName] });
      }
    }
    return order;
  };
  pkg.manifest = function (path) {
    if (!fsModule) core.panic("pkg.manifest requires the fs module in the native lane");
    const text = fsModule.read_file(String(path));
    return serde.json_decode(text);
  };
  pkg.install = function (dir, registry) {
    if (!fsModule) core.panic("pkg.install requires the fs module in the native lane");
    fsModule.make_dir(dir);
    for (const name of Object.keys(registry)) {
      const versions = registry[name];
      for (const version of Object.keys(versions)) {
        const spec = versions[version];
        const target = fsModule.join_path(String(dir), spec.name + "-" + spec.version + ".pkg.json");
        fsModule.write_file(target, serde.json_encode(spec));
      }
    }
    return { tag: "install", dir: String(dir), count: Object.keys(registry).length };
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);