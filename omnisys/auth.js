"use strict";
/**
 * OMNISYS.auth — AuthN/AuthZ primitives: signed tokens, password hashing,
 * sessions. Built on OMNISYS.crypto. Tokens are compact signed JSON
 * (header.payload.signature), deterministic and verifiable.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const auth = (omnisys.auth = omnisys.auth || {});
  const core = omnisys.core;
  const crypto = omnisys.crypto;

  function b64url(text) {
    let out = crypto.to_hex(text);
    // hex -> base64url for compactness
    const raw = crypto.from_hex(out);
    let binary = "";
    for (const ch of raw) binary += String.fromCharCode(ch.charCodeAt(0));
    let b64;
    if (typeof btoa === "function") b64 = btoa(binary);
    else b64 = Buffer.from(binary, "binary").toString("base64");
    return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function unb64url(part) {
    let b64 = String(part).replace(/-/g, "+").replace(/_/g, "/");
    while (b64.length % 4 !== 0) b64 += "=";
    let binary;
    if (typeof atob === "function") binary = atob(b64);
    else binary = Buffer.from(b64, "base64").toString("binary");
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  }

  function sign(payload, secret) {
    const body = b64url(JSON.stringify(payload));
    const sig = crypto.hmac(secret, body).slice(0, 24);
    return body + "." + sig;
  }

  auth.token = function (subject, claims, secret) {
    const payload = Object.assign({ sub: String(subject), iat: Math.floor(Date.now() / 1000) }, claims || {});
    return sign(payload, secret);
  };
  auth.verify_token = function (token, secret) {
    const parts = String(token).split(".");
    if (parts.length !== 2) return { valid: false, reason: "malformed" };
    const body = parts[0];
    const sig = crypto.hmac(secret, body).slice(0, 24);
    if (!crypto.constant_time_eq(sig, parts[1])) return { valid: false, reason: "signature" };
    let payload;
    try {
      payload = JSON.parse(unb64url(body));
    } catch (e) {
      return { valid: false, reason: "payload" };
    }
    return { valid: true, sub: payload.sub, claims: payload };
  };
  auth.token_subject = function (token) {
    const result = auth.verify_token(token, "");
    return result.valid ? result.sub : "";
  };

  auth.hash_password = function (password, salt) {
    const hash = crypto.kdf(String(password), String(salt), 128);
    return String(salt) + "$" + hash;
  };
  auth.verify_password = function (password, hash) {
    const parts = String(hash).split("$");
    if (parts.length !== 2) return false;
    return crypto.constant_time_eq(parts[1], crypto.kdf(String(password), parts[0], 128));
  };

  auth.session_new = function (secret, subject, ttlSeconds) {
    const token = auth.token(subject, {}, secret);
    return {
      tag: "session",
      token: token,
      subject: subject,
      expiresAt: Math.floor(Date.now() / 1000) + (ttlSeconds || 3600),
    };
  };
  auth.session_valid = function (session) {
    return !!session && Math.floor(Date.now() / 1000) < session.expiresAt;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);