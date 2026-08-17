# ruff: noqa: Q000, PLR0911, PLR0912
"""Rust Emitter Module with Bevy ECS Adapter.

Generates Rust 2021 code from OMNI MIR for native targets. The emitted code
uses the ``bevy`` crate for the simulation layer (``sim.*`` calls) and is a
plain, dependency-free program otherwise. Bevy sections are delimited by
comments so the simulation parts can be stripped and the file still compiles.
"""

from typing import Any

MIN_QUOTE_LEN = 2


def _rs_type(omni_type: str) -> str:
    """Map an OmniScript type to a Rust type."""
    type_map = {
        "Number": "f64",
        "Text": "String",
        "Boolean": "bool",
        "List": "Vec<f64>",
        "None": "()",
    }
    return type_map.get(omni_type, omni_type)


def _rs_text(raw: str) -> str:
    """Format a string literal for Rust."""
    body = raw[1:-1] if len(raw) >= MIN_QUOTE_LEN and raw[0] in ('"', "'") else raw
    return f'"{body}"'


def _rs_text_expr(raw: str) -> str:
    """Render a text literal with ``{slot}`` interpolation as a format! call."""
    body = raw[1:-1] if len(raw) >= MIN_QUOTE_LEN and raw[0] in ('"', "'") else raw
    fmt_parts: list[str] = []
    args: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == "{":
            j = body.find("}", i)
            if j == -1:
                buf.append(body[i:])
                break
            slot = body[i + 1:j]
            if buf:
                fmt_parts.append("".join(buf).replace("{", "{{").replace("}", "}}"))
                buf = []
            fmt_parts.append("{}")
            args.append(slot)
            i = j + 1
        else:
            buf.append(body[i])
            i += 1
    if buf:
        fmt_parts.append("".join(buf).replace("{", "{{").replace("}", "}}"))
    fmt = "".join(fmt_parts)
    if not args:
        return f'String::from("{fmt}")'
    return f'format!("{fmt}", {", ".join(args)})'


def _rs_expr(e: dict[str, Any], declared: set[str]) -> str:
    op = e.get("op")
    if op == "number":
        val = str(e["value"])
        return f"{val}.0" if "." not in val and "e" not in val.lower() else val
    if op == "boolean":
        return "true" if e["value"] else "false"
    if op == "none":
        return "()"
    if op == "ident":
        return str(e["name"])
    if op == "text":
        return _rs_text_expr(str(e["value"]))
    if op == "call":
        if e["name"] == "join" and len(e["args"]) == MIN_QUOTE_LEN:
            lst = _rs_expr(e["args"][0], declared)
            sep = _rs_expr(e["args"][1], declared)
            return f"omni_join({lst}, {sep})"
        if str(e["name"]).startswith("sim."):
            return _rs_sim_call(e, declared)
        args = ", ".join(_rs_expr(a, declared) for a in e["args"])
        return f"{e['name']}({args})"
    if op == "list":
        items = ", ".join(_rs_expr(i, declared) for i in e["items"])
        return f"vec![{items}]"
    if op == "field":
        return f"{_rs_expr(e['object'], declared)}.{e['field']}"
    if op == "struct":
        parts = [f"{name}: {_rs_expr(value, declared)}" for name, value in e["args"].items()]
        return f"{e['name']} {{ {', '.join(parts)} }}"
    op_map = {
        "is": "==",
        "is not": "!=",
        "and": "&&",
        "or": "||",
        "greater than": ">",
        "less than": "<",
        "greater or equal": ">=",
        "less or equal": "<=",
    }
    cop = op_map.get(str(op), str(op))
    return f"{_rs_expr(e['left'], declared)} {cop} {_rs_expr(e['right'], declared)}"


def _rs_sim_call(e: dict[str, Any], declared: set[str]) -> str:
    """Lower a sim.* call inside a function to its Bevy/plain form."""
    name = str(e.get("name", ""))
    args = e.get("args", [])
    if name == "sim.entity":
        name_arg = _rs_text(str(args[0].get("value", "entity")))
        return f'// sim.entity {name_arg} -> Bevy spawn in App setup'
    if name == "sim.system":
        fn_arg = str(args[1].get("name", "")) if len(args) > 1 else ""
        return f'// sim.system {fn_arg} -> Bevy Update system'
    if name == "sim.for_each":
        return "// sim.for_each -> Bevy Query"
    return f"{name}({', '.join(_rs_expr(a, declared) for a in args)})"


def _rs_stmt(s: dict[str, Any], declared: set[str], indent: int = 4) -> str:
    pad = " " * indent
    op = s.get("op")
    if op == "assign":
        var_name = s["name"]
        if var_name not in declared:
            declared.add(var_name)
            return f"{pad}let mut {var_name} = {_rs_expr(s['expr'], declared)};"
        return f"{pad}{var_name} = {_rs_expr(s['expr'], declared)};"
    if op == "return":
        return f"{pad}return {_rs_expr(s['expr'], declared)};"
    if op == "show":
        return f"{pad}println!(\"{{}}\", {_rs_expr(s['expr'], declared)});"
    if op == "break":
        return f"{pad}break;"
    if op == "continue":
        return f"{pad}continue;"
    if op == "if":
        lines = [f"{pad}if {_rs_expr(s['cond'], declared)} {{"]
        for st in s["body"]:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f"{pad}}}")
        if s.get("else"):
            lines.append(f"{pad}else {{")
            for st in s["else"]:
                lines.append(_rs_stmt(st, declared, indent + 2))
            lines.append(f"{pad}}}")
        return "\n".join(lines)
    if op == "for":
        var = s["var"]
        iterable = _rs_expr(s["iterable"], declared)
        lines = [f"{pad}for x in &{iterable} {{", f"{pad}  let {var} = x;"]
        for st in s["body"]:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if op == "call":
        return f"{pad}{_rs_expr(s, declared)};"
    return f"{pad}// unknown statement: {s!r}"


def _rs_preamble(custom_types: dict[str, Any]) -> list[str]:
    lines = [
        "// Generated by the OmniScript Rust Emitter (v3.2)",
        "",
        "// Bevy ECS integration (optional).",
        "// Remove the `bevy` sections below to build as a plain Rust program.",
        '// #[cfg(feature = "bevy")]',
        "// use bevy::prelude::*;",
        "",
    ]
    for tname, fields_info in custom_types.items():
        fields = (
            fields_info.get("fields", fields_info)
            if isinstance(fields_info, dict)
            else fields_info
        )
        lines.append("#[derive(Clone, Debug)]")
        lines.append(f"struct {tname} {{")
        for fname, ftype in fields.items():
            lines.append(f"    {fname}: {_rs_type(ftype)},")
        lines.append("}")
        lines.append("")
    lines.append("fn omni_join(list: Vec<String>, sep: &str) -> String {")
    lines.append("    list.join(sep)")
    lines.append("}")
    lines.append("")
    return lines


def _rs_sim_components(mir: Any) -> tuple[list[str], list[str]]:
    """Return (component structs, spawn functions) for sim.* usage in entry point."""
    used: list[str] = []
    structs: list[str] = []
    spawn_lines: list[str] = []
    for stmt in mir.entry_point:
        if stmt.get("op") != "call" or not str(stmt.get("name", "")).startswith("sim."):
            continue
        for arg in stmt.get("args", []):
            if arg.get("op") != "list":
                continue
            for item in arg.get("items", []):
                if item.get("op") == "struct" and item["name"] not in used:
                    used.append(item["name"])
    for tname in used:
        fields_info = mir.types.get(tname, {})
        fields = (
            fields_info.get("fields", fields_info)
            if isinstance(fields_info, dict)
            else fields_info
        )
        structs.append("#[derive(Component, Clone, Debug)]")
        structs.append(f"struct {tname} {{")
        for fname, ftype in fields.items():
            structs.append(f"    {fname}: {_rs_type(ftype)},")
        structs.append("}")
        structs.append("")
    if used:
        spawn_lines.append("// Bevy app setup (sim.entity / sim.system / sim.for_each)")
        spawn_lines.append('#[cfg(feature = "bevy")]')
        spawn_lines.append("fn setup(mut commands: Commands) {")
        for stmt in mir.entry_point:
            is_entity = (
                stmt.get("op") == "call"
                and str(stmt.get("name", "")) == "sim.entity"
                and len(stmt.get("args", [])) >= MIN_QUOTE_LEN
            )
            if is_entity:
                name_arg = _rs_text(str(stmt["args"][0].get("value", "entity")))
                spawn_lines.append("    commands.spawn((")
                for item in stmt["args"][1].get("items", []):
                    if item.get("op") == "struct":
                        spawn_lines.append(f"        {_rs_expr(item, set())},")
                spawn_lines.append(f"    )).insert(Name::new({name_arg}));")
        spawn_lines.append("}")
        spawn_lines.append("")
    return structs, spawn_lines


def emit_rust(mir: Any) -> str:
    """Emit Rust 2021 code with a Bevy adapter from OMNI MIR."""
    lines = _rs_preamble(mir.types)

    component_structs, spawn = _rs_sim_components(mir)
    if component_structs:
        lines.append("// Bevy components (sim.* usage)")
        lines.extend(component_structs)

    for fn in mir.functions.values():
        params = ", ".join(f"{p.name}: {_rs_type(p.type)}" for p in fn.params)
        ret = _rs_type(fn.return_type)
        ret_arrow = f" -> {ret}" if fn.return_type != "None" else ""
        lines.append(f"fn {fn.name}({params}){ret_arrow} {{")
        if fn.effects.uses or fn.effects.reads or fn.effects.writes:
            uses = ", ".join(fn.effects.uses)
            reads = ", ".join(fn.effects.reads)
            writes = ", ".join(fn.effects.writes)
            lines.append(f"    // effects: uses=[{uses}] reads=[{reads}] writes=[{writes}]")
        declared: set[str] = {p.name for p in fn.params}
        for stmt in fn.body:
            lines.append(_rs_stmt(stmt, declared, 4))
        lines.append("}")
        lines.append("")

    lines.extend(spawn)

    lines.append("fn main() {")
    lines.append("    // when app starts")
    declared_main: set[str] = set()
    for stmt in mir.entry_point:
        if stmt.get("op") == "call" and str(stmt.get("name", "")).startswith("sim."):
            lines.append("    " + _rs_expr(stmt, declared_main))
            continue
        lines.append(_rs_stmt(stmt, declared_main, 4))
    lines.append("}")
    lines.append("")

    if mir.scene:
        lines.append("// 3D scene: render via the JS/WebGPU lane or a Bevy scene plugin.")
        lines.append("// scene objects: " + ", ".join(o["shape"] for o in mir.scene))

    return "\n".join(lines)


def emit_rust_with_runtime(mir: Any) -> str:
    """Emit Rust code with the embedded runtime (alias of emit_rust)."""
    return emit_rust(mir)