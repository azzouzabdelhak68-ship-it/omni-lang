# ruff: noqa: Q000, PLR0911, PLR0912, PLR0915, PLR2004
"""C99 Emitter Module with Flecs Adapter.

Generates typed C99 code from OMNI MIR for native desktop and simulation
targets. The generated code is guarded by ``OMNI_HAVE_FLECS``: when defined
the Flecs C API is used for entities/components/systems; otherwise a plain
deterministic fallback loop runs registered systems, so the emitted file
still compiles without the Flecs library.
"""

from typing import Any

MIN_QUOTE_LEN = 2

_C_TYPE_MAP = {
    "Number": "double",
    "Text": "const char*",
    "Boolean": "bool",
    "List": "OmniList",
    "None": "void",
}


def _c_type(omni_type: str) -> str:
    """Map an OmniScript type to a C type."""
    return _C_TYPE_MAP.get(omni_type, omni_type)


def _c_text(raw: str) -> str:
    """Format a string literal for C."""
    body = raw[1:-1] if len(raw) >= MIN_QUOTE_LEN and raw[0] in ('"', "'") else raw
    return f'"{body}"'


def _expr_type(
    e: dict[str, Any],
    types: dict[str, str],
    custom_types: dict[str, Any],
) -> str:
    """Best-effort static type inference for a MIR expression dict."""
    op = e.get("op")
    if op == "number":
        return "Number"
    if op == "text":
        return "Text"
    if op == "boolean":
        return "Boolean"
    if op == "none":
        return "None"
    if op == "list":
        return "List"
    if op == "struct":
        return str(e["name"])
    if op == "ident":
        return types.get(str(e["name"]), "Number")
    if op == "field":
        base = _expr_type(e.get("object", {}), types, custom_types)
        fields = custom_types.get(base)
        if fields:
            return str(fields.get(str(e.get("field")), "Number"))
        return "Number"
    if op == "call":
        if e.get("name") == "join":
            return "Text"
        return "Number"
    if op in ("is", "is not", "and", "or"):
        return "Boolean"
    if op in ("greater than", "less than", "greater or equal", "less or equal"):
        return "Boolean"
    return "Number"


def _slot_type(expr_text: str, types: dict[str, str]) -> str:
    """Infer the type of a ``{slot}`` expression embedded in a text literal."""
    slot = expr_text.strip()
    if slot and slot.replace("_", "").isalnum() and not slot[0].isdigit():
        return types.get(slot, "Number")
    return "Number"


def _c_text_expr(raw: str, types: dict[str, str], _custom_types: dict[str, Any]) -> str:
    """Render a text literal with ``{slot}`` interpolation as omni_format()."""
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
                fmt_parts.append("".join(buf).replace("%", "%%"))
                buf = []
            stype = _slot_type(slot, types)
            if stype == "Text":
                fmt_parts.append("%s")
                args.append(f"((const char*)({slot}))")
            elif stype == "Boolean":
                fmt_parts.append("%s")
                args.append(f"(({slot}) ? 'true' : 'false')".replace("'", '"'))
            else:
                fmt_parts.append("%f")
                args.append(f"(double)({slot})")
            i = j + 1
        else:
            buf.append(body[i])
            i += 1
    if buf:
        fmt_parts.append("".join(buf).replace("%", "%%"))
    if not fmt_parts:
        return '""'
    if not args:
        return _c_text(raw)
    fmt = "".join(fmt_parts)
    return f'omni_format("{fmt}", {", ".join(args)})'


def _c_expr_unary_and_literals(
    e: dict[str, Any],
    custom_types: dict[str, Any],
    types: dict[str, str] | None = None,
) -> str | None:
    types = types or {}
    op = e.get("op")
    if op == "number":
        val = str(e["value"])
        return f"{val}.0" if "." not in val and "e" not in val.lower() else val
    if op == "boolean":
        return "true" if e["value"] else "false"
    if op == "none":
        return "NULL"
    if op == "ident":
        return str(e["name"])
    if op == "text":
        if "{" in str(e["value"]):
            return _c_text_expr(str(e["value"]), types, custom_types)
        return _c_text(str(e["value"]))
    if op == "list":
        items = ", ".join(_c_expr(i, custom_types, types) for i in e["items"])
        return f"omni_make_list((void*[]){{{items}}}, {len(e['items'])})"
    if op == "field":
        return f"{_c_expr(e['object'], custom_types, types)}.{e['field']}"
    if op == "struct":
        struct_type = e["name"]
        fields = ", ".join(
            f".{k} = {_c_expr(v, custom_types, types)}" for k, v in e["args"].items()
        )
        return f"({struct_type}){{ {fields} }}"
    if op == "call":
        args = ", ".join(_c_expr(a, custom_types, types) for a in e["args"])
        return f"omni_join({args})" if e["name"] == "join" else f"{e['name']}({args})"
    return None


def _c_expr(
    e: dict[str, Any],
    custom_types: dict[str, Any],
    types: dict[str, str] | None = None,
) -> str:
    unary_res = _c_expr_unary_and_literals(e, custom_types, types)
    if unary_res is not None:
        return unary_res

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
    cop = op_map.get(e.get("op", ""), e.get("op", ""))
    left = _c_expr(e["left"], custom_types, types)
    right = _c_expr(e["right"], custom_types, types)
    return f"({left} {cop} {right})"


def _c_stmt(
    s: dict[str, Any],
    declared_vars: set[str],
    custom_types: dict[str, Any],
    indent: int = 2,
    types: dict[str, str] | None = None,
) -> str:
    if types is None:
        types = {}
    pad = " " * indent
    op = s.get("op")
    if op == "assign":
        var_name = s["name"]
        vtype = _expr_type(s["expr"], types, custom_types)
        types[var_name] = vtype
        if var_name not in declared_vars:
            declared_vars.add(var_name)
            return f"{pad}{_c_type(vtype)} {var_name} = {_c_expr(s['expr'], custom_types, types)};"
        return f"{pad}{var_name} = {_c_expr(s['expr'], custom_types, types)};"
    if op == "return":
        return f"{pad}return {_c_expr(s['expr'], custom_types, types)};"
    if op == "show":
        return _c_show(s["expr"], custom_types, types, pad)
    if op in ("break", "continue"):
        return f"{pad}{op};"
    if op == "if":
        lines = [f"{pad}if ({_c_expr(s['cond'], custom_types, types)}) {{"]
        for st in s["body"]:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f"{pad}}}")
        if s.get("else"):
            lines.append(f"{pad}else {{")
            for st in s["else"]:
                lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
            lines.append(f"{pad}}}")
        return "\n".join(lines)
    if op == "for":
        var = s["var"]
        iterable = _c_expr(s["iterable"], custom_types, types)
        elem_type = _list_elem_type(s["iterable"], types, custom_types)
        c_elem = _c_type(elem_type)
        declared_vars.add(var)
        types[var] = elem_type
        lines = [
            f"{pad}for (int _i_{var} = 0; _i_{var} < {iterable}.count; _i_{var}++) {{",
            f"{pad}  {c_elem} {var} = (({c_elem}*){iterable}.items)[_i_{var}];",
        ]
        for st in s["body"]:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f"{pad}}}")
        return "\n".join(lines)
    if op == "call":
        return f"{pad}{_c_expr(s, custom_types, types)};"
    return f"{pad}// unknown statement: {s!r}"


def _list_elem_type(
    iterable: dict[str, Any],
    types: dict[str, str],
    custom_types: dict[str, Any],
) -> str:
    """Determine the element type of a list expression (best effort)."""
    if iterable.get("op") == "list":
        items = iterable.get("items", [])
        if items:
            return _expr_type(items[0], types, custom_types)
        return "Number"
    if iterable.get("op") == "ident":
        return types.get(str(iterable["name"]), "Number")
    return "Number"


def _c_show(
    expr: dict[str, Any], custom_types: dict[str, Any], types: dict[str, str], pad: str
) -> str:
    """Emit a printf statement matching the expression type."""
    vtype = _expr_type(expr, types, custom_types)
    cexpr = _c_expr(expr, custom_types, types)
    if vtype == "Text":
        return f'{pad}printf("%s\\n", ({cexpr}));'
    if vtype == "Boolean":
        return f'{pad}printf("%s\\n", ({cexpr}) ? "true" : "false");'
    if vtype in custom_types:
        return f"{pad}// show struct: {cexpr}"
    return f'{pad}printf("%f\\n", (double)({cexpr}));'


def _emit_c_type_decls(custom_types: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for tname, fields_info in custom_types.items():
        fields = (
            fields_info.get("fields", fields_info)
            if isinstance(fields_info, dict)
            else fields_info
        )
        lines.append(f"typedef struct {tname} {{")
        for fname, ftype in fields.items():
            lines.append(f"  {_c_type(ftype)} {fname};")
        lines.append(f"}} {tname};")
        lines.append("")
    return lines


def _component_name(
    item: dict[str, Any],
    constructs: dict[str, dict[str, Any]],
    types: dict[str, str],
) -> str | None:
    """Resolve a sim component item (struct construct or variable) to a type name."""
    if item.get("op") == "struct":
        return str(item["name"])
    if item.get("op") == "ident":
        name = str(item["name"])
        if name in constructs:
            return str(constructs[name]["name"])
        return types.get(name)
    return None


def _component_field_values(
    item: dict[str, Any],
    constructs: dict[str, dict[str, Any]],
    custom_types: dict[str, Any],
) -> list[str]:
    """Extract ordered field values for a component item."""
    construct = item if item.get("op") == "struct" else constructs.get(str(item.get("name", "")))
    if not construct:
        return []
    return [
        _c_expr(construct["args"][f], custom_types)
        for f in _struct_field_order(construct, custom_types)
    ]


def _component_types_used(
    mir: Any, constructs: dict[str, dict[str, Any]], types: dict[str, str]
) -> list[str]:
    """Return the custom types referenced by sim.* calls in the entry point."""
    used: list[str] = []
    for stmt in mir.entry_point:
        if stmt.get("op") != "call" or not str(stmt.get("name", "")).startswith("sim."):
            continue
        for arg in stmt.get("args", []):
            if arg.get("op") != "list":
                continue
            for item in arg.get("items", []):
                cname = _component_name(item, constructs, types)
                if cname and cname not in used:
                    used.append(cname)
    return used


def _struct_field_order(struct_expr: dict[str, Any], custom_types: dict[str, Any]) -> list[str]:
    """Order the fields of a struct construct by declaration order."""
    name = struct_expr["name"]
    fields = custom_types.get(name, {})
    ordered = [f for f in fields if f in struct_expr.get("args", {})]
    for f in struct_expr.get("args", {}):
        if f not in ordered:
            ordered.append(f)
    return ordered


def _emit_sim_lowering(
    mir: Any,
    custom_types: dict[str, Any],
    constructs: dict[str, dict[str, Any]],
    types: dict[str, str],
) -> list[str]:
    """Lower sim.* calls in the entry point to Flecs C API calls."""
    lines: list[str] = []
    components = _component_types_used(mir, constructs, types)
    entity_idx = 0
    fallback_systems: list[str] = []
    entity_specs: list[tuple[str, list[tuple[str, list[str]]]]] = []

    for stmt in mir.entry_point:
        name = str(stmt.get("name", "")) if stmt.get("op") == "call" else ""
        if not name.startswith("sim."):
            continue
        args = stmt.get("args", [])

        if name == "sim.entity" and len(args) >= 2:
            entity_name = _c_text(str(args[0].get("value", "entity")))
            comps = [a for a in args[1].get("items", []) if _component_name(a, constructs, types)]
            var = f"e_{entity_idx}"
            entity_idx += 1
            specs = []
            for comp in comps:
                cname = _component_name(comp, constructs, types)
                if not cname:
                    continue
                values = _component_field_values(comp, constructs, custom_types)
                specs.append((cname, values))
            entity_specs.append((entity_name, specs))

        elif name == "sim.system" and len(args) >= 3:
            sys_name = _c_text(str(args[0].get("value", "system")))
            fn_name = str(args[1].get("name", "")) if args[1].get("op") == "ident" else ""
            if fn_name:
                fallback_systems.append(fn_name)
            lines.append("")
            lines.append("  // sim.system: register system to run every tick")
            lines.append("#ifdef OMNI_HAVE_FLECS")
            lines.append(f"  ECS_SYSTEM(world, {fn_name}, EcsOnUpdate, 0);")
            lines.append("#else")
            lines.append(f"  (void){sys_name};")
            lines.append("#endif")
            lines.append("")

    for entity_name, specs in entity_specs:
        lines.append("")
        lines.append("  // sim.entity: components -> Flecs")
        lines.append("#ifdef OMNI_HAVE_FLECS")
        var = f"e_entity_{len(entity_specs)}"
        lines.append(f"  ecs_entity_t {var} = ecs_new(world);")
        lines.append(f"  ecs_set_name(world, {var}, {entity_name});")
        for cname, _values in specs:
            lines.append(f"  ecs_set(world, {var}, {cname}, {{{', '.join(_values)}}});")
        lines.append(f"  (void){var};")
        lines.append("#else")
        for cname, _ in specs:
            lines.append(f"  (void){cname};")
        lines.append("#endif")
        lines.append("")

    if components:
        lines.append("  // Flecs component registration")
        lines.append("#ifdef OMNI_HAVE_FLECS")
        for cname in components:
            lines.append(f"  ECS_COMPONENT_DECLARE({cname});")
        for cname in components:
            lines.append(f"  ECS_COMPONENT_DEFINE(world, {cname});")
        lines.append("#endif")
        lines.append("")

    if fallback_systems:
        lines.append("  // deterministic fallback: run registered systems each tick")
        lines.append("#ifndef OMNI_HAVE_FLECS")
        for fn_name in fallback_systems:
            lines.append(f"  {fn_name}();")
        lines.append("#endif")
        lines.append("")

    return lines


def emit_c(mir: Any) -> str:
    """Emit C99 code with Flecs adapter from OMNI MIR."""
    lines: list[str] = [
        "// Generated by OmniScript C Emitter (v3.1)",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "#include <string.h>",
        "#include <stdbool.h>",
        "#include <stdarg.h>",
        '#include "flecs.h"',
        "",
        "typedef struct {",
        "  void** items;",
        "  int count;",
        "} OmniList;",
        "",
        "static OmniList omni_make_list(void* items[], int count) {",
        "  OmniList l;",
        "  l.items = items;",
        "  l.count = count;",
        "  return l;",
        "}",
        "",
        "static char omni_format_buf[4096];",
        "static char* omni_format(const char* fmt, ...) {",
        "  va_list args;",
        "  va_start(args, fmt);",
        "  vsnprintf(omni_format_buf, sizeof(omni_format_buf), fmt, args);",
        "  va_end(args);",
        "  return omni_format_buf;",
        "}",
        "",
        "static char omni_join_buf[4096];",
        "static const char* omni_join(OmniList list, const char* sep) {",
        "  omni_join_buf[0] = '\\0';",
        "  size_t off = 0;",
        "  const char** items = (const char**)list.items;",
        "  for (int i = 0; i < list.count; i++) {",
        "    if (i > 0) {",
        "      size_t sl = strlen(sep);",
"      if (off + sl < sizeof(omni_join_buf)) {",
        "        memcpy(omni_join_buf + off, sep, sl); off += sl;",
        "      }",
        "    }",
        '    const char* s = items[i] ? items[i] : "";',
        "    size_t sl = strlen(s);",
        "    if (off + sl < sizeof(omni_join_buf)) {",
        "      memcpy(omni_join_buf + off, s, sl); off += sl;",
        "    }",
        "  }",
        "  omni_join_buf[off] = '\\0';",
        "  return omni_join_buf;",
        "}",
        "",
    ]

    custom_types = getattr(mir, "types", {})
    lines.extend(_emit_c_type_decls(custom_types))

    for fn in mir.functions.values():
        params = ", ".join(f"{_c_type(p.type)} {p.name}" for p in fn.params) or "void"
        ret = _c_type(fn.return_type)
        lines.append(f"{ret} {fn.name}({params});")
    if mir.functions:
        lines.append("")

    for fn in mir.functions.values():
        params = ", ".join(f"{_c_type(p.type)} {p.name}" for p in fn.params) or "void"
        ret = _c_type(fn.return_type)
        lines.append(f"{ret} {fn.name}({params}) {{")
        declared = {p.name for p in fn.params}
        types: dict[str, str] = {p.name: p.type for p in fn.params}
        for stmt in fn.body:
            lines.append(_c_stmt(stmt, declared, custom_types, 2, types))
        lines.append("}")
        lines.append("")

    lines.append("int main(int argc, char** argv) {")
    lines.append("  (void)argc; (void)argv;")
    lines.append("  ecs_world_t* world = ecs_init();")
    lines.append("  (void)world;")
    lines.append("")

    declared_main: set[str] = set()
    main_types: dict[str, str] = {}
    constructs: dict[str, dict[str, Any]] = {}
    for stmt in mir.entry_point:
        if stmt.get("op") == "assign" and stmt["expr"].get("op") == "struct":
            constructs[stmt["name"]] = stmt["expr"]

    sim_system_lines = _emit_sim_lowering(mir, custom_types, constructs, main_types)
    for stmt in mir.entry_point:
        if stmt.get("op") == "call" and str(stmt.get("name", "")).startswith("sim."):
            continue
        lines.append(_c_stmt(stmt, declared_main, custom_types, 2, main_types))

    lines.extend(sim_system_lines)

    lines.append("")
    lines.append("  ecs_progress(world, 0);")
    lines.append("  ecs_fini(world);")
    lines.append("  return 0;")
    lines.append("}")

    return "\n".join(lines)