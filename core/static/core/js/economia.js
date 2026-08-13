/* =========================================================================
   Graficos del analisis economico.
   ========================================================================= */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }
  function pinta(id, svg) { var el = $(id); if (el) el.innerHTML = svg; }

  var el = $("seriesJson");
  if (!el) return;
  var S = JSON.parse(el.textContent);
  var filas = S.filas || [];
  var A = 560, B = 320;

  /* ------------------------------------------------ precio historico ---- */
  if (S.precio_hist && S.precio_hist.length > 1) {
    var h = S.precio_hist;
    var pts = h.map(function (r, i) { return [i, r[1]]; });
    var vals = h.map(function (r) { return r[1]; });
    var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
    var pad = (hi - lo) * 0.12 || 2;
    pinta("g_precio", BLChart.plot({
      w: 1100, h: 210, pad: { l: 62, r: 20, t: 14, b: 40 },
      xdom: [0, pts.length - 1], ydom: [lo - pad, hi + pad],
      xlab: "Días de mercado (" + h[0][0] + " → " + h[h.length - 1][0] + ")",
      ylab: "USD/bbl", nx: 8,
      areas: [{ pts: pts, color: "var(--brine)", op: 0.10 }],
      series: [{ pts: pts, color: "var(--brine)", w: 1.9 }],
      hlines: [{ y: vals[vals.length - 1], color: "var(--crude)", t: "último " + vals[vals.length - 1].toFixed(2) }]
    }));
  }

  if (!filas.length) return;
  var meses = filas.length;

  function col(clave) {
    return filas.map(function (r) { return [r.mes, r[clave]]; });
  }
  function maxDe(clave) {
    return filas.reduce(function (m, r) { return Math.max(m, r[clave] || 0); }, 0);
  }
  function minDe(clave) {
    return filas.reduce(function (m, r) { return Math.min(m, r[clave] || 0); }, 0);
  }

  /* ------------------------------------------------------- produccion --- */
  pinta("g_prod", BLChart.plot({
    w: A, h: B, xdom: [0, meses], ydom: [0, Math.max(maxDe("qo"), maxDe("qw")) * 1.1],
    xlab: "Mes", ylab: "Caudal (bbl/día)",
    areas: [{ pts: col("qw"), color: "var(--brine)", op: 0.12 }],
    series: [{ pts: col("qo"), color: "var(--crude)", w: 2.3 },
             { pts: col("qw"), color: "var(--brine)", w: 2.3 }],
    labels: [{ x: meses * 0.55, y: maxDe("qw") * 0.95, t: "agua", color: "var(--brine)" },
             { x: meses * 0.15, y: maxDe("qo") * 0.55, t: "petróleo", color: "var(--crude)" }]
  }));

  /* ------------------------------------------------------------ corte --- */
  pinta("g_corte", BLChart.plot({
    w: A, h: B, xdom: [0, meses], ydom: [0, 1],
    xlab: "Mes", ylab: "Corte de agua (fracción)",
    areas: [{ pts: col("corte"), color: "var(--brine)", op: 0.14 }],
    series: [{ pts: col("corte"), color: "var(--brine)", w: 2.4 }],
    hlines: [{ y: 0.9, color: "var(--bad)", t: "90 %" }]
  }));

  /* ------------------------------------------------------- flujo mes ---- */
  var loF = Math.min(minDe("neto"), 0) * 1.15;
  pinta("g_flujo", BLChart.plot({
    w: A, h: B, xdom: [0, meses], ydom: [loF, maxDe("ingreso") * 1.1],
    xlab: "Mes", ylab: "USD por mes",
    series: [{ pts: col("ingreso"), color: "var(--good)", w: 2.1 },
             { pts: col("opex"), color: "var(--bad)", w: 2.1 },
             { pts: col("neto"), color: "var(--ink)", w: 2.4 }],
    hlines: [{ y: 0, color: "var(--faint)", t: "" }],
    labels: [{ x: meses * 0.06, y: maxDe("ingreso") * 0.95, t: "ingreso", color: "var(--good)" },
             { x: meses * 0.06, y: maxDe("ingreso") * 0.83, t: "OPEX", color: "var(--bad)" },
             { x: meses * 0.06, y: maxDe("ingreso") * 0.71, t: "margen", color: "var(--ink)" }]
  }));

  /* --------------------------------------------------------- acumulado -- */
  var loA = Math.min(minDe("acum"), minDe("vpn")) * 1.12;
  pinta("g_acum", BLChart.plot({
    w: A, h: B, xdom: [0, meses],
    ydom: [loA, Math.max(maxDe("acum"), maxDe("vpn"), 0) * 1.12 || 1],
    xlab: "Mes", ylab: "USD acumulados",
    series: [{ pts: col("acum"), color: "var(--crude)", w: 2.3 },
             { pts: col("vpn"), color: "var(--brine)", w: 2.3, dash: "6 4" }],
    hlines: [{ y: 0, color: "var(--ink)", t: "" }],
    labels: [{ x: meses * 0.5, y: maxDe("acum") * 0.6, t: "sin descontar", color: "var(--crude)" },
             { x: meses * 0.5, y: maxDe("acum") * 0.42, t: "VPN", color: "var(--brine)" }]
  }));

  /* ----------------------------------------------------- OPEX por rubro - */
  var d = S.desglose || [];
  if (d.length) {
    var total = d.reduce(function (s, r) { return s + r.monto; }, 0) || 1;
    var W = 520, H = 300, y = 26, alto = 34;
    var g = "";
    d.forEach(function (r) {
      var w = (r.monto / total) * (W - 200);
      g += '<rect x="150" y="' + y + '" width="' + Math.max(w, 1) + '" height="' + (alto - 12) +
        '" fill="' + r.color + '" opacity="0.85" rx="4"/>';
      g += '<text class="ann" x="144" y="' + (y + alto / 2 - 2) + '" text-anchor="end" fill="var(--ink)">' +
        BLChart.esc(r.concepto) + "</text>";
      g += '<text class="ann" x="' + (154 + Math.max(w, 1)) + '" y="' + (y + alto / 2 - 2) + '">' +
        (r.fraccion * 100).toFixed(1) + " % · " + Math.round(r.monto).toLocaleString("es") + " USD</text>";
      y += alto;
    });
    pinta("g_opex", '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Composición del OPEX">' + g + "</svg>");
  }

  /* --------------------------------------------------------- OPEX/bbl --- */
  var ob = filas.filter(function (r) { return r.opex_bbl != null; })
    .map(function (r) { return [r.mes, Math.min(r.opex_bbl, 400)]; });
  if (ob.length) {
    var hiOb = ob.reduce(function (m, p) { return Math.max(m, p[1]); }, 0);
    pinta("g_opexbbl", BLChart.plot({
      w: A, h: B, xdom: [0, meses], ydom: [0, hiOb * 1.1],
      xlab: "Mes", ylab: "OPEX por barril de petróleo (USD/bbl)",
      series: [{ pts: ob, color: "var(--gas)", w: 2.3 }],
      hlines: [{ y: S.precio_neto || 0, color: "var(--bad)", t: "precio neto" }]
    }));
  }
})();
