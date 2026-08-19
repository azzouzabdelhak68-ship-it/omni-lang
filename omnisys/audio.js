"use strict";
/**
 * OMNISYS.audio — portable audio model: buffers, synthesis, mixing, WAV
 * encoding. Pure and deterministic; the reference output is a base64 WAV
 * string. Hardware audio I/O is an escape.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const audio = (omnisys.audio = omnisys.audio || {});
  const core = omnisys.core;

  audio.buffer = function (length) {
    return { tag: "audio.buffer", samples: new Array(Math.max(0, length | 0)).fill(0) };
  };
  audio.tone = function (freq, duration, rate) {
    const sampleRate = rate || 44100;
    const n = Math.max(1, Math.round(duration * sampleRate));
    const samples = new Array(n);
    for (let i = 0; i < n; i++) {
      samples[i] = Math.sin((2 * Math.PI * freq * i) / sampleRate);
    }
    return { tag: "audio.buffer", samples: samples, sampleRate: sampleRate };
  };
  audio.silence = function (duration, rate) {
    const sampleRate = rate || 44100;
    const n = Math.max(1, Math.round(duration * sampleRate));
    return { tag: "audio.buffer", samples: new Array(n).fill(0), sampleRate: sampleRate };
  };
  audio.sample = function (buffer, index) {
    if (index < 0 || index >= buffer.samples.length) return 0;
    return buffer.samples[index];
  };
  audio.mix = function (a, b) {
    const n = Math.max(a.samples.length, b.samples.length);
    const samples = new Array(n);
    for (let i = 0; i < n; i++) {
      samples[i] = (a.samples[i] || 0) + (b.samples[i] || 0);
    }
    return { tag: "audio.buffer", samples: samples, sampleRate: a.sampleRate || b.sampleRate || 44100 };
  };
  audio.append = function (a, b) {
    return { tag: "audio.buffer", samples: a.samples.concat(b.samples), sampleRate: a.sampleRate || 44100 };
  };
  audio.gain = function (buffer, factor) {
    const samples = buffer.samples.map((s) => s * factor);
    return { tag: "audio.buffer", samples: samples, sampleRate: buffer.sampleRate || 44100 };
  };
  audio.duration = function (buffer) {
    const rate = buffer.sampleRate || 44100;
    return buffer.samples.length / rate;
  };
  audio.length = function (buffer) {
    return buffer.samples.length;
  };

  audio.encode_wav = function (buffer) {
    const samples = buffer.samples;
    const sampleRate = buffer.sampleRate || 44100;
    const bytesPerSample = 2;
    const blockAlign = 1 * bytesPerSample;
    const dataSize = samples.length * bytesPerSample;
    const bufferSize = 44 + dataSize;
    const out = new Uint8Array(bufferSize);
    const view = new DataView(out.buffer);
    function writeString(offset, text) {
      for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
    }
    writeString(0, "RIFF");
    view.setUint32(4, bufferSize - 8, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, dataSize, true);
    for (let i = 0; i < samples.length; i++) {
      const v = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(44 + i * 2, Math.round(v * 32767), true);
    }
    let binary = "";
    for (const b of out) binary += String.fromCharCode(b);
    if (typeof btoa === "function") return btoa(binary);
    return Buffer.from(binary, "binary").toString("base64");
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);