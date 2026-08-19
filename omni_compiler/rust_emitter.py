# ruff: noqa: Q000, PLR0911, PLR0912
"""Rust Emitter Module with Bevy ECS Adapter and SQLite Support.

Generates Rust 2021 code from OMNI MIR for native targets. The emitted code
uses the ``bevy`` crate for the simulation layer (``sim.*`` calls) and is a
plain, dependency-free program otherwise. Bevy sections are delimited by
comments so the simulation parts can be stripped and the file still compiles.

SQLite support is enabled via the ``sqlite`` feature flag which adds
``rusqlite`` and ``serde_json`` dependencies.

Floating-point conformance: Rust's f64 follows IEEE 754 by default.
This module provides explicit helpers for consistent behavior across backends.
"""

from typing import Any

MIN_QUOTE_LEN = 2


def _rs_type(omni_type: str) -> str:
    """Map an OmniScript type to a Rust type."""
    type_map = {
        'Number': 'f64',
        'Text': 'String',
        'Boolean': 'bool',
        'List': 'Vec<f64>',
        'None': '()',
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
                fmt_parts.append(''.join(buf).replace('{', '{{').replace('}', '}}'))
                buf = []
            fmt_parts.append('{}')
            args.append(slot)
            i = j + 1
        else:
            buf.append(body[i])
            i += 1
    if buf:
        fmt_parts.append(''.join(buf).replace('{', '{{').replace('}', '}}'))
    fmt = ''.join(fmt_parts)
    if not args:
        return f'String::from("{fmt}")'
    return f'format!("{fmt}", {", ".join(args)})'


def _rs_expr(e: dict[str, Any], declared: set[str]) -> str:
    op = e.get('op')
    if op == 'number':
        val = str(e['value'])
        return f'{val}.0' if '.' not in val and 'e' not in val.lower() else val
    if op == 'boolean':
        return 'true' if e['value'] else 'false'
    if op == 'none':
        return '()'
    if op == 'ident':
        return str(e['name'])
    if op == 'text':
        return _rs_text_expr(str(e['value']))
    if op == 'call':
        if e['name'] == 'join' and len(e['args']) == MIN_QUOTE_LEN:
            lst = _rs_expr(e['args'][0], declared)
            sep = _rs_expr(e['args'][1], declared)
            return f'omni_join({lst}, {sep})'
        if str(e['name']).startswith('sim.'):
            return _rs_sim_call(e, declared)
        args = ', '.join(_rs_expr(a, declared) for a in e['args'])
        return f'{e["name"]}({args})'
    if op == 'list':
        items = ', '.join(_rs_expr(i, declared) for i in e['items'])
        return f'vec![{items}]'
    if op == 'map':
        pairs = ', '.join(
            f'("{k}".to_string(), {_rs_expr(v, declared)})' for k, v in e.get('items', {}).items()
        )
        return f'omni_map(vec![{pairs}])'
    if op == 'index':
        return (
            f'{_rs_expr(e.get("object", {}), declared)}[{_rs_expr(e.get("index", {}), declared)}]'
        )
    if op == 'await':
        return _rs_expr(e.get('expr', {}), declared)
    if op == 'field':
        return f'{_rs_expr(e["object"], declared)}.{e["field"]}'
    if op == 'struct':
        parts = [f'{name}: {_rs_expr(value, declared)}' for name, value in e['args'].items()]
        return f'{e["name"]} {{ {", ".join(parts)} }}'
    if op == 'group':
        return f'({_rs_expr(e["expr"], declared)})'
    if op == 'not':
        return f'(!{_rs_expr(e["operand"], declared)})'
    if op == 'neg':
        return f'(-{_rs_expr(e["operand"], declared)})'
    op_str = str(op)
    if op_str == '/':
        return f'omni_fp_divide({_rs_expr(e["left"], declared)}, {_rs_expr(e["right"], declared)})'
    if op_str == '%':
        return f'omni_fp_modulo({_rs_expr(e["left"], declared)}, {_rs_expr(e["right"], declared)})'
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
    cop = op_map.get(op_str, op_str)
    return f'{_rs_expr(e["left"], declared)} {cop} {_rs_expr(e["right"], declared)}'


def _rs_sim_call(e: dict[str, Any], declared: set[str]) -> str:
    """Lower a sim.* call inside a function to its Bevy/plain form."""
    name = str(e.get('name', ''))
    args = e.get('args', [])
    if name == 'sim.entity':
        name_arg = _rs_text(str(args[0].get('value', 'entity')))
        return f'// sim.entity {name_arg} -> Bevy spawn in App setup'
    if name == 'sim.system':
        fn_arg = str(args[1].get('name', '')) if len(args) > 1 else ''
        return f'// sim.system {fn_arg} -> Bevy Update system'
    if name == 'sim.for_each':
        return '// sim.for_each -> Bevy Query'
    if name == 'sim.run':
        n = _rs_expr(args[0], declared) if args else '0'
        return f'// sim.run {n} -> Bevy run {n} frames'
    if name == 'sim.query':
        comp = _rs_text(str(args[0].get('value', ''))) if args else '""'
        return f'// sim.query {comp} -> Bevy Query'
    return f'{name}({", ".join(_rs_expr(a, declared) for a in args)})'


def _rs_sim_assign(stmt: dict[str, Any]) -> str:
    """Lower an assignment whose value is a ``sim.*`` call to a compilable stub."""
    name = str(stmt['name'])
    sim_name = str(stmt['expr'].get('name', ''))
    args = stmt['expr'].get('args', [])
    if sim_name == 'sim.query':
        comp = _rs_text(str(args[0].get('value', ''))) if args else '""'
        return f'let mut {name}: Vec<f64> = Vec::new(); // sim.query {comp} -> Bevy Query'
    if sim_name == 'sim.run':
        n = _rs_expr(args[0], set()) if args else '0'
        return f'let mut {name} = 0.0; // sim.run {n} -> Bevy run frames'
    return f'let mut {name} = 0.0; // {sim_name} -> Bevy'


def _rs_stmt(s: dict[str, Any], declared: set[str], indent: int = 4) -> str:
    pad = ' ' * indent
    op = s.get('op')
    if op == 'assign':
        var_name = s['name']
        if var_name not in declared:
            declared.add(var_name)
            return f'{pad}let mut {var_name} = {_rs_expr(s["expr"], declared)};'
        return f'{pad}{var_name} = {_rs_expr(s["expr"], declared)};'
    if op == 'return':
        return f'{pad}return {_rs_expr(s["expr"], declared)};'
    if op == 'show':
        return f'{pad}println!("{{}}", {_rs_expr(s["expr"], declared)});'
    if op == 'break':
        return f'{pad}break;'
    if op == 'continue':
        return f'{pad}continue;'
    if op == 'if':
        lines = [f'{pad}if {_rs_expr(s["cond"], declared)} {{']
        for st in s['body']:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f'{pad}}}')
        if s.get('else'):
            lines.append(f'{pad}else {{')
            for st in s['else']:
                lines.append(_rs_stmt(st, declared, indent + 2))
            lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'for':
        var = s['var']
        iterable = _rs_expr(s['iterable'], declared)
        lines = [f'{pad}for x in &{iterable} {{', f'{pad}  let {var} = x;']
        for st in s['body']:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'while':
        lines = [f'{pad}while {_rs_expr(s["cond"], declared)} {{']
        for st in s['body']:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f'{pad}}}')
        return '\n'.join(lines)
    if op == 'try':
        lines = [f'{pad}// try/catch lowered to a match guard', f'{pad}{{']
        for st in s['body']:
            lines.append(_rs_stmt(st, declared, indent + 2))
        lines.append(f'{pad}}}')
        for st in s.get('on_error', []):
            lines.append(_rs_stmt(st, declared, indent + 2))
        if s.get('finally'):
            for st in s['finally']:
                lines.append(_rs_stmt(st, declared, indent + 2))
        return '\n'.join(lines)
    if op == 'global':
        return f'{pad}// global {s.get("name", "")}'
    if op == 'call':
        return f'{pad}{_rs_expr(s, declared)};'
    return f'{pad}// unknown statement: {s!r}'


def _rs_preamble(custom_types: dict[str, Any]) -> list[str]:  # noqa: PLR0915
    lines = [
        '// Generated by the OmniScript Rust Emitter (v3.4)',
        '',
        '// Bevy ECS integration (optional).',
        '// Remove the `bevy` sections below to build as a plain Rust program.',
        '// #[cfg(feature = "bevy")]',
        '// use bevy::prelude::*;',
        '',
        '// SQLite support (optional, enabled via `sqlite` feature)',
        '// #[cfg(feature = "sqlite")]',
        '// use rusqlite::{Connection, Result as SqliteResult, params, params_from_iter};',
        '// #[cfg(feature = "sqlite")]',
        '// use serde_json::{json, Value as JsonValue};',
        '// #[cfg(feature = "sqlite")]',
        '// use std::sync::Mutex;',
        '// #[cfg(feature = "sqlite")]',
        '// static SQLITE_DB: Mutex<Option<Connection>> = Mutex::new(None);',
        '',
        '// IEEE 754 Floating-Point Conformance Helpers (Rust f64 is IEEE 754 compliant)',
        'fn omni_fp_is_nan(x: f64) -> bool { x.is_nan() }',
        'fn omni_fp_is_finite(x: f64) -> bool { x.is_finite() }',
        'fn omni_fp_is_infinite(x: f64) -> bool { x.is_infinite() }',
        'fn omni_fp_divide(a: f64, b: f64) -> f64 {',
        '    if b == 0.0 {',
        '        if a == 0.0 { return f64::NAN; }',
        '        return if a > 0.0 { f64::INFINITY } else { f64::NEG_INFINITY };',
        '    }',
        '    a / b',
        '}',
        'fn omni_fp_modulo(a: f64, b: f64) -> f64 {',
        '    if b == 0.0 || a.is_nan() || b.is_nan() { return f64::NAN; }',
        '    if a.is_infinite() { return f64::NAN; }',
        '    a % b',
        '}',
        'fn omni_fp_neg_zero() -> f64 { -0.0 }',
        'fn omni_fp_copy_sign(x: f64, y: f64) -> f64 { x.copysign(y) }',
        '',
    ]

    # SQLite functions (enabled via `sqlite` feature)
    lines.extend(
        [
            '#[cfg(feature = "sqlite")]',
            '// Global SQLite connection',
            'static SQLITE_DB: Mutex<Option<Connection>> = Mutex::new(None);',
            '',
            '#[cfg(feature = "sqlite")]',
            '// db_open(path) - open or create SQLite database',
            '// path: None for in-memory, Some(path) for file',
            'fn omnisys_db_open(path: Option<String>) -> Result<(), Box<dyn std::error::Error>> {',
            '    let mut db = SQLITE_DB.lock().unwrap();',
            '    if db.is_some() {',
            '        *db = None;',
            '    }',
            '    let conn = match path {',
            '        Some(p) if !p.is_empty() => Connection::open(p)?,',
            '        _ => Connection::open_in_memory()?,',
            '    };',
            '    conn.execute("PRAGMA foreign_keys = ON", [])?;',
            '    *db = Some(conn);',
            '    Ok(())',
            '}',
            '',
            '#[cfg(feature = "sqlite")]',
            '// db_exec(sql, params_json) - execute DDL/DML',
            '// params_json: JSON array of parameters',
            'fn omnisys_db_exec(sql: &str, params_json: &str) -> Result<i64, Box<dyn std::error::Error>> {',  # noqa: E501
            '    let db = SQLITE_DB.lock().unwrap();',
            '    let conn = db.as_ref().ok_or("No database open")?;',
            '    let params: Vec<JsonValue> = serde_json::from_str(params_json).unwrap_or_default();',  # noqa: E501
            '    let mut stmt = conn.prepare(sql)?;',
            '    let param_refs: Vec<&dyn rusqlite::ToSql> = params.iter().map(|v| v as &dyn rusqlite::ToSql).collect();',  # noqa: E501
            '    let changed = stmt.execute(params_from_iter(param_refs))?;',
            '    Ok(changed as i64)',
            '}',
            '',
            '#[cfg(feature = "sqlite")]',
            '// db_query(sql, params_json) - execute SELECT and return JSON string',
            'fn omnisys_db_query(sql: &str, params_json: &str) -> Result<String, Box<dyn std::error::Error>> {',  # noqa: E501
            '    let db = SQLITE_DB.lock().unwrap();',
            '    let conn = db.as_ref().ok_or("No database open")?;',
            '    let params: Vec<JsonValue> = serde_json::from_str(params_json).unwrap_or_default();',  # noqa: E501
            '    let mut stmt = conn.prepare(sql)?;',
            '    let param_refs: Vec<&dyn rusqlite::ToSql> = params.iter().map(|v| v as &dyn rusqlite::ToSql).collect();',  # noqa: E501
            '    let rows = stmt.query_map(params_from_iter(param_refs), |row| {',
            '        let col_count = row.column_count();',
            '        let mut map = serde_json::Map::new();',
            '        for i in 0..col_count {',
            '            let name = row.column_name(i).unwrap_or("").to_string();',
            '            let value: JsonValue = match row.get_ref(i)? {',
            '                rusqlite::types::ValueRef::Null => JsonValue::Null,',
            '                rusqlite::types::ValueRef::Integer(i) => json!(i),',
            '                rusqlite::types::ValueRef::Real(f) => json!(f),',
            '                rusqlite::types::ValueRef::Text(t) => json!(String::from_utf8_lossy(t).to_string()),',  # noqa: E501
            '                rusqlite::types::ValueRef::Blob(b) => json!(b.to_vec()),',
            '            };',
            '            map.insert(name, value);',
            '        }',
            '        Ok(JsonValue::Object(map))',
            '    })?;',
            '    let mut results = Vec::new();',
            '    for row in rows {',
            '        results.push(row?);',
            '    }',
            '    Ok(serde_json::to_string(&results)?)',
            '}',
            '',
            '#[cfg(feature = "sqlite")]',
            '// db_close() - close SQLite database',
            'fn omnisys_db_close() {',
            '    let mut db = SQLITE_DB.lock().unwrap();',
            '    *db = None;',
            '}',
            '',
        ]
    )

    for tname, fields_info in custom_types.items():
        fields = (
            fields_info.get('fields', fields_info) if isinstance(fields_info, dict) else fields_info
        )
        lines.append('#[derive(Clone, Debug)]')
        lines.append(f'struct {tname} {{')
        for fname, ftype in fields.items():
            lines.append(f'    {fname}: {_rs_type(ftype)},')
        lines.append('}')
        lines.append('')
    lines.append('fn omni_join(list: Vec<String>, sep: &str) -> String {')
    lines.append('    list.join(sep)')
    lines.append('}')
    lines.append('')
    lines.append('fn omni_map<K, V>(pairs: Vec<(K, V)>) -> std::collections::HashMap<K, V> {')
    lines.append('    pairs.into_iter().collect()')
    lines.append('}')
    lines.append('')
    lines.append('// OMNISYS.async stubs (no-op for Rust target)')
    lines.append('struct OmniTask {')
    lines.append('    handle: *mut std::ffi::c_void,')
    lines.append('    cancel: fn(*mut std::ffi::c_void),')
    lines.append('}')
    lines.append('fn omni_async_cancel_stub(_handle: *mut std::ffi::c_void) {}')
    lines.append(
        'fn omnisys_async_task(fn: *mut std::ffi::c_void) -> OmniTask { OmniTask { handle: fn, cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_async_delay(_ms: f64) -> OmniTask { OmniTask { handle: std::ptr::null_mut(), cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_async_interval(_ms: f64, _fn: *mut std::ffi::c_void) -> OmniTask { OmniTask { handle: std::ptr::null_mut(), cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_async_timeout(_ms: f64, _fn: *mut std::ffi::c_void) -> OmniTask { OmniTask { handle: std::ptr::null_mut(), cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_async_tick(_fn: *mut std::ffi::c_void) -> OmniTask { OmniTask { handle: std::ptr::null_mut(), cancel: omni_async_cancel_stub } }'  # noqa: E501
    )
    lines.append('fn omnisys_async_cancel(task: OmniTask) { (task.cancel)(task.handle); }')
    lines.append('fn omnisys_async_await(task: OmniTask) -> *mut std::ffi::c_void { task.handle }')
    lines.append('')

    # OMNISYS.pkg — Semantic Versioning & Lockfile Support
    lines.append('/// Parsed semantic version (SemVer 2.0.0)')
    lines.append('#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]')
    lines.append('struct OmniVersion {')
    lines.append('    major: u64,')
    lines.append('    minor: u64,')
    lines.append('    patch: u64,')
    lines.append('    prerelease: String,')
    lines.append('    build: String,')
    lines.append('}')
    lines.append('')
    lines.append('impl std::fmt::Display for OmniVersion {')
    lines.append("    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {")
    lines.append('        write!(f, "{}.{}.{}", self.major, self.minor, self.patch)?;')
    lines.append('        if !self.prerelease.is_empty() {')
    lines.append('            write!(f, "-{}", self.prerelease)?;')
    lines.append('        }')
    lines.append('        if !self.build.is_empty() {')
    lines.append('            write!(f, "+{}", self.build)?;')
    lines.append('        }')
    lines.append('        Ok(())')
    lines.append('    }')
    lines.append('}')
    lines.append('')
    lines.append('/// Parse a semantic version string')
    lines.append('fn omni_pkg_parse_version(version: &str) -> Result<OmniVersion, String> {')
    lines.append('    let version = version.trim();')
    lines.append('    let re = regex::Regex::new(')
    lines.append(
        '        r"^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)(?:-((?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\\.(?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\\+([0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*))?$"'  # noqa: E501
    )
    lines.append('    ).map_err(|_| "Invalid regex".to_string())?;')
    lines.append(
        '    let caps = re.captures(version).ok_or_else(|| format!("Invalid semantic version: {}", version))?;'  # noqa: E501
    )
    lines.append('    Ok(OmniVersion {')
    lines.append('        major: caps[1].parse().unwrap(),')
    lines.append('        minor: caps[2].parse().unwrap(),')
    lines.append('        patch: caps[3].parse().unwrap(),')
    lines.append(
        '        prerelease: caps.get(4).map(|m| m.as_str().to_string()).unwrap_or_default(),'
    )
    lines.append('        build: caps.get(5).map(|m| m.as_str().to_string()).unwrap_or_default(),')
    lines.append('    })')
    lines.append('}')
    lines.append('')
    lines.append('/// Compare two versions')
    lines.append(
        'fn omni_pkg_cmp_version(a: &OmniVersion, b: &OmniVersion) -> std::cmp::Ordering {'
    )
    lines.append('    match a.major.cmp(&b.major) {')
    lines.append('        std::cmp::Ordering::Equal => {}')
    lines.append('        o => return o,')
    lines.append('    }')
    lines.append('    match a.minor.cmp(&b.minor) {')
    lines.append('        std::cmp::Ordering::Equal => {}')
    lines.append('        o => return o,')
    lines.append('    }')
    lines.append('    match a.patch.cmp(&b.patch) {')
    lines.append('        std::cmp::Ordering::Equal => {}')
    lines.append('        o => return o,')
    lines.append('    }')
    lines.append('    let a_pre = !a.prerelease.is_empty();')
    lines.append('    let b_pre = !b.prerelease.is_empty();')
    lines.append('    match (a_pre, b_pre) {')
    lines.append('        (true, false) => return std::cmp::Ordering::Less,')
    lines.append('        (false, true) => return std::cmp::Ordering::Greater,')
    lines.append('        (true, true) => return a.prerelease.cmp(&b.prerelease),')
    lines.append('        _ => {}')
    lines.append('    }')
    lines.append('    std::cmp::Ordering::Equal')
    lines.append('}')
    lines.append('')
    lines.append('/// Check if version satisfies constraint')
    lines.append('/// Supports: ^ (caret), ~ (tilde), >=, <=, >, <, =, ==, || (union)')
    lines.append('fn omni_pkg_satisfies(version: &str, constraint: &str) -> bool {')
    lines.append('    let v = match omni_pkg_parse_version(version) {')
    lines.append('        Ok(v) => v,')
    lines.append('        Err(_) => return false,')
    lines.append('    };')
    lines.append('    for part in constraint.split("||") {')
    lines.append('        let part = part.trim();')
    lines.append('        if part.is_empty() { continue; }')
    lines.append("        if part.starts_with('^') {")
    lines.append('            if let Ok(target) = omni_pkg_parse_version(&part[1..]) {')
    lines.append('                let upper = if target.major == 0 {')
    lines.append('                    if target.minor == 0 {')
    lines.append(
        '                        OmniVersion { major: 0, minor: 0, patch: target.patch + 1, prerelease: String::new(), build: String::new() }'  # noqa: E501
    )
    lines.append('                    } else {')
    lines.append(
        '                        OmniVersion { major: 0, minor: target.minor + 1, patch: 0, prerelease: String::new(), build: String::new() }'  # noqa: E501
    )
    lines.append('                    }')
    lines.append('                } else {')
    lines.append(
        '                    OmniVersion { major: target.major + 1, minor: 0, patch: 0, prerelease: String::new(), build: String::new() }'  # noqa: E501
    )
    lines.append('                };')
    lines.append('                if v >= target && v < upper { return true; }')
    lines.append('            }')
    lines.append("        } else if part.starts_with('~') {")
    lines.append('            if let Ok(target) = omni_pkg_parse_version(&part[1..]) {')
    lines.append(
        '                let upper = OmniVersion { major: target.major, minor: target.minor + 1, patch: 0, prerelease: String::new(), build: String::new() };'  # noqa: E501
    )
    lines.append('                if v >= target && v < upper { return true; }')
    lines.append('            }')
    lines.append(
        '        } else if part.starts_with(">=") || part.starts_with("<=") || part.starts_with(">") || part.starts_with("<") || part.starts_with("==") || part.starts_with(\'=\') {'  # noqa: E501
    )
    lines.append(
        '            let (op, ver_str) = if part.starts_with(">=") || part.starts_with("<=") || part.starts_with("==") {'  # noqa: E501
    )
    lines.append('                (&part[..2], &part[2..])')
    lines.append('            } else {')
    lines.append('                (&part[..1], &part[1..])')
    lines.append('            };')
    lines.append('            let ver_str = ver_str.trim();')
    lines.append('            if let Ok(target) = omni_pkg_parse_version(ver_str) {')
    lines.append('                let cmp = v.cmp(&target);')
    lines.append('                let matches = match op {')
    lines.append('                    ">=" => cmp >= std::cmp::Ordering::Equal,')
    lines.append('                    "<=" => cmp <= std::cmp::Ordering::Equal,')
    lines.append('                    ">" => cmp == std::cmp::Ordering::Greater,')
    lines.append('                    "<" => cmp == std::cmp::Ordering::Less,')
    lines.append('                    "=" | "==" => cmp == std::cmp::Ordering::Equal,')
    lines.append('                    _ => false,')
    lines.append('                };')
    lines.append('                if matches { return true; }')
    lines.append('            }')
    lines.append('        } else {')
    lines.append('            if let Ok(target) = omni_pkg_parse_version(part) {')
    lines.append('                if v == target { return true; }')
    lines.append('            }')
    lines.append('        }')
    lines.append('    }')
    lines.append('    false')
    lines.append('}')
    lines.append('')
    lines.append('/// Compute SHA256 checksum of content')
    lines.append('fn omni_pkg_compute_checksum(content: &str) -> String {')
    lines.append('    use sha2::{Sha256, Digest};')
    lines.append('    let mut hasher = Sha256::new();')
    lines.append('    hasher.update(content.as_bytes());')
    lines.append('    let result = hasher.finalize();')
    lines.append('    format!("sha256:{}", hex::encode(result))')
    lines.append('}')
    lines.append('')
    lines.append('/// Lockfile entry')
    lines.append('#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]')
    lines.append('struct OmniLockfileEntry {')
    lines.append('    name: String,')
    lines.append('    version: String,')
    lines.append('    checksum: String,')
    lines.append('    dependencies: std::collections::HashMap<String, String>,')
    lines.append('}')
    lines.append('')
    lines.append('/// Lockfile')
    lines.append('#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]')
    lines.append('struct OmniLockfile {')
    lines.append('    version: u32,')
    lines.append('    packages: Vec<OmniLockfileEntry>,')
    lines.append('    metadata: std::collections::HashMap<String, serde_json::Value>,')
    lines.append('}')
    lines.append('')
    lines.append('impl OmniLockfile {')
    lines.append('    fn new() -> Self {')
    lines.append(
        '        Self { version: 1, packages: Vec::new(), metadata: std::collections::HashMap::new() }'  # noqa: E501
    )
    lines.append('    }')
    lines.append('    fn add(&mut self, entry: OmniLockfileEntry) { self.packages.push(entry); }')
    lines.append(
        '    fn get(&self, name: &str) -> Option<&OmniLockfileEntry> { self.packages.iter().find(|e| e.name == name) }'  # noqa: E501
    )
    lines.append(
        '    fn to_json(&self) -> String { serde_json::to_string(self).unwrap_or_default() }'
    )
    lines.append(
        '    fn from_json(json: &str) -> Result<Self, serde_json::Error> { serde_json::from_str(json) }'  # noqa: E501
    )
    lines.append('}')
    lines.append('')
    lines.append('/// Package spec for resolution')
    lines.append('#[derive(Debug, Clone)]')
    lines.append('struct OmniPackageSpec {')
    lines.append('    name: String,')
    lines.append('    version_constraint: String,')
    lines.append('    dependencies: std::collections::HashMap<String, String>,')
    lines.append('    checksum: Option<String>,')
    lines.append('}')
    lines.append('')
    lines.append('/// Resolution result')
    lines.append('#[derive(Debug, Clone)]')
    lines.append('struct OmniResolution {')
    lines.append('    packages: Vec<OmniLockfileEntry>,')
    lines.append('    lockfile: OmniLockfile,')
    lines.append('    warnings: Vec<String>,')
    lines.append('}')
    lines.append('')
    lines.append('/// Deterministic version resolution')
    lines.append('fn omni_pkg_resolve_versions(')
    lines.append('    specs: &[OmniPackageSpec],')
    lines.append(
        '    registry: &std::collections::HashMap<String, std::collections::HashMap<String, serde_json::Value>>,'  # noqa: E501
    )
    lines.append('    lockfile: Option<&OmniLockfile>,')
    lines.append(') -> OmniResolution {')
    lines.append('    use std::collections::{HashMap, HashSet};')
    lines.append(
        '    let spec_by_name: HashMap<_, _> = specs.iter().map(|s| (s.name.clone(), s)).collect();'
    )
    lines.append('    let mut resolved: HashMap<String, OmniLockfileEntry> = HashMap::new();')
    lines.append('    let mut warnings = Vec::new();')
    lines.append('    let mut visiting = HashSet::new();')
    lines.append('    let mut visited = HashSet::new();')
    lines.append('')
    lines.append('    fn visit(')
    lines.append('        name: &str,')
    lines.append('        spec_by_name: &HashMap<String, &OmniPackageSpec>,')
    lines.append('        registry: &HashMap<String, HashMap<String, serde_json::Value>>,')
    lines.append('        lockfile: Option<&OmniLockfile>,')
    lines.append('        resolved: &mut HashMap<String, OmniLockfileEntry>,')
    lines.append('        visiting: &mut HashSet<String>,')
    lines.append('        visited: &mut HashSet<String>,')
    lines.append('        warnings: &mut Vec<String>,')
    lines.append('    ) {')
    lines.append('        if resolved.contains_key(name) { return; }')
    lines.append('        if visiting.contains(name) {')
    lines.append(
        '            warnings.push(format!("Circular dependency detected involving {}", name));'
    )
    lines.append('            return;')
    lines.append('        }')
    lines.append('        let Some(spec) = spec_by_name.get(name) else {')
    lines.append('            warnings.push(format!("Package {} not found in specs", name));')
    lines.append('            return;')
    lines.append('        };')
    lines.append('        visiting.insert(name.to_string());')
    lines.append('        for (dep_name, dep_constraint) in &spec.dependencies {')
    lines.append(
        '            visit(dep_name, spec_by_name, registry, lockfile, resolved, visiting, visited, warnings);'  # noqa: E501
    )
    lines.append('        }')
    lines.append(
        '        let selected_version = select_best_version(registry, name, &spec.version_constraint, lockfile);'  # noqa: E501
    )
    lines.append('        let selected_version = match selected_version {')
    lines.append('            Some(v) => v,')
    lines.append('            None => {')
    lines.append(
        '                warnings.push(format!("No version found for {} matching {}", name, spec.version_constraint));'  # noqa: E501
    )
    lines.append('                visiting.remove(name);')
    lines.append('                return;')
    lines.append('            }')
    lines.append('        };')
    lines.append(
        '        let reg_entry = registry.get(name).and_then(|v| v.get(&selected_version));'
    )
    lines.append('        let mut dep_versions = HashMap::new();')
    lines.append('        for (dep_name, _) in &spec.dependencies {')
    lines.append('            if let Some(entry) = resolved.get(dep_name) {')
    lines.append('                dep_versions.insert(dep_name.clone(), entry.version.clone());')
    lines.append('            }')
    lines.append('        }')
    lines.append('        let checksum = spec.checksum.clone().unwrap_or_else(|| {')
    lines.append('            let content = serde_json::to_string(&reg_entry).unwrap_or_default();')
    lines.append('            omni_pkg_compute_checksum(&content)')
    lines.append('        });')
    lines.append('        let entry = OmniLockfileEntry {')
    lines.append('            name: name.to_string(),')
    lines.append('            version: selected_version,')
    lines.append('            checksum,')
    lines.append('            dependencies: dep_versions,')
    lines.append('        };')
    lines.append('        resolved.insert(name.to_string(), entry);')
    lines.append('        visiting.remove(name);')
    lines.append('        visited.insert(name.to_string());')
    lines.append('    }')
    lines.append('')
    lines.append('    fn select_best_version(')
    lines.append('        registry: &HashMap<String, HashMap<String, serde_json::Value>>,')
    lines.append('        name: &str,')
    lines.append('        constraint: &str,')
    lines.append('        lockfile: Option<&OmniLockfile>,')
    lines.append('    ) -> Option<String> {')
    lines.append('        if let Some(lf) = lockfile {')
    lines.append('            if let Some(locked) = lf.get(name) {')
    lines.append('                if omni_pkg_satisfies(&locked.version, constraint) {')
    lines.append(
        '                    if registry.get(name).map(|v| v.contains_key(&locked.version)).unwrap_or(false) {'  # noqa: E501
    )
    lines.append('                        return Some(locked.version.clone());')
    lines.append('                    }')
    lines.append('                }')
    lines.append('            }')
    lines.append('        }')
    lines.append('        let versions = registry.get(name)?;')
    lines.append('        let mut vers: Vec<_> = versions.keys()')
    lines.append('            .filter_map(|v| omni_pkg_parse_version(v).ok())')
    lines.append('            .collect();')
    lines.append('        vers.sort_by(|a, b| b.cmp(a));')
    lines.append('        for v in vers {')
    lines.append('            if omni_pkg_satisfies(&v.to_string(), constraint) {')
    lines.append('                return Some(v.to_string());')
    lines.append('            }')
    lines.append('        }')
    lines.append('        None')
    lines.append('    }')
    lines.append('')
    lines.append(
        '    for spec in specs { visit(&spec.name, &spec_by_name, registry, lockfile, &mut resolved, &mut visiting, &mut visited, &mut warnings); }'  # noqa: E501
    )
    lines.append('')
    lines.append('    let mut ordered = Vec::new();')
    lines.append('    let mut seen = HashSet::new();')
    lines.append('')
    lines.append('    fn order(')
    lines.append('        name: &str,')
    lines.append('        resolved: &HashMap<String, OmniLockfileEntry>,')
    lines.append('        ordered: &mut Vec<OmniLockfileEntry>,')
    lines.append('        seen: &mut HashSet<String>,')
    lines.append('    ) {')
    lines.append('        if seen.contains(name) || !resolved.contains_key(name) { return; }')
    lines.append('        let entry = &resolved[name];')
    lines.append(
        '        for dep in entry.dependencies.keys() { order(dep, resolved, ordered, seen); }'
    )
    lines.append(
        '        if !seen.contains(name) { seen.insert(name.to_string()); ordered.push(entry.clone()); }'  # noqa: E501
    )
    lines.append('    }')
    lines.append('')
    lines.append('    for spec in specs { order(&spec.name, &resolved, &mut ordered, &mut seen); }')
    lines.append('')
    lines.append(
        '    let lockfile = OmniLockfile { version: 1, packages: ordered.clone(), metadata: std::collections::HashMap::new() };'  # noqa: E501
    )
    lines.append('    OmniResolution { packages: ordered, lockfile, warnings }')
    lines.append('}')
    lines.append('')
    lines.append('/// OMNISYS.pkg function exports for Rust target')
    lines.append(
        'fn omnisys_pkg_parse_version(version: &str) -> Result<OmniVersion, String> { omni_pkg_parse_version(version) }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_pkg_satisfies(version: &str, constraint: &str) -> bool { omni_pkg_satisfies(version, constraint) }'  # noqa: E501
    )
    lines.append(
        'fn omnisys_pkg_compute_checksum(content: &str) -> String { omni_pkg_compute_checksum(content) }'  # noqa: E501
    )
    lines.append('fn omnisys_pkg_lockfile_new() -> OmniLockfile { OmniLockfile::new() }')
    lines.append('fn omnisys_pkg_lockfile_to_json(lf: &OmniLockfile) -> String { lf.to_json() }')
    lines.append(
        'fn omnisys_pkg_lockfile_from_json(json: &str) -> Result<OmniLockfile, serde_json::Error> { OmniLockfile::from_json(json) }'  # noqa: E501
    )
    lines.append('fn omnisys_pkg_resolve_versions(')
    lines.append('    specs: &[OmniPackageSpec],')
    lines.append(
        '    registry: &std::collections::HashMap<String, std::collections::HashMap<String, serde_json::Value>>,'  # noqa: E501
    )
    lines.append('    lockfile: Option<&OmniLockfile>,')
    lines.append(') -> OmniResolution { omni_pkg_resolve_versions(specs, registry, lockfile) }')
    lines.append('')
    return lines


def _rs_sim_components(mir: Any) -> tuple[list[str], list[str]]:
    """Return (component structs, spawn functions) for sim.* usage in entry point."""
    used: list[str] = []
    structs: list[str] = []
    spawn_lines: list[str] = []
    for stmt in mir.entry_point:
        if stmt.get('op') != 'call' or not str(stmt.get('name', '')).startswith('sim.'):
            continue
        for arg in stmt.get('args', []):
            if arg.get('op') != 'list':
                continue
            for item in arg.get('items', []):
                if item.get('op') == 'struct' and item['name'] not in used:
                    used.append(item['name'])
    for tname in used:
        fields_info = mir.types.get(tname, {})
        fields = (
            fields_info.get('fields', fields_info) if isinstance(fields_info, dict) else fields_info
        )
        structs.append('#[derive(Component, Clone, Debug)]')
        structs.append(f'struct {tname} {{')
        for fname, ftype in fields.items():
            structs.append(f'    {fname}: {_rs_type(ftype)},')
        structs.append('}')
        structs.append('')
    if used:
        spawn_lines.append('// Bevy app setup (sim.entity / sim.system / sim.for_each)')
        spawn_lines.append('#[cfg(feature = "bevy")]')
        spawn_lines.append('fn setup(mut commands: Commands) {')
        for stmt in mir.entry_point:
            is_entity = (
                stmt.get('op') == 'call'
                and str(stmt.get('name', '')) == 'sim.entity'
                and len(stmt.get('args', [])) >= MIN_QUOTE_LEN
            )
            if is_entity:
                name_arg = _rs_text(str(stmt['args'][0].get('value', 'entity')))
                spawn_lines.append('    commands.spawn((')
                for item in stmt['args'][1].get('items', []):
                    if item.get('op') == 'struct':
                        spawn_lines.append(f'        {_rs_expr(item, set())},')
                spawn_lines.append(f'    )).insert(Name::new({name_arg}));')
        spawn_lines.append('}')
        spawn_lines.append('')
    return structs, spawn_lines


def emit_rust(mir: Any) -> str:
    """Emit Rust 2021 code with a Bevy adapter from OMNI MIR."""
    lines = _rs_preamble(mir.types)

    component_structs, spawn = _rs_sim_components(mir)
    if component_structs:
        lines.append('// Bevy components (sim.* usage)')
        lines.extend(component_structs)

    def _extract_cap_names(effects_list: list[Any]) -> list[Any]:
        """Extract capability names from effects list (handles both old string format and new tuple format)."""  # noqa: E501
        return [cap if isinstance(cap, str) else cap[0] for cap in effects_list]

    for fn in mir.functions.values():
        params = ', '.join(f'{p.name}: {_rs_type(p.type)}' for p in fn.params)
        ret = _rs_type(fn.return_type)
        ret_arrow = f' -> {ret}' if fn.return_type != 'None' else ''
        lines.append(f'fn {fn.name}({params}){ret_arrow} {{')
        if fn.effects.uses or fn.effects.reads or fn.effects.writes:
            uses = ', '.join(_extract_cap_names(fn.effects.uses))
            reads = ', '.join(_extract_cap_names(fn.effects.reads))
            writes = ', '.join(_extract_cap_names(fn.effects.writes))
            lines.append(f'    // effects: uses=[{uses}] reads=[{reads}] writes=[{writes}]')
        declared: set[str] = {p.name for p in fn.params}
        for stmt in fn.body:
            lines.append(_rs_stmt(stmt, declared, 4))
        lines.append('}')
        lines.append('')

    lines.extend(spawn)

    lines.append('fn main() {')
    lines.append('    // when app starts')
    declared_main: set[str] = set()
    for stmt in mir.entry_point:
        if stmt.get('op') == 'call' and str(stmt.get('name', '')).startswith('sim.'):
            lines.append('    ' + _rs_expr(stmt, declared_main))
            continue
        if (
            stmt.get('op') == 'assign'
            and stmt['expr'].get('op') == 'call'
            and str(stmt['expr'].get('name', '')).startswith('sim.')
        ):
            lines.append('    ' + _rs_sim_assign(stmt))
            continue
        lines.append(_rs_stmt(stmt, declared_main, 4))
    lines.append('}')
    lines.append('')

    if mir.scene:
        lines.append('// 3D scene: render via the JS/WebGPU lane or a Bevy scene plugin.')
        lines.append('// scene objects: ' + ', '.join(o['shape'] for o in mir.scene))

    return '\n'.join(lines)


def emit_rust_with_runtime(mir: Any) -> str:
    """Emit Rust code with the embedded runtime (alias of emit_rust)."""
    return emit_rust(mir)
