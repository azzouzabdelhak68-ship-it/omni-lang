"use strict";
/**
 * OMNISYS.sim — ECS/simulation semantic model (portable). Entities hold
 * component maps; systems run deterministically per step; queries select
 * entities by component. Also bridges to the v5.3 sim.actor distributed
 * runtime (`omnisys.sim.actor`) when running under Node.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const sim = (omnisys.sim = omnisys.sim || {});
  const core = omnisys.core;

  sim.world = function () {
    return { tag: "world", entities: {}, order: [], systems: [], step: 0 };
  };
  sim.entity = function (world, name) {
    if (!world.entities[name]) {
      world.entities[name] = { tag: "entity", name: name, components: {} };
      world.order.push(name);
    }
    return world.entities[name];
  };
  sim.component = function (world, name, component, value) {
    const entity = sim.entity(world, name);
    entity.components[String(component)] = value;
    return world;
  };
  sim.get = function (world, name, component) {
    const entity = world.entities[name];
    if (!entity) core.panic("sim.get: unknown entity " + name);
    return entity.components[String(component)];
  };
  sim.system = function (world, fn) {
    world.systems.push(fn);
    return world;
  };
  sim.run = function (world, steps) {
    const n = Math.max(0, steps | 0);
    for (let i = 0; i < n; i++) {
      for (const system of world.systems) {
        system(world);
      }
      world.step++;
    }
    return world;
  };
  sim.query = function (world, component) {
    return world.order.filter((name) => {
      const entity = world.entities[name];
      return entity && Object.prototype.hasOwnProperty.call(entity.components, String(component));
    });
  };
  sim.remove_entity = function (world, name) {
    delete world.entities[name];
    world.order = world.order.filter((x) => x !== name);
    return world;
  };
  sim.entities = function (world) {
    return world.order.slice();
  };
  sim.snapshot = function (world) {
    return {
      tag: "world",
      step: world.step,
      entities: JSON.parse(JSON.stringify(world.entities)),
      order: world.order.slice(),
    };
  };

  // Bridge to the v5.3 sim.actor distributed runtime when available.
  try {
    if (typeof require !== "undefined") {
      const { createRuntime } = require("../simulation_engine/runtime.js");
      sim.actor = createRuntime().sim.actor;
    }
  } catch (e) {
    sim.actor = null;
  }
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);