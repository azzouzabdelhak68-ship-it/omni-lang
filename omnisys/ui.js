"use strict";
/**
 * OMNISYS.ui — portable semantic UI model (SwiftUI/WPF/Qt/web principles
 * synthesized, never wrapped). Elements are JSON trees that render to HTML
 * or a serializable DOM; the reference lane is the browser, tests run the
 * serialization lane in Node.
 */
(function (root) {
  const omnisys = (root.omnisys = root.omnisys || {});
  const ui = (omnisys.ui = omnisys.ui || {});
  const core = omnisys.core;

  ui.element = function (kind, attrs, children) {
    return { tag: "element", kind: String(kind), attrs: attrs || {}, children: children || [] };
  };
  ui.text = function (content) {
    return { tag: "text", content: String(content) };
  };
  ui.button = function (label, action) {
    return {
      tag: "element",
      kind: "button",
      attrs: {},
      children: [ui.text(label)],
      action: typeof action === "function" ? action : null,
    };
  };
  ui.row = function (children) {
    return ui.element("row", {}, children);
  };
  ui.column = function (children) {
    return ui.element("column", {}, children);
  };
  ui.input = function (value, placeholder) {
    return ui.element("input", { value: String(value), placeholder: String(placeholder) }, []);
  };
  ui.bind = function (element, slot, value) {
    const out = JSON.parse(JSON.stringify(element));
    out.attrs = out.attrs || {};
    out.attrs[String(slot)] = value;
    return out;
  };
  ui.state = function (value) {
    return { tag: "state", value: value, _onChange: null };
  };
  ui.state_get = function (state) {
    return state.value;
  };
  ui.state_set = function (state, value) {
    state.value = value;
    if (typeof state._onChange === "function") {
      state._onChange();
    }
    return state;
  };
  ui.state_on_change = function (state, callback) {
    state._onChange = callback;
  };

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function attrsToHtml(attrs) {
    let out = "";
    for (const key of Object.keys(attrs || {})) {
      if (key === "value" || key === "placeholder" || key === "class" || key === "id") {
        out += ' ' + key + '="' + escapeHtml(attrs[key]) + '"';
      }
    }
    return out;
  }

  function elementToHtml(node) {
    if (!node) return "";
    if (node.tag === "text") return escapeHtml(node.content);
    const kind = node.kind || "div";
    if (kind === "row" || kind === "column") {
      const style = kind === "row" ? ' style="display:flex;flex-direction:row"' : ' style="display:flex;flex-direction:column"';
      return "<div" + style + ">" + node.children.map(elementToHtml).join("") + "</div>";
    }
    if (kind === "button") {
      return '<button' + attrsToHtml(node.attrs) + '>' + node.children.map(elementToHtml).join("") + "</button>";
    }
    if (kind === "input") {
      return "<input" + attrsToHtml(node.attrs) + " />";
    }
    return "<" + kind + attrsToHtml(node.attrs) + ">" + node.children.map(elementToHtml).join("") + "</" + kind + ">";
  }

  ui.render = function (element) {
    return elementToHtml(element);
  };
  ui.to_html = ui.render;

  ui.get_value = function (id) {
    if (typeof document === "undefined") return "";
    const el = document.getElementById(String(id));
    return el ? String(el.value != null ? el.value : el.textContent) : "";
  };

  ui.get_form_data = function (id) {
    const form = typeof document !== "undefined" ? document.getElementById(String(id)) : null;
    const out = {};
    if (!form) return out;
    const elements = form.elements || form.querySelectorAll("input,select,textarea,button");
    for (const el of elements) {
      if (!el.name) continue;
      if (el.type === "checkbox") out[el.name] = !!el.checked;
      else if (el.type === "radio") {
        if (el.checked) out[el.name] = String(el.value);
      } else if (el.tagName === "BUTTON") {
        continue;
      } else {
        out[el.name] = String(el.value != null ? el.value : "");
      }
    }
    return out;
  };
})(typeof globalThis !== "undefined" ? globalThis : typeof self !== "undefined" ? self : this);