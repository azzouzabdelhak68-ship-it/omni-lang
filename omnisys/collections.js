"use strict";
/**
 * OMNISYS.collections — List / Map / Set / Deque / Heap / RingBuffer.
 * Pure operations on JSON-friendly values (arrays, objects, arrays-as-sets).
 * Deque/Heap/RingBuffer values are plain objects tagged for introspection.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const collections = (omnisys.collections = omnisys.collections || {});
  const core = omnisys.core;

  function panic(msg) {
    core.panic("collections." + msg);
  }

  // ---- List --------------------------------------------------------------
  collections.list_push = function (list, item) {
    list.push(item);
    return list;
  };
  collections.list_pop = function (list) {
    if (list.length === 0) panic("list_pop on empty list");
    return list.pop();
  };
  collections.list_get = function (list, index) {
    if (index < 0 || index >= list.length) panic("list_get index out of range");
    return list[index];
  };
  collections.list_set = function (list, index, value) {
    if (index < 0 || index >= list.length) panic("list_set index out of range");
    list[index] = value;
    return list;
  };
  collections.list_slice = function (list, start, end) {
    return list.slice(start, end);
  };
  collections.list_append = function (a, b) {
    return a.concat(b);
  };
  collections.list_contains = function (list, item) {
    return list.indexOf(item) !== -1;
  };
  collections.list_index_of = function (list, item) {
    return list.indexOf(item);
  };
  collections.list_remove = function (list, index) {
    if (index < 0 || index >= list.length) panic("list_remove index out of range");
    list.splice(index, 1);
    return list;
  };
  collections.list_sort = function (list) {
    return list.slice().sort((a, b) => a - b);
  };
  collections.list_reverse = function (list) {
    return list.slice().reverse();
  };
  collections.list_fold = function (list, fn, init) {
    let acc = init;
    for (let i = 0; i < list.length; i++) {
      acc = fn(acc, list[i]);
    }
    return acc;
  };
  collections.list_map = function (list, fn) {
    return list.map(fn);
  };
  collections.list_filter = function (list, fn) {
    return list.filter(fn);
  };
  collections.list_join = function (list, sep) {
    return list.map(String).join(sep);
  };
  collections.list_zip = function (a, b) {
    const n = Math.min(a.length, b.length);
    const out = [];
    for (let i = 0; i < n; i++) out.push([a[i], b[i]]);
    return out;
  };

  // ---- Map (plain object) ------------------------------------------------
  collections.map_get = function (map, key) {
    return map[String(key)];
  };
  collections.map_set = function (map, key, value) {
    map[String(key)] = value;
    return map;
  };
  collections.map_remove = function (map, key) {
    delete map[String(key)];
    return map;
  };
  collections.map_has = function (map, key) {
    return Object.prototype.hasOwnProperty.call(map, String(key));
  };
  collections.map_keys = function (map) {
    return Object.keys(map);
  };
  collections.map_values = function (map) {
    return Object.keys(map).map((k) => map[k]);
  };
  collections.map_size = function (map) {
    return Object.keys(map).length;
  };

  // ---- Set (array with unique items) -------------------------------------
  collections.set_add = function (set, item) {
    if (set.indexOf(item) === -1) set.push(item);
    return set;
  };
  collections.set_remove = function (set, item) {
    const i = set.indexOf(item);
    if (i !== -1) set.splice(i, 1);
    return set;
  };
  collections.set_has = function (set, item) {
    return set.indexOf(item) !== -1;
  };
  collections.set_size = function (set) {
    return set.length;
  };
  collections.set_union = function (a, b) {
    const out = a.slice();
    for (const item of b) {
      if (out.indexOf(item) === -1) out.push(item);
    }
    return out;
  };
  collections.set_intersection = function (a, b) {
    return a.filter((item) => b.indexOf(item) !== -1);
  };
  collections.set_difference = function (a, b) {
    return a.filter((item) => b.indexOf(item) === -1);
  };

  // ---- Deque -------------------------------------------------------------
  collections.deque_push_front = function (deque, item) {
    deque.items.unshift(item);
    return deque;
  };
  collections.deque_push_back = function (deque, item) {
    deque.items.push(item);
    return deque;
  };
  collections.deque_pop_front = function (deque) {
    if (deque.items.length === 0) panic("deque_pop_front on empty deque");
    return deque.items.shift();
  };
  collections.deque_pop_back = function (deque) {
    if (deque.items.length === 0) panic("deque_pop_back on empty deque");
    return deque.items.pop();
  };
  collections.deque_size = function (deque) {
    return deque.items.length;
  };

  // ---- Heap (min-heap) ---------------------------------------------------
  collections.heap_push = function (heap, item) {
    heap.items.push(item);
    let i = heap.items.length - 1;
    while (i > 0) {
      const parent = Math.floor((i - 1) / 2);
      if (heap.items[parent] <= heap.items[i]) break;
      [heap.items[parent], heap.items[i]] = [heap.items[i], heap.items[parent]];
      i = parent;
    }
    return heap;
  };
  collections.heap_pop = function (heap) {
    if (heap.items.length === 0) panic("heap_pop on empty heap");
    const top = heap.items[0];
    const last = heap.items.pop();
    if (heap.items.length > 0) {
      heap.items[0] = last;
      let i = 0;
      for (;;) {
        const left = 2 * i + 1;
        const right = 2 * i + 2;
        let smallest = i;
        if (left < heap.items.length && heap.items[left] < heap.items[smallest]) smallest = left;
        if (right < heap.items.length && heap.items[right] < heap.items[smallest]) smallest = right;
        if (smallest === i) break;
        [heap.items[smallest], heap.items[i]] = [heap.items[i], heap.items[smallest]];
        i = smallest;
      }
    }
    return top;
  };
  collections.heap_peek = function (heap) {
    if (heap.items.length === 0) panic("heap_peek on empty heap");
    return heap.items[0];
  };
  collections.heap_size = function (heap) {
    return heap.items.length;
  };

  // ---- RingBuffer --------------------------------------------------------
  collections.ring_new = function (capacity) {
    return { tag: "ring", capacity: capacity, items: [] };
  };
  collections.ring_push = function (ring, item) {
    ring.items.push(item);
    if (ring.items.length > ring.capacity) ring.items.shift();
    return ring;
  };
  collections.ring_pop = function (ring) {
    if (ring.items.length === 0) panic("ring_pop on empty ring");
    return ring.items.shift();
  };
  collections.ring_size = function (ring) {
    return ring.items.length;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);