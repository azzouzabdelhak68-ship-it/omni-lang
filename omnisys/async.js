"use strict";
/**
 * OMNISYS.async — Task/Future/Stream-style concurrency primitives.
 * The portable core wraps Promise with a tagged Task value. Real backends
 * (JS lane) are promise-based; the OmniScript surface is synchronous, so
 * these return Task values consumed by runtime tooling.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const asyncModule = (omnisys.async = omnisys.async || {});

  // Task wrapper: a Promise with a cancel method for timer-based tasks
  function makeTask(promise, cancelFn) {
    const task = promise;
    task.cancel = cancelFn;
    task.tag = "task";
    return task;
  }

  asyncModule.task = function (fn) {
    return makeTask(Promise.resolve().then(() => fn()), () => {});
  };
  asyncModule.delay = function (ms) {
    return makeTask(new Promise((resolve) => setTimeout(resolve, ms)), () => {});
  };
  asyncModule.interval = function (ms, fn) {
    const id = setInterval(fn, ms);
    return makeTask(Promise.resolve(id), () => clearInterval(id));
  };
  asyncModule.timeout = function (ms, fn) {
    const id = setTimeout(fn, ms);
    return makeTask(Promise.resolve(id), () => clearTimeout(id));
  };
  asyncModule.tick = function (fn) {
    const id = requestAnimationFrame(fn);
    return makeTask(Promise.resolve(id), () => cancelAnimationFrame(id));
  };
  asyncModule.cancel = function (task) {
    if (task && typeof task.cancel === "function") {
      task.cancel();
    }
  };
  asyncModule.await = function (task) {
    return Promise.resolve(task);
  };
  asyncModule.all = function (tasks) {
    return Promise.all(tasks);
  };
  asyncModule.race = function (tasks) {
    return Promise.race(tasks);
  };
  asyncModule.any = function (tasks) {
    return Promise.any(tasks);
  };
  asyncModule.with_timeout = function (task, ms) {
    return Promise.race([
      task,
      new Promise((_, reject) => setTimeout(() => reject(new Error("omnisys.async.timeout")), ms)),
    ]);
  };

  // Channel: bounded FIFO. send/recv return Tasks (promises).
  asyncModule.channel = function (capacity) {
    const buf = [];
    const waiters = [];
    return {
      tag: "channel",
      capacity: capacity,
      send: (value) => {
        if (buf.length >= capacity) {
          return new Promise((resolve) => waiters.push({ kind: "send", value: value, resolve: resolve }));
        }
        buf.push(value);
        return Promise.resolve();
      },
      recv: () => {
        if (buf.length > 0) {
          return Promise.resolve(buf.shift());
        }
        return new Promise((resolve) => waiters.push({ kind: "recv", resolve: resolve }));
      },
      size: () => buf.length,
    };
  };
  asyncModule.channel_send = function (channel, value) {
    return channel.send(value);
  };
  asyncModule.channel_recv = function (channel) {
    return channel.recv();
  };
  asyncModule.is_promise = function (x) {
    return !!(x && typeof x.then === "function");
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);