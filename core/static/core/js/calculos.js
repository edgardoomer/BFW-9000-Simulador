/* =========================================================================
   Graficos de la ficha de calculos por pozo.
   ========================================================================= */
(function (global) {
  "use strict";

  function $(id) { return document.getElementById(id); }
  function leer(id) {
    var el = $(id);
    if (!el) return null;
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }
  function pinta(id, svg) { var el = $(id); if (el) el.innerHTML = svg; }
  function maxY(pts, i) {
    return pts.reduce(function (m, p) { return Math.max(m, p[i]); }, 0);
  }

  /* ------------------------------------------------- inyector: polar ---- */
  function polar(campo) {
    var el = $("polar");
    if (!el || !campo || !campo.th || !campo.th.length) return;
    var W = 560, H = 470, cx = W / 2, cy = H / 2;
    var rmax = Math.max.apply(null, campo.ru) * 1.12;
    var esc = Math.min(W, H) / 2 - 62;
    var k = esc / rmax;

    var g = '<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="var(--panel2)" stroke="var(--rule)" rx="12"/>';

    /* anillos de referencia */
    for (var i = 1; i <= 4; i++) {
      var rr = rmax * i / 4;
      g += '<circle cx="' + cx + '" cy="' + cy + '" r="' + (rr * k) +
        '" fill="none" stroke="var(--rule)" stroke-width="0.6"/>';
      g += '<text class="tk" x="' + (cx + 3) + '" y="' + (cy - rr * k - 2) + '">' +
        BLChart.nice(rr) + "</text>";
    }
    /* ejes cardinales */
    [[1, 0, "E"], [0, -1, "N"], [-1, 0, "O"], [0, 1, "S"]].forEach(function (d) {
      g += '<line x1="' + cx + '" y1="' + cy + '" x2="' + (cx + d[0] * esc) + '" y2="' + (cy + d[1] * esc) +
        '" stroke="var(--rule)" stroke-width="0.6"/>';
      g += '<text class="al" x="' + (cx + d[0] * (esc + 16)) + '" y="' + (cy + d[1] * (esc + 16) + 4) +
        '" text-anchor="middle">' + d[2] + "</text>";
    });

    /* huella r1(theta) */
    var d = "";
    for (var j = 0; j < campo.th.length; j++) {
      var x = cx + campo.ru[j] * k * Math.cos(campo.th[j]);
      var y = cy - campo.ru[j] * k * Math.sin(campo.th[j]);
      d += (j ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1);
    }
    d += "Z";
    g += '<path d="' + d + '" fill="var(--brine)" opacity="0.28"/>';
    g += '<path d="' + d + '" fill="none" stroke="var(--brine)" stroke-width="1.8"/>';

    /* direcciones de los productores */
    (campo.brazos || []).forEach(function (b) {
      var x = cx + rmax * k * Math.cos(b.azimut);
      var y = cy - rmax * k * Math.sin(b.azimut);
      g += '<line x1="' + cx + '" y1="' + cy + '" x2="' + x + '" y2="' + y +
        '" stroke="var(--crude)" stroke-width="1" stroke-dasharray="3 3"/>';
      g += '<text class="ann" x="' + x + '" y="' + (y - 5) + '" text-anchor="middle" fill="var(--crude)">' +
        BLChart.esc(b.productor) + "</text>";
    });

    g += '<circle cx="' + cx + '" cy="' + cy + '" r="7" fill="var(--good)" stroke="#fff" stroke-width="2"/>';
    g += '<text class="al" x="' + cx + '" y="' + (H - 12) + '" text-anchor="middle">r₁(θ) en ft/√día</text>';

    el.innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Huella angular del inyector">' + g + "</svg>";
  }

  /* ----------------------------------------------- productor: graficos -- */
  function graficos(s, pc) {
    if (!s || !s.fw) return;
    var A = 540, B = 320;

    /* 1 · kr */
    var krw = s.kr.map(function (r) { return [r[0], r[1]]; });
    var kro = s.kr.map(function (r) { return [r[0], r[2]]; });
    var km = Math.max(maxY(krw, 1), maxY(kro, 1)) * 1.1;
    pinta("g_kr", BLChart.plot({
      w: A, h: B, xdom: [0, 1], ydom: [0, km], xlab: "Sw (fracción)", ylab: "kr",
      series: [{ pts: krw, color: "var(--brine)" }, { pts: kro, color: "var(--crude)" }],
      dots: krw.map(function (p) { return { x: p[0], y: p[1], color: "var(--brine)", r: 3 }; })
        .concat(kro.map(function (p) { return { x: p[0], y: p[1], color: "var(--crude)", r: 3 }; }))
        // puntos de la leyenda, dentro del area del grafico
        .concat([{ x: 0.055, y: km * 0.94, color: "var(--crude)", r: 3.6 },
                 { x: 0.055, y: km * 0.845, color: "var(--brine)", r: 3.6 }]),
      labels: [{ x: 0.10, y: km * 0.925, t: "kro", color: "var(--crude)" },
               { x: 0.10, y: km * 0.830, t: "krw", color: "var(--brine)" }]
    }));

    /* 2 · ajuste */
    if (s.ajuste && s.ajuste.length) {
      var ys = s.ajuste.map(function (p) { return p[1]; });
      var lo = Math.min.apply(null, ys), hi = Math.max.apply(null, ys);
      var xs = s.ajuste.map(function (p) { return p[0]; });
      pinta("g_fit", BLChart.plot({
        w: A, h: B,
        xdom: [Math.min.apply(null, xs) - 0.04, Math.max.apply(null, xs) + 0.04],
        ydom: [lo - 0.7, hi + 0.7],
        xlab: "Sw (fracción)", ylab: "ln(kro / krw)",
        series: [{ pts: s.recta, color: "var(--ink)", w: 1.6, dash: "6 4" }],
        dots: s.ajuste.map(function (p) { return { x: p[0], y: p[1], color: "var(--gas)", r: 4 }; })
      }));
    }

    /* 3 · fw + tangente */
    var sw0 = s.fw[0][0], sw1 = s.fw[s.fw.length - 1][0];
    pinta("g_fw", BLChart.plot({
      w: A, h: B, xdom: [sw0, sw1], ydom: [0, 1],
      xlab: "Sw (fracción)", ylab: "fw",
      areas: [{ pts: s.fw, color: "var(--brine)", op: 0.09 }],
      series: [{ pts: s.fw, color: "var(--brine)", w: 2.3 },
               { pts: s.tangente, color: "var(--crude)", w: 1.6, dash: "5 4" }],
      rings: [{ x: s.tangente[1][0], y: s.tangente[1][1], color: "var(--ink)" },
              { x: s.tangente[2][0], y: 1, color: "var(--crude)", r: 4.5 }],
      vlines: [{ x: s.tangente[1][0], color: "var(--ink)", t: "Swf" }],
      labels: [{ x: s.tangente[2][0], y: 0.94, t: "S̄w", color: "var(--crude)", a: "middle" }]
    }));

    /* 4 · derivada. El anillo marca (Swf, dfw|Swf), que por la condicion de
       tangencia coincide con la pendiente de la tangente de Welge. */
    var swf = s.tangente[1][0];
    var enFrente = s.dfw.reduce(function (mejor, p) {
      return Math.abs(p[0] - swf) < Math.abs(mejor[0] - swf) ? p : mejor;
    }, s.dfw[0]);
    pinta("g_dfw", BLChart.plot({
      w: A, h: B, xdom: [sw0, sw1], ydom: [0, maxY(s.dfw, 1) * 1.1],
      xlab: "Sw (fracción)", ylab: "dfw / dSw",
      series: [{ pts: s.dfw, color: "var(--gas)", w: 2.3 }],
      rings: [{ x: enFrente[0], y: enFrente[1], color: "var(--ink)" }],
      vlines: [{ x: swf, color: "var(--ink)", t: "Swf" }]
    }));

    /* 5 · perfil de saturacion */
    if (s.perfil && s.perfil.length) {
      var xm = s.perfil[s.perfil.length - 1][0];
      pinta("g_perfil", BLChart.plot({
        w: A, h: B, xdom: [0, xm], ydom: [0, 1],
        xlab: "Distancia desde el inyector (ft)", ylab: "Sw (fracción)",
        areas: [{ pts: s.perfil, color: "var(--brine)", op: 0.13 }],
        series: [{ pts: s.perfil, color: "var(--brine)", w: 2.5 }],
        vlines: [{ x: s.perfil[s.perfil.length - 2][0], color: "var(--crude)", t: "productor" }]
      }));
    }

    /* 6 · recobro y corte tras irrupcion  [wi, ed, corte, wor, sw2] */
    if (s.post_bt && s.post_bt.length) {
      var wimax = Math.min(s.post_bt[s.post_bt.length - 1][0], 12);
      var ed = s.post_bt.map(function (r) { return [r[0], r[1]]; });
      var cut = s.post_bt.map(function (r) { return [r[0], r[2]]; });
      // La etiqueta se apoya sobre la propia curva, no en una altura fija:
      // asi queda junto a la linea aunque cambien los datos del pozo.
      var xEd = wimax * 0.55;
      var pEd = ed.reduce(function (mejor, p) {
        return Math.abs(p[0] - xEd) < Math.abs(mejor[0] - xEd) ? p : mejor;
      }, ed[0]);
      var xCut = wimax * 0.35;
      var pCut = cut.reduce(function (mejor, p) {
        return Math.abs(p[0] - xCut) < Math.abs(mejor[0] - xCut) ? p : mejor;
      }, cut[0]);

      pinta("g_post", BLChart.plot({
        w: A, h: B, xdom: [0, wimax], ydom: [0, 1],
        xlab: "Agua inyectada (volúmenes porosos)", ylab: "Fracción",
        series: [{ pts: ed, color: "var(--crude)", w: 2.3 },
                 { pts: cut, color: "var(--brine)", w: 2.3 }],
        // Por encima de la curva, salvo que esta ya vaya pegada al techo:
        // ahi la etiqueta se cuelga por debajo para no montarse en la linea.
        labels: [{ x: pEd[0], y: pEd[1] > 0.88 ? pEd[1] - 0.06 : pEd[1] + 0.05,
                   a: "middle", t: "eficiencia de desplazamiento", color: "var(--crude)" },
                 { x: pCut[0], y: pCut[1] > 0.88 ? pCut[1] - 0.06 : pCut[1] + 0.05,
                   a: "middle", t: "corte de agua", color: "var(--brine)" }]
      }));

      var wor = s.post_bt.map(function (r) { return [r[0], r[3]]; })
        .filter(function (r) { return r[0] <= wimax; });
      pinta("g_wor", BLChart.plot({
        w: A, h: B, xdom: [0, wimax], ydom: [0, Math.min(maxY(wor, 1) * 1.1, 200)],
        xlab: "Agua inyectada (volúmenes porosos)", ylab: "WOR (bbl agua / bbl petróleo)",
        series: [{ pts: wor, color: "var(--bad)", w: 2.3 }],
        hlines: [{ y: 10, color: "var(--faint)", t: "WOR = 10" }]
      }));
    }

    /* 8 · presion capilar */
    if (pc && pc.length) {
      pinta("g_pc", BLChart.plot({
        w: A, h: B, xdom: [pc[0][0], pc[pc.length - 1][0]],
        ydom: [0, maxY(pc, 1) * 1.1],
        xlab: "Sw (fracción)", ylab: "Pc (psi)",
        series: [{ pts: pc, color: "var(--rock)", w: 2.3 }]
      }));
    } else {
      var h = $("pc_hint");
      if (h) {
        h.textContent = "Sin datos suficientes: cargue σ (tensión interfacial), " +
          "θ (ángulo de contacto), k y φ en la ficha del pozo.";
      }
      pinta("g_pc", '<div class="vacio" style="padding:60px 20px">Sin datos de presión capilar</div>');
    }
  }

  /* ------------------------------------------------- tabla kr editable -- */
  function tablaKr(puntos, cfg) {
    var cuerpo = document.querySelector("#tablaKr tbody");
    if (!cuerpo) return;

    function dibuja() {
      cuerpo.innerHTML = puntos.map(function (p, i) {
        var razon = p.krw > 0 ? p.kro / p.krw : null;
        var editable = cfg.curvaId !== null;
        function celda(campo, paso) {
          return '<td class="num"><input type="number" step="' + paso + '" value="' + p[campo] +
            '" data-i="' + i + '" data-c="' + campo + '" style="text-align:right"' +
            (editable ? "" : " readonly") + "></td>";
        }
        return "<tr>" + celda("sw", "0.001") + celda("krw", "0.0001") + celda("kro", "0.0001") +
          '<td class="num">' + (razon === null ? "—" : razon.toFixed(3)) + "</td>" +
          '<td class="num">' + (razon === null ? "excluida" : Math.log(razon).toFixed(3)) + "</td>" +
          "<td>" + (editable ? '<button class="icon btn-danger" data-del="' + i + '">✕</button>' : "") + "</td></tr>";
      }).join("");
    }
    dibuja();

    cuerpo.addEventListener("input", function (ev) {
      var el = ev.target;
      if (el.dataset.i === undefined) return;
      puntos[+el.dataset.i][el.dataset.c] = parseFloat(el.value) || 0;
      var fila = el.closest("tr");
      var p = puntos[+el.dataset.i];
      var razon = p.krw > 0 ? p.kro / p.krw : null;
      fila.children[3].textContent = razon === null ? "—" : razon.toFixed(3);
      fila.children[4].textContent = razon === null ? "excluida" : Math.log(razon).toFixed(3);
    });
    cuerpo.addEventListener("click", function (ev) {
      if (ev.target.dataset.del === undefined) return;
      puntos.splice(+ev.target.dataset.del, 1);
      dibuja();
    });

    var add = $("addFila");
    if (add) add.addEventListener("click", function () {
      puntos.push({ sw: 0.5, krw: 0.1, kro: 0.2 });
      dibuja();
    });

    var save = $("guardarKr");
    if (save) save.addEventListener("click", function () {
      var g = $("guardando");
      if (g) g.classList.add("on");
      fetch(cfg.urlCurva + cfg.curvaId + "/guardar/", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": global.CSRF },
        body: JSON.stringify({ puntos: puntos })
      }).then(function (r) { return r.json(); }).then(function (r) {
        if (g) g.classList.remove("on");
        if (r.ok) location.reload();
        else alert("No se pudo guardar: " + (r.error || "error desconocido"));
      }).catch(function () {
        if (g) g.classList.remove("on");
        alert("No se pudo guardar la curva.");
      });
    });
  }

  function iniciar(cfg) {
    var campo = leer("campoJson");
    if (campo) { polar(campo); return; }
    graficos(leer("seriesJson"), leer("pcJson"));
    tablaKr(leer("krJson") || [], cfg);
  }

  global.BLCalculos = { iniciar: iniciar };
})(window);
