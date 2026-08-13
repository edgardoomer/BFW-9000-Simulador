/* =========================================================================
   Graficador SVG minimo. Sin dependencias externas.
   Devuelve una cadena SVG lista para insertar con innerHTML.
   ========================================================================= */
(function (global) {
  "use strict";

  function nice(v) {
    var a = Math.abs(v);
    if (a === 0) return "0";
    if (a >= 1e6 || a < 1e-3) return v.toExponential(1);
    if (a >= 1e4) return (v / 1000).toFixed(0) + "k";
    if (a >= 100) return v.toFixed(0);
    if (a >= 10) return v.toFixed(1);
    if (a >= 1) return v.toFixed(2);
    return v.toFixed(3);
  }

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  /* Ejes "bonitos": pasos de 1, 2, 2.5 o 5 por decada. */
  function ticks(lo, hi, n) {
    if (!isFinite(lo) || !isFinite(hi) || hi <= lo) return [lo];
    var span = hi - lo;
    var crudo = span / Math.max(n, 1);
    var mag = Math.pow(10, Math.floor(Math.log10(crudo)));
    var norm = crudo / mag;
    var paso = (norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 2.5 ? 2.5 : norm <= 5 ? 5 : 10) * mag;
    var out = [];
    for (var v = Math.ceil(lo / paso) * paso; v <= hi + paso * 1e-6; v += paso) {
      out.push(Math.abs(v) < paso * 1e-9 ? 0 : v);
    }
    return out.length ? out : [lo, hi];
  }

  function plot(o) {
    var W = o.w || 560, H = o.h || 330;
    var P = Object.assign({ l: 62, r: 20, t: 16, b: 46 }, o.pad || {});
    var x0 = o.xdom[0], x1 = o.xdom[1], y0 = o.ydom[0], y1 = o.ydom[1];
    if (x1 - x0 === 0) x1 = x0 + 1;
    if (y1 - y0 === 0) y1 = y0 + 1;

    var X = function (v) { return P.l + (v - x0) / (x1 - x0) * (W - P.l - P.r); };
    var Y = function (v) { return H - P.b - (v - y0) / (y1 - y0) * (H - P.t - P.b); };
    var cx = function (v) { return Math.min(Math.max(v, x0), x1); };
    var cy = function (v) { return Math.min(Math.max(v, y0), y1); };

    var g = "";

    /* -------- rejilla y marcas -------- */
    var tx = ticks(x0, x1, o.nx || 6), ty = ticks(y0, y1, o.ny || 5);
    tx.forEach(function (v) {
      g += '<line class="grl" x1="' + X(v) + '" y1="' + Y(y0) + '" x2="' + X(v) + '" y2="' + Y(y1) + '"/>';
      g += '<text class="tk" x="' + X(v) + '" y="' + (Y(y0) + 15) + '" text-anchor="middle">' + nice(v) + "</text>";
    });
    ty.forEach(function (v) {
      g += '<line class="grl" x1="' + X(x0) + '" y1="' + Y(v) + '" x2="' + X(x1) + '" y2="' + Y(v) + '"/>';
      g += '<text class="tk" x="' + (X(x0) - 7) + '" y="' + (Y(v) + 3) + '" text-anchor="end">' + nice(v) + "</text>";
    });

    /* -------- areas sombreadas -------- */
    (o.areas || []).forEach(function (a) {
      if (!a.pts || a.pts.length < 2) return;
      var d = a.pts.map(function (q, i) {
        return (i ? "L" : "M") + X(cx(q[0])).toFixed(1) + " " + Y(cy(q[1])).toFixed(1);
      }).join(" ");
      d += " L" + X(cx(a.pts[a.pts.length - 1][0])).toFixed(1) + " " + Y(y0).toFixed(1);
      d += " L" + X(cx(a.pts[0][0])).toFixed(1) + " " + Y(y0).toFixed(1) + " Z";
      g += '<path d="' + d + '" fill="' + a.color + '" opacity="' + (a.op || 0.14) + '"/>';
    });

    /* -------- ejes -------- */
    g += '<line class="axl" x1="' + X(x0) + '" y1="' + Y(y0) + '" x2="' + X(x1) + '" y2="' + Y(y0) + '"/>';
    g += '<line class="axl" x1="' + X(x0) + '" y1="' + Y(y0) + '" x2="' + X(x0) + '" y2="' + Y(y1) + '"/>';
    if (o.xlab) {
      g += '<text class="al" x="' + (X(x0) + X(x1)) / 2 + '" y="' + (H - 10) + '" text-anchor="middle">' + esc(o.xlab) + "</text>";
    }
    if (o.ylab) {
      g += '<text class="al" transform="translate(14,' + (Y(y0) + Y(y1)) / 2 + ') rotate(-90)" text-anchor="middle">' + esc(o.ylab) + "</text>";
    }

    /* -------- barras -------- */
    (o.bars || []).forEach(function (b) {
      var bw = b.w || (W - P.l - P.r) / ((o.bars.length) * 1.6);
      g += '<rect x="' + (X(b.x) - bw / 2) + '" y="' + Y(cy(b.y)) + '" width="' + bw +
        '" height="' + Math.max(Y(y0) - Y(cy(b.y)), 0) + '" fill="' + b.color +
        '" opacity="' + (b.op || 0.85) + '" rx="2"/>';
    });

    /* -------- lineas -------- */
    (o.series || []).forEach(function (s) {
      if (!s.pts || !s.pts.length) return;
      var d = s.pts.map(function (q, i) {
        return (i ? "L" : "M") + X(cx(q[0])).toFixed(1) + " " + Y(cy(q[1])).toFixed(1);
      }).join(" ");
      g += '<path d="' + d + '" fill="none" stroke="' + s.color + '" stroke-width="' + (s.w || 2.1) +
        '" stroke-linecap="round" stroke-linejoin="round"' +
        (s.dash ? ' stroke-dasharray="' + s.dash + '"' : "") +
        (s.op ? ' opacity="' + s.op + '"' : "") + "/>";
    });

    /* -------- referencias -------- */
    (o.vlines || []).forEach(function (v) {
      g += '<line x1="' + X(v.x) + '" y1="' + Y(y0) + '" x2="' + X(v.x) + '" y2="' + Y(y1) +
        '" stroke="' + v.color + '" stroke-dasharray="4 3" stroke-width="1"/>';
      if (v.t) {
        g += '<text class="ann" x="' + (X(v.x) + 4) + '" y="' + (Y(y1) + 10) + '" fill="' + v.color + '">' + esc(v.t) + "</text>";
      }
    });
    (o.hlines || []).forEach(function (v) {
      g += '<line x1="' + X(x0) + '" y1="' + Y(v.y) + '" x2="' + X(x1) + '" y2="' + Y(v.y) +
        '" stroke="' + v.color + '" stroke-dasharray="4 3" stroke-width="1"/>';
      if (v.t) {
        g += '<text class="ann" x="' + (X(x1) - 3) + '" y="' + (Y(v.y) - 4) + '" text-anchor="end" fill="' + v.color + '">' + esc(v.t) + "</text>";
      }
    });

    /* -------- puntos -------- */
    (o.dots || []).forEach(function (p) {
      g += '<circle cx="' + X(cx(p.x)) + '" cy="' + Y(cy(p.y)) + '" r="' + (p.r || 3.4) +
        '" fill="' + p.color + '"' + (p.op ? ' opacity="' + p.op + '"' : "") + "/>";
    });
    (o.rings || []).forEach(function (p) {
      g += '<circle cx="' + X(cx(p.x)) + '" cy="' + Y(cy(p.y)) + '" r="' + (p.r || 5.5) +
        '" fill="' + (p.fill || "var(--panel)") + '" stroke="' + p.color + '" stroke-width="1.9"/>';
    });

    /* -------- etiquetas -------- */
    (o.labels || []).forEach(function (l) {
      g += '<text class="ann" x="' + X(cx(l.x)) + '" y="' + Y(cy(l.y)) + '" fill="' + (l.color || "var(--soft)") +
        '" text-anchor="' + (l.a || "start") + '">' + esc(l.t) + "</text>";
    });

    return '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' +
      esc(o.alt || o.ylab || "gráfico") + '">' + g + "</svg>";
  }

  global.BLChart = { plot: plot, nice: nice, ticks: ticks, esc: esc };
})(window);
