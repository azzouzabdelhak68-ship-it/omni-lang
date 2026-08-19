"use strict";
/**
 * OMNISYS.db — in-memory relational data platform with SQLite persistence.
 * Portable semantic core: databases, tables with schemas, row insert/select/update/delete with
 * predicate functions, counts, schema introspection. Real backends (SQLite,
 * postgres) are escape hatches behind the same API.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const db = (omnisys.db = omnisys.db || {});
  const core = omnisys.core;

  // In-memory implementation (default)
  let _inMemoryDb = null;
  let _sqliteDb = null; // Will hold sql.js database instance
  let _sqliteFile = null; // Uint8Array for persistence

  function _getInMemoryDb() {
    if (!_inMemoryDb) {
      _inMemoryDb = { tag: "database", name: "memory", tables: {} };
    }
    return _inMemoryDb;
  }

  db.create_db = function (name) {
    return { tag: "database", name: String(name), tables: {} };
  };
  db.create_table = function (database, name, schema) {
    if (database.tables[String(name)]) core.panic("db: table already exists: " + name);
    const table = {
      tag: "table",
      name: String(name),
      schema: schema || {},
      rows: [],
      nextId: 1,
    };
    database.tables[String(name)] = table;
    return table;
  };
  db.insert = function (table, row) {
    const stored = Object.assign({ id: table.nextId++ }, row || {});
    table.rows.push(stored);
    return stored;
  };
  db.select = function (table, predicate) {
    if (typeof predicate === "function") return table.rows.filter(predicate);
    return table.rows.slice();
  };
  db.update = function (table, predicate, patch) {
    let count = 0;
    for (const row of table.rows) {
      if (predicate(row)) {
        Object.assign(row, patch || {});
        count++;
      }
    }
    return count;
  };
  db.delete = function (table, predicate) {
    const before = table.rows.length;
    table.rows = table.rows.filter((row) => !predicate(row));
    return before - table.rows.length;
  };
  db.count = function (table, predicate) {
    if (typeof predicate === "function") return table.rows.filter(predicate).length;
    return table.rows.length;
  };
  db.drop_table = function (database, name) {
    if (!database.tables[String(name)]) return false;
    delete database.tables[String(name)];
    return true;
  };
  db.schema = function (table) {
    return table.schema;
  };
  db.table_size = function (table) {
    return table.rows.length;
  };

  // SQLite persistence functions (use sql.js when available)
  db.db_open = async function (path) {
    if (typeof initSqlJs === "undefined") {
      core.panic("db_open: sql.js not loaded. Include sql-wasm.js before using SQLite persistence.");
    }
    const SQL = await initSqlJs({ locateFile: (file) => `https://sql.js.org/dist/${file}` });
    if (path === ":memory:" || !path) {
      _sqliteDb = new SQL.Database();
      _sqliteFile = null;
    } else {
      try {
        const response = await fetch(path);
        if (response.ok) {
          const arrayBuffer = await response.arrayBuffer();
          _sqliteFile = new Uint8Array(arrayBuffer);
          _sqliteDb = new SQL.Database(_sqliteFile);
        } else {
          _sqliteDb = new SQL.Database();
          _sqliteFile = null;
        }
      } catch {
        _sqliteDb = new SQL.Database();
        _sqliteFile = null;
      }
    }
    _sqliteDb.run("PRAGMA foreign_keys = ON");
  };

  db.db_query = function (sql, params) {
    if (!_sqliteDb) core.panic("db_query: no database open. Call db_open() first.");
    const stmt = _sqliteDb.prepare(sql);
    const results = [];
    if (params && params.length) {
      stmt.bind(params);
    }
    while (stmt.step()) {
      results.push(stmt.getAsObject());
    }
    stmt.free();
    return results;
  };

  db.db_exec = function (sql, params) {
    if (!_sqliteDb) core.panic("db_exec: no database open. Call db_open() first.");
    const stmt = _sqliteDb.prepare(sql);
    if (params && params.length) {
      stmt.bind(params);
    }
    stmt.step();
    const changes = _sqliteDb.getRowsModified();
    stmt.free();
    if (_sqliteFile !== null) {
      _sqliteFile = _sqliteDb.export();
    }
    return changes;
  };

  db.db_close = function () {
    if (_sqliteDb) {
      if (_sqliteFile !== null) {
        _sqliteFile = _sqliteDb.export();
      }
      _sqliteDb.close();
      _sqliteDb = null;
    }
  };

  // Export the database file for download/saving
  db.db_export = function () {
    if (!_sqliteDb || _sqliteFile === null) return null;
    return _sqliteFile;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);