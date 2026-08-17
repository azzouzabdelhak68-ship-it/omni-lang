/* OmniScript Visual Editor (v5.2)
 *
 * Block-based visual editor: drag blocks from the palette onto the canvas,
 * configure their fields, and generate OmniScript source.
 *
 * `renderOmni(blocks)` is the pure, Node-testable core: it converts an array
 * of block records into OmniScript source. `blockToOmni` renders a single
 * (possibly nested) block. Both are exported via a UMD-style wrapper so the
 * module can be required from Node and the browser alike.
 */

(function (root, factory) {
  var api = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  if (root) {
    root.renderOmni = api.renderOmni;
    root.blockToOmni = api.blockToOmni;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function blockToOmni(b, n) {
    var pad = "    ".repeat(n);
    switch (b.type) {
      case "assign":
        return pad + b.name + " = " + b.value;
      case "show":
        return pad + "show " + b.value;
      case "return":
        return pad + "return " + b.value;
      case "call":
        return pad + b.call;
      case "break":
        return pad + "break";
      case "continue":
        return pad + "continue";
      case "if": {
        var out = pad + "if " + b.cond + ":";
        out += "\n" + (b.body || []).map(function (x) { return blockToOmni(x, n + 1); }).join("\n");
        if (b.elseBody && b.elseBody.length) {
          out += "\n" + pad + "else:";
          out += "\n" + b.elseBody.map(function (x) { return blockToOmni(x, n + 1); }).join("\n");
        }
        out += "\n" + pad + "end";
        return out;
      }
      case "for": {
        var loop = pad + "for " + b.variable + " in " + b.iterable + ":";
        loop += "\n" + (b.body || []).map(function (x) { return blockToOmni(x, n + 1); }).join("\n");
        loop += "\n" + pad + "end";
        return loop;
      }
      case "fn": {
        var fn = pad + "fn " + b.name + "(" + b.params + ") -> " + b.ret + ":";
        fn += "\n" + pad + "    pure";
        var body = (b.body || []).map(function (x) { return blockToOmni(x, n + 1); }).join("\n");
        if (body) {
          fn += "\n" + body;
        }
        fn += "\n" + pad + "end";
        return fn;
      }
      default:
        return "";
    }
  }

  function renderOmni(blocks) {
    var fns = blocks.filter(function (b) { return b.type === "fn"; });
    var app = blocks.filter(function (b) { return b.type !== "fn"; });
    var lines = [];

    if (fns.length) {
      lines.push(fns.map(function (b) { return blockToOmni(b, 0); }).join("\n\n"));
    }
    lines.push("when app starts:");
    lines.push(app.map(function (b) { return blockToOmni(b, 1); }).join("\n"));
    lines.push("end");

    var slot = null;
    for (var i = 0; i < app.length; i++) {
      if (app[i].type === "assign") {
        slot = app[i].name;
        break;
      }
    }
    lines.push("");
    lines.push("UI:");
    lines.push(slot ? "<h1>{" + slot + "}</h1>" : "<p>OmniScript app</p>");
    lines.push("end");
    return lines.join("\n");
  }

  /* ---- browser editor ---- */

  function initEditor() {
    var rootEl = document.getElementById("root");
    var codeArea = document.getElementById("omni-code");
    var statusEl = document.getElementById("status");
    var generateBtn = document.getElementById("generate-btn");
    var clearBtn = document.getElementById("clear-btn");

    var state = [];
    var dragType = null;

    document.querySelectorAll("#palette .chip").forEach(function (chip) {
      chip.addEventListener("dragstart", function (ev) {
        dragType = chip.getAttribute("data-type");
        if (ev.dataTransfer) {
          ev.dataTransfer.setData("text/plain", dragType);
        }
      });
    });

    function makeBlock(type) {
      switch (type) {
        case "assign":
          return { type: "assign", name: "x", value: "0" };
        case "show":
          return { type: "show", value: "x" };
        case "call":
          return { type: "call", call: "log()" };
        case "return":
          return { type: "return", value: "x" };
        case "if":
          return { type: "if", cond: "x greater than 0", body: [], elseBody: [] };
        case "for":
          return { type: "for", variable: "n", iterable: "items", body: [] };
        case "fn":
          return { type: "fn", name: "f", params: "a: Number", ret: "Number", body: [] };
        case "break":
          return { type: "break" };
        case "continue":
          return { type: "continue" };
        default:
          return { type: "assign", name: "x", value: "0" };
      }
    }

    function dropTarget(el, onDrop) {
      el.addEventListener("dragover", function (ev) {
        ev.preventDefault();
        if (ev.dataTransfer) {
          ev.dataTransfer.dropEffect = "copy";
        }
        el.classList.add("drop-hover");
      });
      el.addEventListener("dragleave", function () {
        el.classList.remove("drop-hover");
      });
      el.addEventListener("drop", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        el.classList.remove("drop-hover");
        var type = ev.dataTransfer ? ev.dataTransfer.getData("text/plain") : dragType;
        if (!type) {
          type = dragType;
        }
        onDrop(type);
      });
    }

    function fieldsFor(b) {
      var fields = [];
      function add(label, key) {
        fields.push({ label: label, key: key });
      }
      switch (b.type) {
        case "assign":
          add("Name", "name");
          add("Value", "value");
          break;
        case "show":
          add("Value", "value");
          break;
        case "call":
          add("Call", "call");
          break;
        case "return":
          add("Value", "value");
          break;
        case "if":
          add("Condition", "cond");
          break;
        case "for":
          add("Variable", "variable");
          add("Iterable", "iterable");
          break;
        case "fn":
          add("Name", "name");
          add("Params", "params");
          add("Return", "ret");
          break;
      }
      return fields;
    }

    function dropzoneFor(arr, isElse) {
      var dz = document.createElement("div");
      dz.className = "dropzone" + (isElse ? " else" : "");
      dz.textContent = isElse ? "+ drop else block" : "+ drop nested block";
      dropTarget(dz, function (type) {
        arr.push(makeBlock(type));
        render();
      });
      return dz;
    }

    function cardFor(b, arr) {
      var card = document.createElement("div");
      card.className = "card type-" + b.type;
      card.setAttribute("data-block", b.type);

      var head = document.createElement("div");
      head.className = "card-head";
      var title = document.createElement("span");
      title.className = "card-title";
      title.textContent = b.type;
      var rm = document.createElement("button");
      rm.type = "button";
      rm.textContent = "\u00d7";
      rm.className = "remove";
      rm.title = "Remove block";
      rm.addEventListener("click", function () {
        var i = arr.indexOf(b);
        if (i >= 0) {
          arr.splice(i, 1);
        }
        render();
      });
      head.appendChild(title);
      head.appendChild(rm);
      card.appendChild(head);

      var bodyEl = document.createElement("div");
      bodyEl.className = "card-body";
      fieldsFor(b).forEach(function (f) {
        var label = document.createElement("label");
        label.className = "field";
        var span = document.createElement("span");
        span.textContent = f.label;
        var input = document.createElement("input");
        input.type = "text";
        input.value = b[f.key] || "";
        input.addEventListener("input", function () {
          b[f.key] = input.value;
          renderCode();
        });
        label.appendChild(span);
        label.appendChild(input);
        bodyEl.appendChild(label);
      });
      card.appendChild(bodyEl);

      if (b.type === "if" || b.type === "for" || b.type === "fn") {
        var wrap = document.createElement("div");
        wrap.className = "nested";
        b.body.forEach(function (child) {
          wrap.appendChild(cardFor(child, b.body));
        });
        wrap.appendChild(dropzoneFor(b.body));
        card.appendChild(wrap);
      }
      if (b.type === "if") {
        var ewrap = document.createElement("div");
        ewrap.className = "nested else";
        b.elseBody.forEach(function (child) {
          ewrap.appendChild(cardFor(child, b.elseBody));
        });
        ewrap.appendChild(dropzoneFor(b.elseBody, true));
        card.appendChild(ewrap);
      }
      return card;
    }

    function renderCode() {
      var omni = renderOmni(state);
      codeArea.value = omni;
      statusEl.textContent = state.length
        ? state.length + " block(s) - generated " + omni.length + " chars"
        : "Add a block to begin.";
    }

    function render() {
      rootEl.innerHTML = "";
      if (!state.length) {
        rootEl.classList.add("empty");
        rootEl.textContent = "Drag a block here to start your OmniScript program.";
        renderCode();
        return;
      }
      rootEl.classList.remove("empty");
      state.forEach(function (b) {
        rootEl.appendChild(cardFor(b, state));
      });
      renderCode();
    }

    dropTarget(rootEl, function (type) {
      state.push(makeBlock(type));
      render();
    });

    generateBtn.addEventListener("click", function () {
      renderCode();
      codeArea.focus();
      codeArea.select();
    });

    clearBtn.addEventListener("click", function () {
      state = [];
      render();
    });

    render();
  }

  if (typeof document !== "undefined") {
    initEditor();
  }

  return {
    renderOmni: renderOmni,
    blockToOmni: blockToOmni
  };
});
