"use strict";
/**
 * OMNISYS.scene — portable 3D scene graph. Nodes carry transforms (position,
 * rotation, scale) and kinds (mesh/camera/light). Pure tree model; snapshot()
 * returns a JSON serializable scene. Hardware renderers are escapes.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const scene = (omnisys.scene = omnisys.scene || {});
  const core = omnisys.core;

  scene.new_scene = function () {
    return { tag: "scene", nodes: {}, order: [], nextId: 1 };
  };

  function nodeBase(id, kind) {
    return {
      id: id,
      kind: kind,
      children: [],
      transform: { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] },
    };
  }

  function ensureNode(s, id, kind) {
    if (!s.nodes[id]) {
      s.nodes[id] = nodeBase(id, kind);
      s.order.push(id);
    }
    return s.nodes[id];
  }

  scene.node = function (s, id) {
    return ensureNode(s, String(id), "group");
  };
  scene.mesh = function (s, id, geometry) {
    const node = ensureNode(s, String(id), "mesh");
    node.geometry = String(geometry);
    return node;
  };
  scene.camera = function (s, id) {
    return ensureNode(s, String(id), "camera");
  };
  scene.light = function (s, id, kind) {
    const node = ensureNode(s, String(id), "light");
    node.lightType = String(kind || "directional");
    return node;
  };
  scene.add = function (s, parent, child) {
    const parentNode = s.nodes[parent];
    if (!parentNode) core.panic("scene.add: unknown parent " + parent);
    const childNode = ensureNode(s, child, "group");
    if (parentNode.children.indexOf(child) === -1) parentNode.children.push(child);
    return s;
  };
  scene.transform = function (s, id, attrs) {
    const node = s.nodes[id];
    if (!node) core.panic("scene.transform: unknown node " + id);
    if (attrs.position) node.transform.position = attrs.position;
    if (attrs.rotation) node.transform.rotation = attrs.rotation;
    if (attrs.scale) node.transform.scale = attrs.scale;
    return s;
  };
  scene.remove = function (s, id) {
    delete s.nodes[id];
    s.order = s.order.filter((x) => x !== id);
    return s;
  };
  scene.snapshot = function (s) {
    return JSON.parse(JSON.stringify({ nodes: s.nodes, order: s.order }));
  };
  scene.update = function (s, dt) {
    // Deterministic placeholder: propagate transforms to children.
    for (const id of s.order) {
      const node = s.nodes[id];
      if (node) node._elapsed = (node._elapsed || 0) + dt;
    }
    return s;
  };
  scene.to_json = scene.snapshot;
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);