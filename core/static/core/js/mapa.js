/* =========================================================================
   Mapa areal del frente de agua.

   Cada inyector trae tres arreglos paralelos: th (azimut), ru (radio unitario)
   y tope (radio maximo del brazo). El radio al tiempo t es

       r(theta, t) = min_suave( ru(theta)·sqrt(t) , tope(theta) )

   Toda la fisica ya viene resuelta desde Django; aqui solo se dibuja, para
   que la barra de tiempo responda sin ida y vuelta al servidor.
   ========================================================================= */
(function (global) {
  "use strict";

  var W = 780, H = 545, PAD = 46;

  /* Mismo tope suave que usa flood.py, para que mapa y tabla coincidan. */
  function topeSuave(r, tope) {
    if (!(tope > 0)) return 0;
    var u = r / tope;
    if (u <= 0.8) return r;
    return tope * (1 - 0.2 * Math.exp(-(u - 0.8) / 0.2));
  }

  function radios(iny, t) {
    var raiz = Math.sqrt(Math.max(t, 0));
    var out = new Array(iny.ru.length);
    for (var i = 0; i < iny.ru.length; i++) {
      out[i] = topeSuave(iny.ru[i] * raiz, iny.tope[i]);
    }
    return out;
  }

  /* Barra de escala con una longitud "redonda". */
  function escalaBonita(ftPorPx, anchoMax) {
    var objetivo = ftPorPx * anchoMax;
    var mag = Math.pow(10, Math.floor(Math.log10(objetivo)));
    var n = objetivo / mag;
    var val = (n >= 5 ? 5 : n >= 2 ? 2 : 1) * mag;
    return { ft: val, px: val / ftPorPx };
  }

  function render(el, datos, t, opts) {
    opts = opts || {};
    if (!el) return;
    var m = datos.marco;
    if (!m) { el.innerHTML = ""; return; }

    var dx = m.x1 - m.x0, dy = m.y1 - m.y0;
    var sc = Math.min((W - 2 * PAD) / dx, (H - 2 * PAD) / dy);
    var ox = (W - dx * sc) / 2, oy = (H - dy * sc) / 2;
    var MX = function (v) { return ox + (v - m.x0) * sc; };
    var MY = function (v) { return H - oy - (v - m.y0) * sc; };

    var g = "";
    g += '<rect x="0" y="0" width="' + W + '" height="' + H +
      '" fill="var(--panel2)" stroke="var(--rule)" rx="12"/>';

    /* ---------------- rejilla, rotulada en pies desde el borde ---------- */
    var paso = BLChart.ticks(0, dx, 6);
    var stepFt = paso.length > 1 ? paso[1] - paso[0] : dx;
    for (var vx = 0; vx <= dx + 1e-6; vx += stepFt) {
      var px = MX(m.x0 + vx);
      g += '<line class="grl" x1="' + px + '" y1="' + MY(m.y0) + '" x2="' + px + '" y2="' + MY(m.y1) + '"/>';
      g += '<text class="tk" x="' + px + '" y="' + (H - 13) + '" text-anchor="middle">' + BLChart.nice(vx) + "</text>";
    }
    for (var vy = 0; vy <= dy + 1e-6; vy += stepFt) {
      var py = MY(m.y0 + vy);
      g += '<line class="grl" x1="' + MX(m.x0) + '" y1="' + py + '" x2="' + MX(m.x1) + '" y2="' + py + '"/>';
      g += '<text class="tk" x="' + (MX(m.x0) - 6) + '" y="' + (py + 3) + '" text-anchor="end">' + BLChart.nice(vy) + "</text>";
    }
    g += '<text class="al" x="' + W / 2 + '" y="' + (H - 1) + '" text-anchor="middle">Distancia (ft)</text>';

    /* ---------------- area barrida: union de todos los inyectores ------- */
    var contornos = [];
    (datos.inyectores || []).forEach(function (iny) {
      if (!iny.ok || !iny.th || !iny.th.length) return;
      var r = radios(iny, t);
      var d = "";
      for (var i = 0; i < iny.th.length; i++) {
        var X = MX(iny.x + r[i] * Math.cos(iny.th[i]));
        var Y = MY(iny.y + r[i] * Math.sin(iny.th[i]));
        d += (i ? "L" : "M") + X.toFixed(1) + " " + Y.toFixed(1);
      }
      contornos.push(d + "Z");
    });

    if (contornos.length) {
      /* fill-rule nonzero une los lobulos superpuestos en una sola mancha */
      g += '<path d="' + contornos.join(" ") + '" fill="var(--brine)" fill-rule="nonzero" opacity="0.42"/>';
      contornos.forEach(function (d) {
        g += '<path d="' + d + '" fill="none" stroke="var(--brine)" stroke-width="1.5" opacity="0.75"/>';
      });
    }

    /* ---------------- lineas inyector - productor ----------------------- */
    var porId = {};
    (datos.productores || []).forEach(function (p) { porId[p.id] = p; });

    (datos.inyectores || []).forEach(function (iny) {
      (iny.brazos || []).forEach(function (b) {
        var p = porId[b.productor_id];
        if (!p) return;
        var golpe = b.tbt != null && t >= b.tbt;
        g += '<line x1="' + MX(iny.x) + '" y1="' + MY(iny.y) + '" x2="' + MX(p.x) + '" y2="' + MY(p.y) +
          '" stroke="' + (golpe ? "var(--bad)" : "var(--rock)") + '" stroke-width="1" stroke-dasharray="3 4" opacity="' +
          (golpe ? 0.75 : 0.45) + '"/>';
      });
    });

    /* ---------------- pozos --------------------------------------------- */
    (datos.inyectores || []).forEach(function (iny) {
      var X = MX(iny.x), Y = MY(iny.y);
      g += '<circle cx="' + X + '" cy="' + Y + '" r="8.5" fill="var(--good)" stroke="#fff" stroke-width="2"/>';
      g += '<text class="wlbl" x="' + X + '" y="' + (Y - 14) + '" text-anchor="middle" fill="var(--ink)">' +
        BLChart.esc(iny.nombre) + "</text>";
      g += '<text class="ann" x="' + X + '" y="' + (Y + 21) + '" text-anchor="middle" fill="var(--soft)">' +
        BLChart.nice(iny.q) + " BWPD</text>";
    });

    (datos.productores || []).forEach(function (p) {
      var X = MX(p.x), Y = MY(p.y);
      var golpe = p.tbt != null && t >= p.tbt;
      var activo = opts.activo === p.id;
      if (activo) {
        g += '<circle cx="' + X + '" cy="' + Y + '" r="14" fill="none" stroke="var(--ink)" stroke-width="1.3" stroke-dasharray="3 3"/>';
      }
      g += '<circle cx="' + X + '" cy="' + Y + '" r="8" fill="' + (golpe ? "var(--bad)" : "var(--crude)") +
        '" stroke="#fff" stroke-width="2"/>';
      g += '<text class="wlbl" x="' + X + '" y="' + (Y - 13) + '" text-anchor="middle" fill="' +
        (golpe ? "var(--bad)" : "var(--ink)") + '">' + BLChart.esc(p.nombre) + "</text>";
      if (golpe) {
        g += '<text class="ann" x="' + X + '" y="' + (Y + 21) + '" text-anchor="middle" fill="var(--bad)">IRRUPCIÓN · día ' +
          Math.round(p.tbt) + "</text>";
      } else if (p.tbt != null) {
        g += '<text class="ann" x="' + X + '" y="' + (Y + 21) + '" text-anchor="middle" fill="var(--faint)">' +
          Math.round(p.tbt - t) + " d</text>";
      }
    });

    /* ---------------- barra de escala ----------------------------------- */
    var esc = escalaBonita(1 / sc, 130);
    var bx = W - PAD - esc.px, by = PAD - 14;
    g += '<line x1="' + bx + '" y1="' + by + '" x2="' + (bx + esc.px) + '" y2="' + by +
      '" stroke="var(--ink)" stroke-width="1.6"/>';
    g += '<line x1="' + bx + '" y1="' + (by - 4) + '" x2="' + bx + '" y2="' + (by + 4) + '" stroke="var(--ink)" stroke-width="1.6"/>';
    g += '<line x1="' + (bx + esc.px) + '" y1="' + (by - 4) + '" x2="' + (bx + esc.px) + '" y2="' + (by + 4) + '" stroke="var(--ink)" stroke-width="1.6"/>';
    g += '<text class="ann" x="' + (bx + esc.px / 2) + '" y="' + (by - 7) + '" text-anchor="middle">' +
      BLChart.nice(esc.ft) + " ft</text>";

    /* ---------------- reloj --------------------------------------------- */
    g += '<g transform="translate(' + (PAD - 22) + "," + (PAD - 26) + ')">' +
      '<rect x="0" y="0" width="128" height="30" rx="9" fill="var(--ink)" opacity="0.92"/>' +
      '<text x="11" y="19" font-family="IBM Plex Mono, monospace" font-size="13" fill="#fff">día ' +
      Math.round(t).toLocaleString("es") + "</text></g>";

    el.innerHTML = '<svg viewBox="0 0 ' + W + " " + H +
      '" role="img" aria-label="Mapa del área barrida por el agua inyectada">' + g + "</svg>";
  }

  global.BLMapa = { render: render, radios: radios };
})(window);
