# Repo metadata: apply these in GitHub → Settings / About

This file holds the exact strings for the repository-level fields that live in
GitHub settings (not in code). Apply them once; revisit when positioning changes.

## Description (Settings → General → About)

Paste into "Description" (350-character limit):

```text
AI-first programming language and compiler. One .omni file compiles through OMNI MIR to JavaScript, WASM, and native C, with a static effect system, capability borrowing, and SMT-verified contracts. Safety checked before your program ever runs.
```

239 characters. Front-loads every search term a stranger might type:
programming language, compiler, MIR, effect system, multi-backend, AI.

## Website (Settings → General → About)

Point at the rendered spec or docs site when one exists. Until then, leave empty;
a dead link costs more credibility than no link.

## Topics (About → gear icon → Topics)

Core set (apply exactly):

```text
programming-language compiler language-design compiler-design static-analysis effect-system intermediate-representation ai developer-tools
```

Optional additions once they earn their place:

```text
mir code-generation capability-system wasm webassembly smt z3 language-server ai-agents
```

Rules GitHub enforces: lowercase letters, numbers, hyphens only; 50 topics max.

## Releases

Releases are published automatically by `.github/workflows/release.yml`: push a
tag `vX.Y.Z` and CI builds the wheel, smoke-tests it in a clean venv, and
publishes a release whose notes walk through install → first program → result.
Keep that promise intact when editing the workflow.

## Social preview

Upload a 1280×640 image showing the OmniScript name, one `.omni` snippet, and
the three backend logos (JS, WASM, C). This image is what most people see first
when the repo is shared.
