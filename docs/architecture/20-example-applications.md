# OMNISYS Example Applications

**Deliverable §14U.** The reference applications that exercise OMNISYS
end-to-end — and how they map to the v7 benchmark.

---

## 1. The Reference Set (spec §17.9U)

OMNISYS MUST be proven by these application classes:

| # | Application | Modules exercised |
|---|-------------|-------------------|
| 1 | CRUD SaaS | `db`, `http`, `auth`, `serde` |
| 2 | Desktop GUI | `ui`, `fs`, `platform` |
| 3 | Web app | `ui`, `http`, `net` |
| 4 | 3D app | `scene`, `graphics`, `gpu` |
| 5 | Game | `sim`, `scene`, `audio`, `async` |
| 6 | GPU compute | `gpu`, `graphics` |
| 7 | Networking server | `net`, `http`, `async`, `crypto` |
| 8 | Multimedia | `audio`, `video`, `platform` |
| 9 | AI | `ai`, `gpu`, `serde` |

## 2. Mapping to the v7 Benchmark

Each reference class maps to one or more benchmark projects
(`OMNISCRIPT_AI_BENCHMARK/`), which measure the AI × ecosystem interaction:

| Phase | Benchmark projects |
|-------|--------------------|
| Phase 0 — Language discovery | unit converter, todo engine, RPG action engine, particle motion, state-machine adventure |
| Phase 1 — Foundations | log analyzer (collections), file organizer (fs), config exporter (serde), error recovery, self-test suite, async job processor |
| Phase 2 — App foundations | finance dashboard (ui), inventory system (db), REST client (http), chat server (net) |
| Phase 3 — Graphics/GPU/Sim | canvas app, solar system (scene), image filter (gpu), ECS particle coexistence (sim) |
| Phase 4 — Media/Platform | voice recorder, video player, camera capture, system utility |
| Phase 5 — Security/Tooling | file vault (crypto), auth web service, app diagnostics (observability), project inspection (tool), native interop |
| Phase 6 — AI/Advanced | AI assistant (ai), distributed actors, multi-package app (pkg) |

`STATUS: BLOCKED` projects unlock as the matching v6 modules ship (e.g. the
async job processor unlocks when `OMNISYS.async` lands).

## 3. Example Snippets

**CRUD + HTTP + Auth** (the "CRUD SaaS" class):

```omni
import OMNISYS.db
import OMNISYS.http

fn handle_request(req: Map) -> Response:
    uses network
    uses database
    t = create_table(create_db("app.db"), "items", {id: "Number", name: "Text"})
    insert(t, {id: 1, name: "bolt"})
    return response_json(200, select(t, (r) -> true))
end

when app starts:
    srv = server(handle_request)
    start(srv)
end
```

**Game loop** (the "Game" class):

```omni
import OMNISYS.sim
import OMNISYS.scene

fn move_system(w: World) -> World:
    writes Position
    pure
    # model-level movement
    return w
end

when app starts:
    w = world()
    entity(w, "player")
    run(w, 60)
end
```

## 4. Acceptance Criterion

Each example application must:

- compile with `omni check` (code 0),
- run on its target with `omni run` (observable output),
- declare its capabilities honestly,
- pass the package's tests.

## 5. Reference Implementation Policy

Examples are written against the **portable core** first; escapes are shown
only where the class demands backend-specific power (GPU kernels, native
device access). This mirrors the Escape-Hatch rule (§14R).