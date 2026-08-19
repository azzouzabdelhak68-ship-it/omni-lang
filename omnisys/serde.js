"use strict";
/**
 * OMNISYS.serde — JSON, CSV, hex, base64, schema validation.
 * Portable. base64 uses btoa/atob when available and a JS fallback in Node.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const serde = (omnisys.serde = omnisys.serde || {});
  const core = omnisys.core;

  serde.json_encode = function (value) {
    return JSON.stringify(value);
  };
  serde.json_decode = function (text) {
    return JSON.parse(text);
  };
  serde.csv_encode = function (rows) {
    return rows.map((row) => row.map((cell) => String(cell)).join(",")).join("\n");
  };
  serde.csv_decode = function (text) {
    return String(text)
      .trim()
      .split("\n")
      .filter((line) => line.length > 0)
      .map((line) => line.split(",").map((cell) => cell.trim()));
  };
  serde.to_hex = function (text) {
    let out = "";
    for (const ch of String(text)) {
      out += ch.charCodeAt(0).toString(16).padStart(2, "0");
    }
    return out;
  };
  serde.from_hex = function (hex) {
    let out = "";
    for (let i = 0; i + 1 < String(hex).length; i += 2) {
      out += String.fromCharCode(parseInt(String(hex).slice(i, i + 2), 16));
    }
    return out;
  };
  serde.base64_encode = function (text) {
    const bytes = new TextEncoder().encode(String(text));
    let binary = "";
    for (const b of bytes) binary += String.fromCharCode(b);
    if (typeof btoa === "function") return btoa(binary);
    return Buffer.from(binary, "binary").toString("base64");
  };
  serde.base64_decode = function (b64) {
    let binary;
    if (typeof atob === "function") binary = atob(String(b64));
    else binary = Buffer.from(String(b64), "base64").toString("binary");
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  };

  function typeMatches(actual, expected) {
    if (expected === "any") return true;
    if (expected === "text") return typeof actual === "string";
    if (expected === "number") return typeof actual === "number";
    if (expected === "boolean") return typeof actual === "boolean";
    if (expected === "list") return Array.isArray(actual);
    if (expected === "map") return typeof actual === "object" && actual !== null && !Array.isArray(actual);
    return true;
  }

  serde.schema_validate = function (value, schema) {
    if (typeof schema !== "object" || schema === null) return true;
    if (schema.type && !typeMatches(value, schema.type)) return false;
    if (schema.fields) {
      for (const key of Object.keys(schema.fields)) {
        if (!(key in value)) return false;
        if (!serde.schema_validate(value[key], schema.fields[key])) return false;
      }
    }
    return true;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);