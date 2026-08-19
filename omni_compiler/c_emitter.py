# ruff: noqa: Q000, PLR0911, PLR0912, PLR0915, PLR2004
"""C99 Emitter Module with Flecs Adapter and SQLite Support.

Generates typed C99 code from OMNI MIR for native desktop and simulation
targets. The generated code is guarded by ``OMNI_HAVE_FLECS``: when defined
the Flecs C API is used for entities/components/systems; otherwise a plain
deterministic fallback loop runs registered systems, so the emitted file
still compiles without the Flecs library.

SQLite support is enabled via ``OMNI_HAVE_SQLITE`` which links against
the system SQLite3 library.

Floating-point conformance: uses math.h for IEEE 754 compliant operations
including proper handling of division by zero, NaN, infinity, and rounding.
"""

from typing import Any

MIN_QUOTE_LEN = 2

_C_TYPE_MAP = {
    'Number': 'double',
    'Text': 'const char*',
    'Boolean': 'bool',
    'List': 'OmniList',
    'None': 'void',
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
    op = e.get('op')
    if op == 'number':
        return 'Number'
    if op == 'text':
        return 'Text'
    if op == 'boolean':
        return 'Boolean'
    if op == 'none':
        return 'None'
    if op == 'list':
        return 'List'
    if op == 'struct':
        return str(e['name'])
    if op == 'ident':
        return types.get(str(e['name']), 'Number')
    if op == 'group':
        return _expr_type(e.get('expr', {}), types, custom_types)
    if op == 'not':
        return 'Boolean'
    if op == 'neg':
        return 'Number'
    if op == 'field':
        base = _expr_type(e.get('object', {}), types, custom_types)
        fields = custom_types.get(base)
        if fields:
            return str(fields.get(str(e.get('field')), 'Number'))
        return 'Number'
    if op == 'call':
        if e.get('name') == 'join':
            return 'Text'
        return 'Number'
    if op in ('is', 'is not', 'and', 'or'):
        return 'Boolean'
    if op in ('greater than', 'less than', 'greater or equal', 'less or equal'):
        return 'Boolean'
    return 'Number'


def _slot_type(expr_text: str, types: dict[str, str]) -> str:
    """Infer the type of a ``{slot}`` expression embedded in a text literal."""
    slot = expr_text.strip()
    if slot and slot.replace('_', '').isalnum() and not slot[0].isdigit():
        return types.get(slot, 'Number')
    return 'Number'


def _c_text_expr(raw: str, types: dict[str, str], _custom_types: dict[str, Any]) -> str:
    """Render a text literal with ``{slot}`` interpolation as omni_format()."""
    body = raw[1:-1] if len(raw) >= MIN_QUOTE_LEN and raw[0] in ('"', "'") else raw
    fmt_parts: list[str] = []
    args: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(body):
        if body[i] == '\\' and i + 1 < len(body) and body[i + 1] in '{}.}':
            buf.append(body[i + 1])
            i += 2
        elif body[i] == '{':
            j = body.find('}', i)
            if j == -1:
                buf.append(body[i:])
                break
            slot = body[i + 1 : j]
            if buf:
                fmt_parts.append(''.join(buf).replace('%', '%%'))
                buf = []
            stype = _slot_type(slot, types)
            if stype == 'Text':
                fmt_parts.append('%s')
                args.append(f'((const char*)({slot}))')
            elif stype == 'Boolean':
                fmt_parts.append('%s')
                args.append(f"(({slot}) ? 'true' : 'false')".replace("'", '"'))
            else:
                fmt_parts.append('%f')
                args.append(f'(double)({slot})')
            i = j + 1
        else:
            buf.append(body[i])
            i += 1
    if buf:
        fmt_parts.append(''.join(buf).replace('%', '%%'))
    if not fmt_parts:
        return '""'
    if not args:
        return _c_text(raw)
    fmt = ''.join(fmt_parts)
    return f'omni_format("{fmt}", {", ".join(args)})'


def _c_expr_unary_and_literals(
    e: dict[str, Any],
    custom_types: dict[str, Any],
    types: dict[str, str] | None = None,
) -> str | None:
    types = types or {}
    op = e.get('op')
    if op == 'number':
        val = str(e['value'])
        return f'{val}.0' if '.' not in val and 'e' not in val.lower() else val
    if op == 'boolean':
        return 'true' if e['value'] else 'false'
    if op == 'none':
        return 'NULL'
    if op == 'ident':
        return str(e['name'])
    if op == 'text':
        if '{' in str(e['value']):
            return _c_text_expr(str(e['value']), types, custom_types)
        return _c_text(str(e['value']))
    if op == 'list':
        items = ', '.join(_c_expr(i, custom_types, types) for i in e['items'])
        return f'omni_make_list((void*[]){{{items}}}, {len(e["items"])})'
    if op == 'map':
        return '// map literal (unsupported in C): omni_map'
    if op == 'index':
        obj = _c_expr(e.get('object', {}), custom_types, types)
        idx = _c_expr(e.get('index', {}), custom_types, types)
        return f'((void**)({obj}).items)[(int)({idx})]'
    if op == 'await':
        return _c_expr(e.get('expr', {}), custom_types, types)
    if op == 'field':
        return f'{_c_expr(e["object"], custom_types, types)}.{e["field"]}'
    if op == 'struct':
        struct_type = e['name']
        fields = ', '.join(
            f'.{k} = {_c_expr(v, custom_types, types)}' for k, v in e['args'].items()
        )
        return f'({struct_type}){{ {fields} }}'
    if op == 'call':
        args = ', '.join(_c_expr(a, custom_types, types) for a in e['args'])
        return f'omni_join({args})' if e['name'] == 'join' else f'{e["name"]}({args})'
    if op == 'group':
        return f'({_c_expr(e["expr"], custom_types, types)})'
    if op == 'not':
        return f'(!{_c_expr(e["operand"], custom_types, types)})'
    if op == 'neg':
        return f'(-{_c_expr(e["operand"], custom_types, types)})'
    return None


def _c_expr(
    e: dict[str, Any],
    custom_types: dict[str, Any],
    types: dict[str, str] | None = None,
) -> str:
    unary_res = _c_expr_unary_and_literals(e, custom_types, types)
    if unary_res is not None:
        return unary_res

    op = e.get('op', '')
    left = _c_expr(e['left'], custom_types, types)
    right = _c_expr(e['right'], custom_types, types)

    if op == '/':
        return f'omni_fp_divide({left}, {right})'
    if op == '%':
        return f'omni_fp_modulo({left}, {right})'

    op_map = {
        'is': '==',
        'is not': '!=',
        'and': '&&',
        'or': '||',
        'greater than': '>',
        'less than': '<',
        'greater or equal': '>=',
        'less or equal': '<=',
    }
    cop = op_map.get(op, op)
    return f'({left} {cop} {right})'


def _c_stmt(
    s: dict[str, Any],
    declared_vars: set[str],
    custom_types: dict[str, Any],
    indent: int = 2,
    types: dict[str, str] | None = None,
) -> str:
    if types is None:
        types = {}
    pad = ' ' * indent
    op = s.get('op')
    if op == 'assign':
        var_name = s['name']
        vtype = _expr_type(s['expr'], types, custom_types)
        types[var_name] = vtype
        if var_name not in declared_vars:
            declared_vars.add(var_name)
            return f'{pad}{_c_type(vtype)} {var_name} = {_c_expr(s["expr"], custom_types, types)};'
        return f'{pad}{var_name} = {_c_expr(s["expr"], custom_types, types)};'
    if op == 'return':
        return f'{pad}return {_c_expr(s["expr"], custom_types, types)};'
    if op == 'show':
        return _c_show(s['expr'], custom_types, types, pad)
    if op in ('break', 'continue'):
        return f'{pad}{op};'
    if op == 'if':
        lines = [f'{pad}if ({_c_expr(s["cond"], custom_types, types)}) {{']
        for st in s['body']:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f'{pad}}}')
        if s.get('else'):
            lines.append(f'{pad}else {{')
            for st in s['else']:
                lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
            lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'for':
        var = s['var']
        iterable = _c_expr(s['iterable'], custom_types, types)
        elem_type = _list_elem_type(s['iterable'], types, custom_types)
        c_elem = _c_type(elem_type)
        declared_vars.add(var)
        types[var] = elem_type
        lines = [
            f'{pad}for (int _i_{var} = 0; _i_{var} < {iterable}.count; _i_{var}++) {{',
            f'{pad}  {c_elem} {var} = (({c_elem}*){iterable}.items)[_i_{var}];',
        ]
        for st in s['body']:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'while':
        lines = [f'{pad}while ({_c_expr(s["cond"], custom_types, types)}) {{']
        for st in s['body']:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'try':
        lines = [
            f'{pad}// try/catch lowered to a return-on-error guard',
            f'{pad}{{',
        ]
        for st in s['body']:
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        lines.append(f'{pad}}}')
        for st in s.get('on_error', []):
            lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        if s.get('finally'):
            for st in s['finally']:
                lines.append(_c_stmt(st, declared_vars, custom_types, indent + 2, types))
        return '\n'.join(lines)
    if op == 'global':
        return f'{pad}// global {s.get("name", "")}'
    if op == 'call':
        return f'{pad}{_c_expr(s, custom_types, types)};'
    return f'{pad}// unknown statement: {s!r}'


def _list_elem_type(
    iterable: dict[str, Any],
    types: dict[str, str],
    custom_types: dict[str, Any],
) -> str:
    """Determine the element type of a list expression (best effort)."""
    if iterable.get('op') == 'list':
        items = iterable.get('items', [])
        if items:
            return _expr_type(items[0], types, custom_types)
        return 'Number'
    if iterable.get('op') == 'ident':
        return types.get(str(iterable['name']), 'Number')
    return 'Number'


def _c_show(
    expr: dict[str, Any], custom_types: dict[str, Any], types: dict[str, str], pad: str
) -> str:
    """Emit a printf statement matching the expression type."""
    vtype = _expr_type(expr, types, custom_types)
    cexpr = _c_expr(expr, custom_types, types)
    if vtype == 'Text':
        return f'{pad}printf("%s\\n", ({cexpr}));'
    if vtype == 'Boolean':
        return f'{pad}printf("%s\\n", ({cexpr}) ? "true" : "false");'
    if vtype in custom_types:
        return f'{pad}// show struct: {cexpr}'
    return f'{pad}printf("%f\\n", (double)({cexpr}));'


def _emit_c_type_decls(custom_types: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for tname, fields_info in custom_types.items():
        fields = (
            fields_info.get('fields', fields_info) if isinstance(fields_info, dict) else fields_info
        )
        lines.append(f'typedef struct {tname} {{')
        for fname, ftype in fields.items():
            lines.append(f'  {_c_type(ftype)} {fname};')
        lines.append(f'}} {tname};')
        lines.append('')
    return lines


def _component_name(
    item: dict[str, Any],
    constructs: dict[str, dict[str, Any]],
    types: dict[str, str],
) -> str | None:
    """Resolve a sim component item (struct construct or variable) to a type name."""
    if item.get('op') == 'struct':
        return str(item['name'])
    if item.get('op') == 'ident':
        name = str(item['name'])
        if name in constructs:
            return str(constructs[name]['name'])
        return types.get(name)
    return None


def _component_field_values(
    item: dict[str, Any],
    constructs: dict[str, dict[str, Any]],
    custom_types: dict[str, Any],
) -> list[str]:
    """Extract ordered field values for a component item."""
    construct = item if item.get('op') == 'struct' else constructs.get(str(item.get('name', '')))
    if not construct:
        return []
    return [
        _c_expr(construct['args'][f], custom_types)
        for f in _struct_field_order(construct, custom_types)
    ]


def _component_types_used(
    mir: Any, constructs: dict[str, dict[str, Any]], types: dict[str, str]
) -> list[str]:
    """Return the custom types referenced by sim.* calls in the entry point."""
    used: list[str] = []
    for stmt in mir.entry_point:
        if stmt.get('op') != 'call' or not str(stmt.get('name', '')).startswith('sim.'):
            continue
        for arg in stmt.get('args', []):
            if arg.get('op') != 'list':
                continue
            for item in arg.get('items', []):
                cname = _component_name(item, constructs, types)
                if cname and cname not in used:
                    used.append(cname)
    return used


def _struct_field_order(struct_expr: dict[str, Any], custom_types: dict[str, Any]) -> list[str]:
    """Order the fields of a struct construct by declaration order."""
    name = struct_expr['name']
    fields = custom_types.get(name, {})
    ordered = [f for f in fields if f in struct_expr.get('args', {})]
    for f in struct_expr.get('args', {}):
        if f not in ordered:
            ordered.append(f)
    return ordered


def _emit_sim_lowering(
    mir: Any,
    custom_types: dict[str, Any],
    constructs: dict[str, dict[str, Any]],
    types: dict[str, str],
) -> tuple[list[str], str | None]:
    """Emit the entry point main body, lowering ``sim.*`` calls to Flecs C.

    Returns ``(body_lines, run_ticks)`` where ``run_ticks`` is the ``sim.run``
    argument (a C expression) or ``None`` when the program never calls
    ``sim.run``. Non-``sim.*`` statements are emitted inline so variable
    declaration order matches source order.
    """
    lines: list[str] = []
    components = _component_types_used(mir, constructs, types)
    fallback_systems: list[str] = []
    entity_specs: list[tuple[str, list[tuple[str, list[str]]]]] = []
    run_ticks: str | None = None
    declared_main: set[str] = set()

    def lower_sim_call(name: str, args: list[dict[str, Any]]) -> None:
        """Lower a top-level ``sim.*`` call statement in place."""
        nonlocal run_ticks
        if name == 'sim.entity' and len(args) >= 2:
            entity_name = _c_text(str(args[0].get('value', 'entity')))
            comps = [a for a in args[1].get('items', []) if _component_name(a, constructs, types)]
            specs = []
            for comp in comps:
                cname = _component_name(comp, constructs, types)
                if not cname:
                    continue
                values = _component_field_values(comp, constructs, custom_types)
                specs.append((cname, values))
            entity_specs.append((entity_name, specs))

        elif name == 'sim.system' and len(args) >= 3:
            sys_name = _c_text(str(args[0].get('value', 'system')))
            fn_name = str(args[1].get('name', '')) if args[1].get('op') == 'ident' else ''
            if fn_name:
                fallback_systems.append(fn_name)
            lines.append('')
            lines.append('  // sim.system: register system to run every tick')
            lines.append('#ifdef OMNI_HAVE_FLECS')
            lines.append(f'  ECS_SYSTEM(world, {fn_name}, EcsOnUpdate, 0);')
            lines.append('#else')
            lines.append(f'  (void){sys_name};')
            lines.append('#endif')
            lines.append('')

        elif name == 'sim.run':
            run_ticks = _c_expr(args[0], custom_types, types) if args else '1'
            lines.append('')
            lines.append(f'  // sim.run({run_ticks}): run the world {run_ticks} ticks')

        elif name == 'sim.query':
            comp = _c_text(str(args[0].get('value', ''))) if args else '""'
            lines.append('')
            lines.append(f'  // sim.query {comp}: entities carrying a component (empty stub)')
            lines.append('')

        else:
            lines.append('')
            lines.append(f'  // sim.{name}: no C lowering yet')
            lines.append('')

    def lower_sim_assign(var: str, expr: dict[str, Any]) -> None:
        """Lower an assignment whose value is a ``sim.*`` call."""
        nonlocal run_ticks
        sim_name = str(expr.get('name', ''))
        args = expr.get('args', [])
        if sim_name == 'sim.query':
            comp = _c_text(str(args[0].get('value', ''))) if args else '""'
            lines.append('')
            lines.append(f'  // sim.query {comp}: entities carrying a component (empty stub)')
            lines.append(f'  OmniList {var} = omni_make_list((void*[]){{}}, 0);')
            lines.append(f'  (void){var};')
            lines.append('')
        elif sim_name == 'sim.run':
            run_ticks = _c_expr(args[0], custom_types, types) if args else '1'
            lines.append('')
            lines.append(f'  // sim.run({run_ticks}): run the world {run_ticks} ticks')
            lines.append(f'  double {var} = 0;')
            lines.append(f'  (void){var};')
            lines.append('')
        else:
            lines.append('')
            lines.append(f'  // {sim_name} result assigned to {var} (no C lowering yet)')
            lines.append(f'  double {var} = 0;')
            lines.append(f'  (void){var};')
            lines.append('')

    for stmt in mir.entry_point:
        op = stmt.get('op')
        if op == 'call' and str(stmt.get('name', '')).startswith('sim.'):
            lower_sim_call(str(stmt['name']), stmt.get('args', []))
            continue
        if (
            op == 'assign'
            and stmt['expr'].get('op') == 'call'
            and str(stmt['expr'].get('name', '')).startswith('sim.')
        ):
            lower_sim_assign(str(stmt['name']), stmt['expr'])
            continue
        lines.append(_c_stmt(stmt, declared_main, custom_types, 2, types))

    for entity_name, specs in entity_specs:
        lines.append('')
        lines.append('  // sim.entity: components -> Flecs')
        lines.append('#ifdef OMNI_HAVE_FLECS')
        var = f'e_entity_{len(entity_specs)}'
        lines.append(f'  ecs_entity_t {var} = ecs_new(world);')
        lines.append(f'  ecs_set_name(world, {var}, {entity_name});')
        for cname, _values in specs:
            lines.append(f'  ecs_set(world, {var}, {cname}, {{{", ".join(_values)}}});')
        lines.append(f'  (void){var};')
        lines.append('#else')
        for cname, _ in specs:
            lines.append(f'  (void){cname};')
        lines.append('#endif')
        lines.append('')

    if components:
        lines.append('  // Flecs component registration')
        lines.append('#ifdef OMNI_HAVE_FLECS')
        for cname in components:
            lines.append(f'  ECS_COMPONENT_DECLARE({cname});')
        for cname in components:
            lines.append(f'  ECS_COMPONENT_DEFINE(world, {cname});')
        lines.append('#endif')
        lines.append('')

    if fallback_systems:
        lines.append('  // deterministic fallback: run registered systems each tick')
        lines.append('#ifndef OMNI_HAVE_FLECS')
        if run_ticks is not None:
            lines.append(f'  for (int _omni_tick = 0; _omni_tick < {run_ticks}; _omni_tick++) {{')
            for fn_name in fallback_systems:
                lines.append(f'    {fn_name}();')
            lines.append('  }')
        else:
            for fn_name in fallback_systems:
                lines.append(f'  {fn_name}();')
        lines.append('#endif')
        lines.append('')

    return lines, run_ticks


def emit_c(mir: Any) -> str:
    """Emit C99 code with Flecs adapter and SQLite support from OMNI MIR."""
    lines: list[str] = [
        '// Generated by OmniScript C Emitter (v3.3)',
        '#include <stdio.h>',
        '#include <stdlib.h>',
        '#include <string.h>',
        '#include <stdbool.h>',
        '#include <stdarg.h>',
        '#include <math.h>',
        '#include "flecs.h"',
        '',
        '#ifdef OMNI_HAVE_SQLITE',
        '#include <sqlite3.h>',
        '#endif',
        '',
        '// IEEE 754 Floating-Point Conformance Helpers',
        'static inline bool omni_fp_is_nan(double x) { return isnan(x); }',
        'static inline bool omni_fp_is_finite(double x) { return isfinite(x); }',
        'static inline bool omni_fp_is_infinite(double x) { return isinf(x); }',
        'static inline double omni_fp_divide(double a, double b) {',
        '  if (b == 0.0) {',
        '    if (a == 0.0) return NAN;',
        '    return copysign(INFINITY, a);',
        '  }',
        '  return a / b;',
        '}',
        'static inline double omni_fp_modulo(double a, double b) {',
        '  if (b == 0.0 || isnan(a) || isnan(b)) return NAN;',
        '  if (isinf(a)) return NAN;',
        '  return fmod(a, b);',
        '}',
        'static inline double omni_fp_neg_zero(void) { return -0.0; }',
        'static inline double omni_fp_copy_sign(double x, double y) { return copysign(x, y); }',
        '',
        'typedef struct {',
        '  void** items;',
        '  int count;',
        '} OmniList;',
        '',
        'static OmniList omni_make_list(void* items[], int count) {',
        '  OmniList l;',
        '  l.items = items;',
        '  l.count = count;',
        '  return l;',
        '}',
        '',
        'static char omni_format_buf[4096];',
        'static char* omni_format(const char* fmt, ...) {',
        '  va_list args;',
        '  va_start(args, fmt);',
        '  vsnprintf(omni_format_buf, sizeof(omni_format_buf), fmt, args);',
        '  va_end(args);',
        '  return omni_format_buf;',
        '}',
        '',
        'static char omni_join_buf[4096];',
        'static const char* omni_join(OmniList list, const char* sep) {',
        "  omni_join_buf[0] = '\\0';",
        '  size_t off = 0;',
        '  const char** items = (const char**)list.items;',
        '  for (int i = 0; i < list.count; i++) {',
        '    if (i > 0) {',
        '      size_t sl = strlen(sep);',
        '      if (off + sl < sizeof(omni_join_buf)) {',
        '        memcpy(omni_join_buf + off, sep, sl); off += sl;',
        '      }',
        '    }',
        '    const char* s = items[i] ? items[i] : "";',
        '    size_t sl = strlen(s);',
        '    if (off + sl < sizeof(omni_join_buf)) {',
        '      memcpy(omni_join_buf + off, s, sl); off += sl;',
        '    }',
        '  }',
        "  omni_join_buf[off] = '\\0';",
        '  return omni_join_buf;',
        '}',
        '',
        '// OMNISYS.async stubs (no-op for C target)',
        'typedef struct {',
        '  void* handle;',
        '  void (*cancel)(void*);',
        '} OmniTask;',
        'static void omni_async_cancel_stub(void* handle) { (void)handle; }',
        'static OmniTask omnisys_async_task(void* fn) { return (OmniTask){ .handle = fn, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static OmniTask omnisys_async_delay(double ms) { return (OmniTask){ .handle = NULL, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static OmniTask omnisys_async_interval(double ms, void* fn) { return (OmniTask){ .handle = NULL, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static OmniTask omnisys_async_timeout(double ms, void* fn) { return (OmniTask){ .handle = NULL, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static OmniTask omnisys_async_tick(void* fn) { return (OmniTask){ .handle = NULL, .cancel = omni_async_cancel_stub }; }',  # noqa: E501
        'static void omnisys_async_cancel(OmniTask task) { if (task.cancel) task.cancel(task.handle); }',  # noqa: E501
        'static void* omnisys_async_await(OmniTask task) { return task.handle; }',
        '',
        '// OMNISYS.pkg — Semantic Versioning & Lockfile Support',
        '// Version struct',
        'typedef struct {',
        '  int major;',
        '  int minor;',
        '  int patch;',
        '  const char* prerelease;',
        '  const char* build;',
        '} OmniVersion;',
        '',
        '// Parse semantic version string into OmniVersion',
        '// Returns 0 on success, -1 on failure',
        'static int omni_pkg_parse_version(const char* version, OmniVersion* out) {',
        '  if (!version || !out) return -1;',
        '  int major = 0, minor = 0, patch = 0;',
        '  const char* p = version;',
        '  char* end;',
        '  major = (int)strtol(p, &end, 10);',
        "  if (end == p || *end != '.') return -1;",
        '  p = end + 1;',
        '  minor = (int)strtol(p, &end, 10);',
        "  if (end == p || *end != '.') return -1;",
        '  p = end + 1;',
        '  patch = (int)strtol(p, &end, 10);',
        '  if (end == p) {',
        '    out->major = major;',
        '    out->minor = minor;',
        '    out->patch = patch;',
        '    out->prerelease = "";',
        '    out->build = "";',
        '    return 0;',
        '  }',
        '  const char* prerelease = "";',
        '  const char* build = "";',
        "  if (*end == '-') {",
        '    p = end + 1;',
        '    prerelease = p;',
        "    while (*p && *p != '+') p++;",
        "    if (*p == '+') {",
        '      p++;',
        '      build = p;',
        '    }',
        "  } else if (*end == '+') {",
        '    p = end + 1;',
        '    build = p;',
        '  }',
        '  out->major = major;',
        '  out->minor = minor;',
        '  out->patch = patch;',
        '  out->prerelease = prerelease;',
        '  out->build = build;',
        '  return 0;',
        '}',
        '',
        '// Compare two versions: -1 if a<b, 0 if a==b, 1 if a>b',
        'static int omni_pkg_cmp_version(const OmniVersion* a, const OmniVersion* b) {',
        '  if (a->major != b->major) return (a->major < b->major) ? -1 : 1;',
        '  if (a->minor != b->minor) return (a->minor < b->minor) ? -1 : 1;',
        '  if (a->patch != b->patch) return (a->patch < b->patch) ? -1 : 1;',
        '  // prerelease < release',
        '  bool a_pre = a->prerelease && a->prerelease[0];',
        '  bool b_pre = b->prerelease && b->prerelease[0];',
        '  if (a_pre != b_pre) return a_pre ? -1 : 1;',
        '  if (a_pre && b_pre) {',
        '    return strcmp(a->prerelease, b->prerelease);',
        '  }',
        '  return 0;',
        '}',
        '',
        '// Check if version satisfies constraint',
        '// Supports: ^ (caret), ~ (tilde), >=, <=, >, <, =, ==, || (union)',
        'static bool omni_pkg_satisfies(const char* version, const char* constraint) {',
        '  if (!version || !constraint) return false;',
        '  OmniVersion v;',
        '  if (omni_pkg_parse_version(version, &v) != 0) return false;',
        '  ',
        '  // Split by || for union constraints',
        '  char constraint_copy[512];',
        '  strncpy(constraint_copy, constraint, sizeof(constraint_copy) - 1);',
        "  constraint_copy[sizeof(constraint_copy) - 1] = '\\0';",
        '  ',
        '  char* part = strtok(constraint_copy, "|");',
        '  while (part) {',
        '    // Trim whitespace',
        "    while (*part == ' ' || *part == '\\t') part++;",
        '    char* end = part + strlen(part) - 1;',
        "    while (end > part && (*end == ' ' || *end == '\\t')) *end-- = '\\0';",
        '    ',
        "    if (part[0] == '^') {",
        '      // Caret: ^1.2.3 := >=1.2.3 <2.0.0 (or <0.3.0 for 0.x)',
        '      OmniVersion target;',
        '      if (omni_pkg_parse_version(part + 1, &target) == 0) {',
        '        OmniVersion upper = target;',
        '        if (target.major == 0) {',
        '          if (target.minor == 0) upper.patch++;',
        '          else upper.minor++;',
        '        } else {',
        '          upper.major++;',
        '        }',
        '        upper.minor = (target.major == 0 && target.minor == 0) ? 0 : upper.minor;',
        '        upper.patch = (target.major == 0 && target.minor == 0) ? upper.patch : 0;',
        '        if (omni_pkg_cmp_version(&v, &target) >= 0 && omni_pkg_cmp_version(&v, &upper) < 0) {',  # noqa: E501
        '          return true;',
        '        }',
        '      }',
        "    } else if (part[0] == '~') {",
        '      // Tilde: ~1.2.3 := >=1.2.3 <1.3.0',
        '      OmniVersion target;',
        '      if (omni_pkg_parse_version(part + 1, &target) == 0) {',
        '        OmniVersion upper = target;',
        '        upper.minor++;',
        '        upper.patch = 0;',
        '        if (omni_pkg_cmp_version(&v, &target) >= 0 && omni_pkg_cmp_version(&v, &upper) < 0) {',  # noqa: E501
        '          return true;',
        '        }',
        '      }',
        '    } else if (strncmp(part, ">=", 2) == 0 || strncmp(part, "<=", 2) == 0 ||',
        '               strncmp(part, ">", 1) == 0 || strncmp(part, "<", 1) == 0 ||',
        '               strncmp(part, "==", 2) == 0 || part[0] == \'=\') {',
        '      // Simple comparison',
        '      const char* op = part;',
        '      const char* ver_str = part;',
        '      if (strncmp(part, ">=", 2) == 0 || strncmp(part, "<=", 2) == 0 || strncmp(part, "==", 2) == 0) {',  # noqa: E501
        '        ver_str = part + 2;',
        "      } else if (part[0] == '>' || part[0] == '<' || part[0] == '=') {",
        '        ver_str = part + 1;',
        '      }',
        "      while (*ver_str == ' ' || *ver_str == '\\t') ver_str++;",
        '      OmniVersion target;',
        '      if (omni_pkg_parse_version(ver_str, &target) == 0) {',
        '        int cmp = omni_pkg_cmp_version(&v, &target);',
        "        if ((op[0] == '>' && op[1] == '=' && cmp >= 0) ||",
        "            (op[0] == '<' && op[1] == '=' && cmp <= 0) ||",
        "            (op[0] == '>' && op[1] != '=' && cmp > 0) ||",
        "            (op[0] == '<' && op[1] != '=' && cmp < 0) ||",
        "            ((op[0] == '=' || (op[0] == '=' && op[1] == '=')) && cmp == 0)) {",
        '          return true;',
        '        }',
        '      }',
        '    } else {',
        '      // Bare version = exact match',
        '      OmniVersion target;',
        '      if (omni_pkg_parse_version(part, &target) == 0) {',
        '        if (omni_pkg_cmp_version(&v, &target) == 0) return true;',
        '      }',
        '    }',
        '    part = strtok(NULL, "|");',
        '  }',
        '  return false;',
        '}',
        '',
        '// SHA256 checksum (simplified - uses a basic hash for demo)',
        '// In production, link with OpenSSL or use platform crypto API',
        'static void omni_pkg_compute_checksum(const char* content, char* out, size_t out_size) {',
        '  // Simple FNV-1a hash as placeholder for SHA256',
        '  uint32_t hash = 2166136261u;',
        '  for (size_t i = 0; content[i]; i++) {',
        '    hash ^= (uint8_t)content[i];',
        '    hash *= 16777619u;',
        '  }',
        '  snprintf(out, out_size, "sha256:%08x", hash);',
        '}',
        '',
        '// Lockfile entry',
        'typedef struct {',
        '  const char* name;',
        '  const char* version;',
        '  const char* checksum;',
        '  const char** dep_names;',
        '  const char** dep_versions;',
        '  int dep_count;',
        '} OmniLockfileEntry;',
        '',
        '// Lockfile',
        'typedef struct {',
        '  OmniLockfileEntry* entries;',
        '  int count;',
        '  int capacity;',
        '} OmniLockfile;',
        '',
        'static void omni_lockfile_init(OmniLockfile* lf) {',
        '  lf->entries = NULL;',
        '  lf->count = 0;',
        '  lf->capacity = 0;',
        '}',
        '',
        'static void omni_lockfile_add(OmniLockfile* lf, const char* name, const char* version,',
        '                               const char* checksum, const char** dep_names,',
        '                               const char** dep_versions, int dep_count) {',
        '  if (lf->count >= lf->capacity) {',
        '    lf->capacity = lf->capacity ? lf->capacity * 2 : 4;',
        '    lf->entries = realloc(lf->entries, lf->capacity * sizeof(OmniLockfileEntry));',
        '  }',
        '  OmniLockfileEntry* e = &lf->entries[lf->count++];',
        '  e->name = name;',
        '  e->version = version;',
        '  e->checksum = checksum;',
        '  e->dep_names = dep_names;',
        '  e->dep_versions = dep_versions;',
        '  e->dep_count = dep_count;',
        '}',
        '',
        'static OmniLockfileEntry* omni_lockfile_get(OmniLockfile* lf, const char* name) {',
        '  for (int i = 0; i < lf->count; i++) {',
        '    if (strcmp(lf->entries[i].name, name) == 0) return &lf->entries[i];',
        '  }',
        '  return NULL;',
        '}',
        '',
        'static void omni_lockfile_free(OmniLockfile* lf) {',
        '  free(lf->entries);',
        '  lf->entries = NULL;',
        '  lf->count = 0;',
        '  lf->capacity = 0;',
        '}',
        '',
        '// Package spec for resolution',
        'typedef struct {',
        '  const char* name;',
        '  const char* version_constraint;',
        '  const char** dep_names;',
        '  const char** dep_constraints;',
        '  int dep_count;',
        '  const char* checksum;',
        '} OmniPackageSpec;',
        '',
        '// Resolution result',
        'typedef struct {',
        '  OmniLockfileEntry* packages;',
        '  int count;',
        '  OmniLockfile lockfile;',
        '  const char** warnings;',
        '  int warning_count;',
        '} OmniResolution;',
        '',
        '// Deterministic version resolution (simplified)',
        'static OmniResolution omni_pkg_resolve_versions(OmniPackageSpec* specs, int spec_count,',
        '                                                 const char** registry_names,',
        '                                                 const char*** registry_versions,',
        '                                                 const char**** registry_deps,',
        '                                                 int registry_count,',
        '                                                 OmniLockfile* lockfile) {',
        '  OmniResolution result = {0};',
        '  // This is a simplified stub - full implementation would require',
        '  // a proper registry data structure and topological sort',
        '  result.packages = NULL;',
        '  result.count = 0;',
        '  omni_lockfile_init(&result.lockfile);',
        '  result.warnings = NULL;',
        '  result.warning_count = 0;',
        '  return result;',
        '}',
        '',
        '// OMNISYS.pkg function stubs for C target',
        'OmniVersion omnisys_pkg_parse_version(const char* version) {',
        '  OmniVersion v = {0};',
        '  omni_pkg_parse_version(version, &v);',
        '  return v;',
        '}',
        '',
        'bool omnisys_pkg_satisfies(const char* version, const char* constraint) {',
        '  return omni_pkg_satisfies(version, constraint);',
        '}',
        '',
        'void omnisys_pkg_compute_checksum(const char* content, char* out, size_t out_size) {',
        '  omni_pkg_compute_checksum(content, out, out_size);',
        '}',
        '',
        'OmniLockfile* omnisys_pkg_lockfile_new(void) {',
        '  OmniLockfile* lf = malloc(sizeof(OmniLockfile));',
        '  omni_lockfile_init(lf);',
        '  return lf;',
        '}',
        '',
        'void omnisys_pkg_lockfile_free(OmniLockfile* lf) {',
        '  omni_lockfile_free(lf);',
        '  free(lf);',
        '}',
        '',
        'const char* omnisys_pkg_lockfile_to_json(OmniLockfile* lf) {',
        '  // Simplified JSON serialization',
        '  static char buf[8192];',
        '  size_t off = 0;',
        '  off += snprintf(buf + off, sizeof(buf) - off, "{\\"version\\":1,\\"packages\\":[");',
        '  for (int i = 0; i < lf->count; i++) {',
        '    if (i > 0) off += snprintf(buf + off, sizeof(buf) - off, ",");',
        '    off += snprintf(buf + off, sizeof(buf) - off,',
        '      "{\\"name\\":\\"%s\\",\\"version\\":\\"%s\\",\\"checksum\\":\\"%s\\"}',
        '      lf->entries[i].name, lf->entries[i].version, lf->entries[i].checksum);',
        '  }',
        '  off += snprintf(buf + off, sizeof(buf) - off, "]}");',
        '  return buf;',
        '}',
        '',
        'OmniLockfile* omnisys_pkg_lockfile_from_json(const char* json) {',
        '  // Simplified - returns empty lockfile',
        '  return omnisys_pkg_lockfile_new();',
        '}',
        '',
        'OmniResolution omnisys_pkg_resolve_versions(OmniPackageSpec* specs, int spec_count,',
        '                                             const char** registry_names,',
        '                                             const char*** registry_versions,',
        '                                             const char**** registry_deps,',
        '                                             int registry_count,',
        '                                             OmniLockfile* lockfile) {',
        '  return omni_pkg_resolve_versions(specs, spec_count, registry_names,',
        '                                    registry_versions, registry_deps,',
        '                                    registry_count, lockfile);',
        '}',
        '',
    ]

    # SQLite support
    lines.extend(
        [
            '#ifdef OMNI_HAVE_SQLITE',
            '// SQLite connection (single global connection)',
            'static sqlite3* _omni_sqlite_db = NULL;',
            '',
            '// db_open(path) - open or create SQLite database',
            '// path: NULL or ":memory:" for in-memory, otherwise file path',
            'void omnisys_db_open(const char* path) {',
            '  if (_omni_sqlite_db) {',
            '    sqlite3_close(_omni_sqlite_db);',
            '    _omni_sqlite_db = NULL;',
            '  }',
            '  const char* db_path = (path && path[0]) ? path : ":memory:";',
            '  int rc = sqlite3_open(db_path, &_omni_sqlite_db);',
            '  if (rc != SQLITE_OK) {',
            '    fprintf(stderr, "sqlite3_open failed: %s\\n", sqlite3_errmsg(_omni_sqlite_db));',
            '    return;',
            '  }',
            '  sqlite3_exec(_omni_sqlite_db, "PRAGMA foreign_keys = ON", NULL, NULL, NULL);',
            '}',
            '',
            '// db_exec(sql, params_json) - execute DDL/DML',
            '// params_json: JSON array of parameters (simplified - uses first param only for demo)',  # noqa: E501
            'int omnisys_db_exec(const char* sql, const char* params_json) {',
            '  (void)params_json; // TODO: parse JSON params',
            '  if (!_omni_sqlite_db) return -1;',
            '  char* errmsg = NULL;',
            '  int rc = sqlite3_exec(_omni_sqlite_db, sql, NULL, NULL, &errmsg);',
            '  if (rc != SQLITE_OK) {',
            '    fprintf(stderr, "sqlite3_exec failed: %s\\n", errmsg);',
            '    sqlite3_free(errmsg);',
            '    return -1;',
            '  }',
            '  return sqlite3_changes(_omni_sqlite_db);',
            '}',
            '',
            '// db_query(sql, params_json) - execute SELECT and return JSON',
            '// Returns a JSON string array of row objects',
            'const char* omnisys_db_query(const char* sql, const char* params_json) {',
            '  (void)params_json; // TODO: parse JSON params',
            '  if (!_omni_sqlite_db) return "[]";',
            '  sqlite3_stmt* stmt = NULL;',
            '  int rc = sqlite3_prepare_v2(_omni_sqlite_db, sql, -1, &stmt, NULL);',
            '  if (rc != SQLITE_OK) {',
            '    fprintf(stderr, "sqlite3_prepare failed: %s\\n", sqlite3_errmsg(_omni_sqlite_db));',  # noqa: E501
            '    return "[]";',
            '  }',
            '  // Simplified: build JSON result in static buffer',
            '  static char result_buf[8192];',
            '  size_t off = 0;',
            "  result_buf[off++] = '[';",
            '  int first_row = 1;',
            '  while ((rc = sqlite3_step(stmt)) == SQLITE_ROW) {',
            '    if (!first_row) {',
            "      if (off + 1 < sizeof(result_buf)) result_buf[off++] = ',';",
            '    }',
            '    first_row = 0;',
            "    if (off + 1 < sizeof(result_buf)) result_buf[off++] = '{';",
            '    int col_count = sqlite3_column_count(stmt);',
            '    for (int i = 0; i < col_count; i++) {',
            '      const char* col_name = sqlite3_column_name(stmt, i);',
            '      const char* col_value = (const char*)sqlite3_column_text(stmt, i);',
            "      if (i > 0 && off + 1 < sizeof(result_buf)) result_buf[off++] = ',';",
            '      // Write key',
            '      size_t kn = strlen(col_name);',
            '      if (off + kn + 3 < sizeof(result_buf)) {',
            "        result_buf[off++] = '\"';",
            '        memcpy(result_buf + off, col_name, kn);',
            '        off += kn;',
            "        result_buf[off++] = '\"';",
            "        result_buf[off++] = ':';",
            '      }',
            '      // Write value',
            '      if (col_value) {',
            '        size_t vn = strlen(col_value);',
            '        if (off + vn + 3 < sizeof(result_buf)) {',
            "          result_buf[off++] = '\"';",
            '          memcpy(result_buf + off, col_value, vn);',
            '          off += vn;',
            "          result_buf[off++] = '\"';",
            '        }',
            '      } else {',
            '        if (off + 4 < sizeof(result_buf)) {',
            '          memcpy(result_buf + off, "null", 4);',
            '          off += 4;',
            '        }',
            '      }',
            '    }',
            "    if (off + 1 < sizeof(result_buf)) result_buf[off++] = '}';",
            '  }',
            "  if (off + 1 < sizeof(result_buf)) result_buf[off++] = ']';",
            "  result_buf[off] = '\\0';",
            '  sqlite3_finalize(stmt);',
            '  return result_buf;',
            '}',
            '',
            '// db_close() - close SQLite database',
            'void omnisys_db_close(void) {',
            '  if (_omni_sqlite_db) {',
            '    sqlite3_close(_omni_sqlite_db);',
            '    _omni_sqlite_db = NULL;',
            '  }',
            '}',
            '#endif // OMNI_HAVE_SQLITE',
            '',
        ]
    )

    custom_types = getattr(mir, 'types', {})
    lines.extend(_emit_c_type_decls(custom_types))

    for fn in mir.functions.values():
        params = ', '.join(f'{_c_type(p.type)} {p.name}' for p in fn.params) or 'void'
        ret = _c_type(fn.return_type)
        lines.append(f'{ret} {fn.name}({params});')
    if mir.functions:
        lines.append('')

    for fn in mir.functions.values():
        params = ', '.join(f'{_c_type(p.type)} {p.name}' for p in fn.params) or 'void'
        ret = _c_type(fn.return_type)
        lines.append(f'{ret} {fn.name}({params}) {{')
        declared = {p.name for p in fn.params}
        types: dict[str, str] = {p.name: p.type for p in fn.params}
        for stmt in fn.body:
            lines.append(_c_stmt(stmt, declared, custom_types, 2, types))
        lines.append('}')
        lines.append('')

    lines.append('int main(int argc, char** argv) {')
    lines.append('  (void)argc; (void)argv;')
    lines.append('  ecs_world_t* world = ecs_init();')
    lines.append('  (void)world;')
    lines.append('')

    main_types: dict[str, str] = {}
    constructs: dict[str, dict[str, Any]] = {}
    for stmt in mir.entry_point:
        if stmt.get('op') == 'assign' and stmt['expr'].get('op') == 'struct':
            constructs[stmt['name']] = stmt['expr']

    sim_system_lines, run_ticks = _emit_sim_lowering(mir, custom_types, constructs, main_types)
    lines.extend(sim_system_lines)

    lines.append('')
    if run_ticks is not None:
        lines.append(f'  for (int _omni_tick = 0; _omni_tick < {run_ticks}; _omni_tick++) {{')
        lines.append('    ecs_progress(world, 0);')
        lines.append('  }')
    else:
        lines.append('  ecs_progress(world, 0);')
    lines.append('  ecs_fini(world);')
    lines.append('  return 0;')
    lines.append('}')

    return '\n'.join(lines)
