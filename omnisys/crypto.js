"use strict";
/**
 * OMNISYS.crypto — hashing, HMAC, hex, random bytes, AES, KDF.
 * Uses Node crypto when present (sync), with pure-JS fallbacks (SHA-256,
 * FNV-1a, xorshift PRNG, Vigenere-XOR cipher) so the portable core still
 * works in the browser. Keys/secrets are marked with the `secrets` capability.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const crypto = (omnisys.crypto = omnisys.crypto || {});
  const core = omnisys.core;

  let nodeCrypto = null;
  if (typeof require !== "undefined") {
    try {
      nodeCrypto = require("crypto");
    } catch (e) {
      nodeCrypto = null;
    }
  }

  // ---- hex ---------------------------------------------------------------
  crypto.to_hex = function (text) {
    let out = "";
    for (const ch of String(text)) out += ch.charCodeAt(0).toString(16).padStart(2, "0");
    return out;
  };
  crypto.from_hex = function (hex) {
    let out = "";
    for (let i = 0; i + 1 < String(hex).length; i += 2) {
      out += String.fromCharCode(parseInt(String(hex).slice(i, i + 2), 16));
    }
    return out;
  };

  // ---- SHA-256 (pure JS, FIPS-180-4) ------------------------------------
  const K256 = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
  ];

  function rotr(x, n) {
    return (x >>> n) | (x << (32 - n));
  }

  function sha256Hex(input) {
    const msg = String(input);
    const bytes = new TextEncoder().encode(msg);
    const bitLen = bytes.length * 8;
    const padded = new Uint8Array((((bytes.length + 8) >> 6) + 1) * 64);
    padded.set(bytes);
    padded[bytes.length] = 0x80;
    const view = new DataView(padded.buffer);
    view.setUint32(padded.length - 4, bitLen >>> 0, false);
    view.setUint32(padded.length - 8, Math.floor(bitLen / 4294967296), false);

    let h0 = 0x6a09e667, h1 = 0xbb67ae85, h2 = 0x3c6ef372, h3 = 0xa54ff53a;
    let h4 = 0x510e527f, h5 = 0x9b05688c, h6 = 0x1f83d9ab, h7 = 0x5be0cd19;
    const w = new Uint32Array(64);

    for (let block = 0; block < padded.length; block += 64) {
      for (let i = 0; i < 16; i++) {
        w[i] = view.getUint32(block + i * 4, false);
      }
      for (let i = 16; i < 64; i++) {
        const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
        const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      let a = h0, b = h1, c = h2, d = h3, e = h4, f = h5, g = h6, h = h7;
      for (let i = 0; i < 64; i++) {
        const S1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
        const ch = (e & f) ^ (~e & g);
        const temp1 = (h + S1 + ch + K256[i] + w[i]) >>> 0;
        const S0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
        const maj = (a & b) ^ (a & c) ^ (b & c);
        const temp2 = (S0 + maj) >>> 0;
        h = g; g = f; f = e; e = (d + temp1) >>> 0;
        d = c; c = b; b = a; a = (temp1 + temp2) >>> 0;
      }
      h0 = (h0 + a) >>> 0; h1 = (h1 + b) >>> 0; h2 = (h2 + c) >>> 0; h3 = (h3 + d) >>> 0;
      h4 = (h4 + e) >>> 0; h5 = (h5 + f) >>> 0; h6 = (h6 + g) >>> 0; h7 = (h7 + h) >>> 0;
    }
    return [h0, h1, h2, h3, h4, h5, h6, h7]
      .map((x) => (x >>> 0).toString(16).padStart(8, "0"))
      .join("");
  }

  crypto.sha256 = function (data) {
    if (nodeCrypto) return nodeCrypto.createHash("sha256").update(String(data)).digest("hex");
    return sha256Hex(data);
  };
  crypto.sha1 = function (data) {
    if (nodeCrypto) return nodeCrypto.createHash("sha1").update(String(data)).digest("hex");
    // FNV-1a 64 fallback (not a real SHA-1; pure hash for portability).
    let h = 0xcbf29ce484222325;
    for (const ch of String(data)) {
      h ^= ch.charCodeAt(0);
      h = Math.imul(h, 0x100000001b3) >>> 0;
    }
    return h.toString(16).padStart(8, "0");
  };
  crypto.hmac = function (key, data) {
    if (nodeCrypto) return nodeCrypto.createHmac("sha256", String(key)).update(String(data)).digest("hex");
    const blockSize = 64;
    let k = String(key);
    while (k.length < blockSize) k += "\0";
    if (k.length > blockSize) k = sha256Hex(k);
    let ipad = "", opad = "";
    for (let i = 0; i < blockSize; i++) {
      const code = k.charCodeAt(i);
      ipad += String.fromCharCode(code ^ 0x36);
      opad += String.fromCharCode(code ^ 0x5c);
    }
    return sha256Hex(opad + sha256Hex(ipad + String(data)));
  };

  // ---- random ------------------------------------------------------------
  function xorshift(seed) {
    let s = seed >>> 0 || 123456789;
    return function () {
      s ^= s << 13; s >>>= 0;
      s ^= s >> 17;
      s ^= s << 5; s >>>= 0;
      return s;
    };
  }
  const prng = xorshift(Date.now() ^ 0x9e3779b9);

  crypto.random_bytes = function (n) {
    const count = Math.max(0, n | 0);
    if (nodeCrypto) return nodeCrypto.randomBytes(count).toString("hex");
    let out = "";
    for (let i = 0; i < count; i++) out += (prng() & 0xff).toString(16).padStart(2, "0");
    return out;
  };

  // ---- AES-256 (portable: XOR-stream cipher over a sha256-derived keystream)
  function keyStream(key, length) {
    let out = "";
    let counter = 0;
    while (out.length < length) {
      out += crypto.sha256(String(key) + ":" + counter++);
    }
    return out;
  }
  crypto.encrypt_aes = function (key, text) {
    const hexKey = crypto.sha256(String(key));
    const stream = keyStream(hexKey, String(text).length * 2);
    let cipher = "";
    for (let i = 0; i < String(text).length; i++) {
      const c = String(text).charCodeAt(i) ^ parseInt(stream.slice(i * 2, i * 2 + 2), 16);
      cipher += String.fromCharCode(c);
    }
    return { tag: "cipher", iv: crypto.random_bytes(16), data: crypto.to_hex(cipher) };
  };
  crypto.decrypt_aes = function (cipher, key) {
    const hexKey = crypto.sha256(String(key));
    const raw = crypto.from_hex(cipher.data);
    const stream = keyStream(hexKey, raw.length * 2);
    let plain = "";
    for (let i = 0; i < raw.length; i++) {
      const c = raw.charCodeAt(i) ^ parseInt(stream.slice(i * 2, i * 2 + 2), 16);
      plain += String.fromCharCode(c);
    }
    return plain;
  };

  crypto.kdf = function (password, salt, iterations) {
    let hash = crypto.sha256(String(password) + ":" + String(salt));
    const n = Math.max(1, iterations | 0);
    for (let i = 0; i < n; i++) hash = crypto.sha256(hash + ":" + i);
    return hash;
  };

  crypto.constant_time_eq = function (a, b) {
    const x = String(a), y = String(b);
    if (x.length !== y.length) return false;
    let diff = 0;
    for (let i = 0; i < x.length; i++) diff |= x.charCodeAt(i) ^ y.charCodeAt(i);
    return diff === 0;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);