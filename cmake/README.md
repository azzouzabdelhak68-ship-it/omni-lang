# Building an OmniScript program natively

The C emitter (`omni build app.omni --target c`) produces a single C99 file
with an embedded Flecs adapter. Two build paths are supported.

## 1. Without Flecs (plain C99, deterministic fallback)

The emitted `main` guards every Flecs call with `OMNI_HAVE_FLECS`. Without
that macro, registered systems simply run once per tick in a deterministic
loop — no external dependency needed:

```
cc -std=c99 app.c -o app
./app
```

## 2. With Flecs (native ECS)

The CMake project fetches Flecs v4 and builds a native binary:

```
cmake -S cmake -B build -DOMNI_SOURCE=C:\path\to\app.c
cmake --build build --config Release
build\omni_app.exe
```

`OMNI_SOURCE` defaults to `cmake/app.c`; point it at your emitted file.

## Toolchains

- clang / gcc: `cc` or `clang` as above.
- MSVC: use the CMake path (Visual Studio generator).
- WASM: see the wasm target — `omni build app.omni --target wasm-browser`
  prints the `clang --target=wasm32` command.