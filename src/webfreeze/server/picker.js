/* webfreeze picker bootstrap (HP2).
 * Injected into the preview iframe. Same-origin, but communicates with the
 * parent via postMessage. Marks selected elements with data-wf-keep; overlay
 * boxes carry data-wf-ui so they (and this script) are stripped before export.
 */
(function () {
  "use strict";
  if (window.__wfPicker) return;

  var picking = false;
  var uid = 0;
  var selected = new Set(); // elements carrying data-wf-keep
  var current = null; // focus element for parent/child navigation
  var hovered = null;
  var hoverBox = null;
  var selBoxes = [];

  function isUi(el) {
    return !el || (el.getAttribute && el.getAttribute("data-wf-ui") != null);
  }

  function makeBox(border, bg, z) {
    var b = document.createElement("div");
    b.setAttribute("data-wf-ui", "box");
    var s = b.style;
    s.position = "fixed";
    s.pointerEvents = "none";
    s.zIndex = String(z);
    s.border = "2px solid " + border;
    s.background = bg;
    s.borderRadius = "2px";
    s.boxSizing = "border-box";
    s.display = "none";
    document.documentElement.appendChild(b);
    return b;
  }

  function position(box, el) {
    var r = el.getBoundingClientRect();
    var s = box.style;
    s.left = r.left + "px";
    s.top = r.top + "px";
    s.width = r.width + "px";
    s.height = r.height + "px";
    s.display = "block";
  }

  function firstChildEl(el) {
    var c = el.firstElementChild;
    while (c && isUi(c)) c = c.nextElementSibling;
    return c;
  }

  function mark(el) {
    if (!el || isUi(el)) return;
    if (!el.hasAttribute("data-wf-keep")) {
      el.setAttribute("data-wf-keep", "wf" + ++uid);
      selected.add(el);
    }
    current = el;
  }

  function unmark(el) {
    if (!el) return;
    el.removeAttribute("data-wf-keep");
    selected.delete(el);
    if (current === el) {
      var arr = Array.from(selected);
      current = arr.length ? arr[arr.length - 1] : null;
    }
  }

  function toggle(el) {
    if (!el || isUi(el)) return;
    if (el.hasAttribute("data-wf-keep")) unmark(el);
    else mark(el);
  }

  function clearAll() {
    selected.forEach(function (el) {
      el.removeAttribute("data-wf-keep");
    });
    selected.clear();
    current = null;
  }

  function moveFocus(toParent) {
    if (!current) return;
    var next = toParent ? current.parentElement : firstChildEl(current);
    if (!next || next === document.documentElement || isUi(next)) return;
    var wasMarked = current.hasAttribute("data-wf-keep");
    if (wasMarked) unmark(current);
    mark(next);
  }

  function describe(el) {
    if (!el) return null;
    var depth = 0;
    var p = el;
    while (p.parentElement) {
      depth++;
      p = p.parentElement;
    }
    var crumb = [];
    p = el;
    while (p && p !== document.documentElement) {
      var t = p.tagName.toLowerCase();
      if (p.id) t += "#" + p.id;
      else if (typeof p.className === "string" && p.className.trim()) {
        t += "." + p.className.trim().split(/\s+/).slice(0, 2).join(".");
      }
      crumb.unshift(t);
      p = p.parentElement;
    }
    return {
      tag: el.tagName.toLowerCase(),
      depth: depth,
      breadcrumb: crumb.join(" > "),
    };
  }

  function syncBoxes() {
    while (selBoxes.length < selected.size) {
      selBoxes.push(makeBox("#10b981", "rgba(16,185,129,0.14)", 2147483645));
    }
    var arr = Array.from(selected);
    selBoxes.forEach(function (b, i) {
      if (i < arr.length) position(b, arr[i]);
      else b.style.display = "none";
    });
  }

  function post(type, extra) {
    var msg = { type: type };
    if (extra) for (var k in extra) msg[k] = extra[k];
    try {
      window.parent.postMessage(msg, "*");
    } catch (e) {}
  }

  function notify() {
    syncBoxes();
    post("wf-selection", { count: selected.size, current: describe(current) });
  }

  function setPicking(on) {
    picking = on;
    if (!on && hoverBox) hoverBox.style.display = "none";
    document.documentElement.style.cursor = on ? "crosshair" : "";
  }

  function stripUi() {
    var nodes = document.querySelectorAll("[data-wf-ui]");
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].parentNode) nodes[i].parentNode.removeChild(nodes[i]);
    }
    hoverBox = null;
    selBoxes = [];
  }

  document.addEventListener(
    "mousemove",
    function (e) {
      if (!picking) return;
      var el = document.elementFromPoint(e.clientX, e.clientY);
      if (isUi(el) || !el) return;
      hovered = el;
      if (!hoverBox) hoverBox = makeBox("#2563eb", "rgba(37,99,235,0.12)", 2147483646);
      position(hoverBox, el);
    },
    true,
  );

  document.addEventListener(
    "click",
    function (e) {
      if (!picking) return;
      var el = document.elementFromPoint(e.clientX, e.clientY);
      if (isUi(el) || !el) return;
      e.preventDefault();
      e.stopPropagation();
      toggle(el);
      notify();
    },
    true,
  );

  function reposition() {
    if (picking && hovered && hoverBox) position(hoverBox, hovered);
    syncBoxes();
  }
  window.addEventListener("scroll", reposition, true);
  window.addEventListener("resize", reposition, true);

  window.addEventListener("message", function (e) {
    var d = e.data || {};
    switch (d.type) {
      case "wf-pickmode":
        setPicking(!!d.on);
        break;
      case "wf-select-parent":
        moveFocus(true);
        notify();
        break;
      case "wf-select-child":
        moveFocus(false);
        notify();
        break;
      case "wf-clear":
        clearAll();
        notify();
        break;
      case "wf-grab-dom":
        stripUi();
        post("wf-dom", {
          html: "<!DOCTYPE html>\n" + document.documentElement.outerHTML,
        });
        break;
    }
  });

  window.__wfPicker = true;
  post("wf-ready", {});
})();
