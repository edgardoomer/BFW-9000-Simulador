/* =========================================================================
   Pestana de estudio: fichas de entrada (derecha) y resultados (izquierda).
   ========================================================================= */
(function (global) {
  "use strict";

  var S = {
    datos: null, pozos: null, curvas: [], opciones: {},
    t: 0, activo: null, anim: null, cfg: null,
    orden: [], abiertas: {}, pendientes: {}, temporizador: null
  };

  /* ------------------------------------------------------------- utiles -- */
  function $(id) { return document.getElementById(id); }
  function E(s) { return BLChart.esc(s); }
  function n2(v, d) { return (v === null || v === undefined || isNaN(v)) ? "—" : (+v).toFixed(d === undefined ? 1 : d); }
  function miles(v) { return v == null ? "—" : Math.round(v).toLocaleString("es"); }

  function post(url, cuerpo) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": global.CSRF },
      body: JSON.stringify(cuerpo || {})
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false, error: "Respuesta no válida" }; });
    });
  }

  function marcarGuardando(on) {
    var el = $("guardando");
    if (el) el.classList.toggle("on", !!on);
  }

  /* ============================ ENTRADAS ================================ */

  function pares_de(prodId) {
    return S.pozos.pares.filter(function (p) { return p.productor === prodId; });
  }
  function pares_de_iny(injId) {
    return S.pozos.pares.filter(function (p) { return p.inyector === injId; });
  }
  function pozoPorId(id) {
    return S.pozos.pozos.filter(function (p) { return p.id === id; })[0];
  }
  function resultadoDe(id) {
    return (S.datos.productores || []).filter(function (p) { return p.id === id; })[0];
  }

  /* Campo numerico con herencia visible del valor por defecto del proyecto. */
  function num(p, campo, etiqueta, paso, def) {
    var v = p[campo];
    var ph = def !== undefined && def !== null ? "auto " + def : "";
    return '<div><label>' + E(etiqueta) + '</label>' +
      '<input type="number" step="' + (paso || "any") + '" value="' + (v === null || v === undefined ? "" : v) +
      '" placeholder="' + E(ph) + '" data-pozo="' + p.id + '" data-campo="' + campo + '"></div>';
  }

  function txt(p, campo, etiqueta) {
    return '<div><label>' + E(etiqueta) + '</label>' +
      '<input type="text" value="' + E(p[campo] || "") + '" data-pozo="' + p.id +
      '" data-campo="' + campo + '" data-texto="1"></div>';
  }

  function sel(p, campo, etiqueta, opciones) {
    var o = opciones.map(function (c) {
      return '<option value="' + E(c[0]) + '"' + (p[campo] === c[0] ? " selected" : "") + ">" + E(c[1]) + "</option>";
    }).join("");
    return '<div><label>' + E(etiqueta) + '</label><select data-pozo="' + p.id +
      '" data-campo="' + campo + '" data-texto="1">' + o + "</select></div>";
  }

  /* ---------------------------------------------------- ficha inyector -- */
  function fichaInyector(p) {
    var mis = pares_de_iny(p.id);
    var d = S.pozos.defaults;
    var lista = mis.length
      ? '<table class="list" style="font-size:12px">' + mis.map(function (q) {
          var prod = pozoPorId(q.productor);
          return "<tr><td class='n'>" + E(prod ? prod.nombre_pozo : "?") +
            "</td><td class='num'>" + miles(q.L) + " ft</td><td class='num'>" +
            n2(q.k_direccional, 0) + " md</td></tr>";
        }).join("") + "</table>"
      : '<p class="hint">Todavía no alimenta ningún productor. Agregue el canal desde la ficha del productor.</p>';

    return '<div class="sub">Identificación</div>' +
      '<div class="fields f2">' + txt(p, "id_pozo", "ID pozo") + txt(p, "nombre_pozo", "Nombre") + "</div>" +
      '<div class="fields f2 mt">' + num(p, "x", "Coord. X") + num(p, "y", "Coord. Y") + "</div>" +

      '<div class="sub">Inyección</div>' +
      '<div class="fields f3">' +
        num(p, "q", "q iny (BWPD)", "10") +
        num(p, "presion_cabeza", "P cabeza (psi)", "10") +
        num(p, "skin", "Skin", "0.1") +
      "</div>" +
      '<div class="fields f3 mt">' +
        num(p, "h", "h (ft)", "0.5", d.h) +
        num(p, "phi", "φ (fracc.)", "0.01", d.phi) +
        num(p, "k", "k (md)", "1", d.k) +
      "</div>" +

      '<div class="sub">Equipo de inyección</div>' +
      '<div class="fields">' + sel(p, "tipo_bomba_iny", "Tipo de bomba", S.opciones.bomba) + "</div>" +

      '<div class="sub">Productores que alimenta</div>' + lista;
  }

  /* --------------------------------------------------- ficha productor -- */
  function fichaProductor(p) {
    var d = S.pozos.defaults;
    var mis = pares_de(p.id);
    var inyectores = S.pozos.pozos.filter(function (z) { return z.tipo === "INY"; });
    var libres = inyectores.filter(function (z) {
      return !mis.some(function (q) { return q.inyector === z.id; });
    });

    var filas = mis.map(function (q) {
      var iny = pozoPorId(q.inyector);
      return '<div class="card" style="background:var(--panel2);margin-bottom:7px;border-radius:11px">' +
        '<div style="display:flex;align-items:center;gap:7px;padding:7px 10px 0">' +
          '<b style="font-family:var(--disp);font-size:12.5px;flex:1">' + E(iny ? iny.nombre_pozo : "?") + "</b>" +
          '<span class="pill">L = ' + miles(q.L) + " ft</span>" +
          '<button class="icon btn-danger" data-borrarpar="' + q.id + '" title="Quitar este canal">✕</button>' +
        "</div>" +
        '<div class="fields f2" style="padding:7px 10px 10px">' +
          '<div><label>k direccional (md)</label><input type="number" step="1" value="' + q.k_direccional +
            '" data-par="' + q.id + '" data-campo="k_direccional"></div>' +
          '<div><label>Ancho del brazo (°)</label><input type="number" step="1" value="' + q.ancho_brazo +
            '" data-par="' + q.id + '" data-campo="ancho_brazo"></div>' +
        "</div></div>";
    }).join("");

    var agregar = libres.length
      ? '<div class="flex mt"><select id="nuevoIny_' + p.id + '" style="flex:1">' +
          libres.map(function (z) { return '<option value="' + z.id + '">' + E(z.nombre_pozo) + "</option>"; }).join("") +
        '</select><button class="mini" data-agregarpar="' + p.id + '">+ Conectar</button></div>'
      : (inyectores.length ? '<p class="hint mt">Ya está conectado a todos los inyectores.</p>'
                           : '<p class="hint mt">Cree primero un inyector.</p>');

    var curvas = S.curvas.map(function (c) {
      return '<option value="' + c.id + '"' + (p.curva_kr === c.id ? " selected" : "") + ">" + E(c.nombre) + "</option>";
    }).join("");

    var params = Object.keys(p.parametros_levantamiento || {}).sort().map(function (k) {
      return "<tr><td>" + E(k.replace(/_/g, " ")) + "</td><td class='num'>" +
        E(p.parametros_levantamiento[k]) + "</td></tr>";
    }).join("");

    return '<div class="sub">Identificación</div>' +
      '<div class="fields f2">' + txt(p, "id_pozo", "ID pozo") + txt(p, "nombre_pozo", "Nombre") + "</div>" +
      '<div class="fields f3 mt">' + num(p, "x", "Coord. X") + num(p, "y", "Coord. Y") +
        num(p, "q", "q líquido (BFPD)", "10") + "</div>" +

      '<div class="sub">Inyectores que alimentan este pozo</div>' +
      (filas || '<p class="hint">Sin conexión: este pozo no recibe agua todavía.</p>') + agregar +

      '<div class="sub">Petrofísica</div>' +
      '<div class="fields f3">' +
        num(p, "h", "h (ft)", "0.5", d.h) +
        num(p, "phi", "φ (fracc.)", "0.01", d.phi) +
        num(p, "k", "kh (md)", "1", d.k) +
        num(p, "kv", "kv (md)", "1") +
        num(p, "swi", "Swi", "0.01", d.swi) +
        num(p, "sor", "Sor", "0.01", d.sor) +
      "</div>" +

      '<div class="sub">Fluidos</div>' +
      '<div class="fields f3">' +
        num(p, "muw", "μw (cp)", "0.01", d.muw) +
        num(p, "muo", "μo (cp)", "0.1", d.muo) +
        num(p, "bo", "Bo", "0.01", d.bo) +
        num(p, "bw", "Bw", "0.01", d.bw) +
        num(p, "api", "°API", "0.1") +
        num(p, "pwf", "Pwf (psi)", "10") +
      "</div>" +

      '<div class="sub">Permeabilidad relativa</div>' +
      '<div class="fields"><div><label>Curva asignada</label><select data-pozo="' + p.id +
        '" data-campo="curva_kr" data-numsel="1">' + curvas + "</select></div></div>" +
      '<p class="hint" style="margin-top:5px">Edite los puntos de la curva en ' +
        '<a href="' + S.cfg.urls.calculos + "pozo/" + p.id + '/">Cálculos por pozo</a>.</p>' +

      "<details class='acc' style='margin-top:11px;box-shadow:none'><summary>Completación y levantamiento</summary>" +
      "<div class='inner'>" +
        '<div class="fields f2">' +
          num(p, "prof_md", "Prof. MD (ft)", "1") + num(p, "prof_tvd", "Prof. TVD (ft)", "1") +
          num(p, "tope_arena", "Tope arena (ft)", "1") + num(p, "base_arena", "Base arena (ft)", "1") +
        "</div>" +
        '<div class="fields f2 mt">' +
          sel(p, "tipo_completacion", "Completación", S.opciones.completacion) +
          sel(p, "tipo_levantamiento", "Levantamiento", S.opciones.levantamiento) +
        "</div>" +
        (params ? '<div class="sub">Parámetros del equipo</div><table class="list">' + params + "</table>" : "") +
        '<div class="sub">Presión capilar</div>' +
        '<div class="fields f3">' +
          num(p, "sigma_ow", "σ o/w (din/cm)", "0.5") +
          num(p, "angulo_contacto", "θ (°)", "1") +
          num(p, "pc_entrada", "Pc entrada (psi)", "0.1") +
        "</div>" +
      "</div></details>";
  }

  /* --------------------------------------------------------- fichas ----- */
  function renderFichas() {
    var cont = $("fichas");
    if (!S.orden.length) {
      S.orden = S.pozos.pozos.map(function (p) { return p.id; });
    } else {
      // conserva el orden del usuario y agrega los pozos nuevos al final
      var ids = S.pozos.pozos.map(function (p) { return p.id; });
      S.orden = S.orden.filter(function (i) { return ids.indexOf(i) >= 0; });
      ids.forEach(function (i) { if (S.orden.indexOf(i) < 0) S.orden.push(i); });
    }

    if (!S.pozos.pozos.length) {
      cont.innerHTML = '<div class="vacio" style="width:100%">Sin pozos. Agregue un inyector y un productor para empezar.</div>';
      return;
    }

    cont.innerHTML = S.orden.map(function (id) {
      var p = pozoPorId(id);
      if (!p) return "";
      var esIny = p.tipo === "INY";
      var abierta = !!S.abiertas[id];
      var r = esIny ? null : resultadoDe(id);
      var pill = "";
      if (r && r.tbt != null) {
        pill = '<span class="pill">tBT ' + miles(r.tbt) + " d</span>";
      } else if (r && !r.ok) {
        pill = '<span class="pill hit">revisar</span>';
      }
      return '<div class="well ' + (esIny ? "inj" : "prod") + " " + (abierta ? "abierta" : "cerrada") +
        '" data-w="' + id + '" draggable="true">' +
        '<div class="well-h" data-toggle="' + id + '">' +
          '<span class="grip" title="Arrastrar">⠿</span>' +
          '<span class="tag">' + (esIny ? "Iny" : "Prod") + "</span>" +
          '<span class="nm">' + E(p.nombre_pozo) + "</span>" + pill +
          '<button class="icon btn-danger" data-borrar="' + id + '" title="Eliminar pozo">✕</button>' +
          '<span class="chev">' + (abierta ? "▾" : "▸") + "</span>" +
        "</div>" +
        '<div class="well-b">' + (esIny ? fichaInyector(p) : fichaProductor(p)) + "</div>" +
      "</div>";
    }).join("");
  }

  /* Actualiza sin reconstruir: no roba el foco mientras se escribe. */
  function refrescarEtiquetas() {
    (S.datos.productores || []).forEach(function (r) {
      var card = document.querySelector('.well[data-w="' + r.id + '"] .well-h .pill');
      if (card) card.textContent = r.tbt != null ? "tBT " + miles(r.tbt) + " d" : "revisar";
    });
    // distancias L de cada canal
    var mapa = {};
    (S.datos.inyectores || []).forEach(function (iny) {
      (iny.brazos || []).forEach(function (b) { mapa[iny.id + ":" + b.productor_id] = b.L; });
    });
    S.pozos.pares.forEach(function (q) {
      var L = mapa[q.inyector + ":" + q.productor];
      if (L != null) q.L = L;
    });
    document.querySelectorAll("[data-par]").forEach(function (el) {
      var fila = el.closest(".card");
      if (!fila) return;
      var par = S.pozos.pares.filter(function (z) { return z.id === +el.dataset.par; })[0];
      var pill = fila.querySelector(".pill");
      if (par && pill) pill.textContent = "L = " + miles(par.L) + " ft";
    });
  }

  /* ============================ RESULTADOS ============================== */

  function renderMapa() {
    BLMapa.render($("mapa"), S.datos, S.t, { activo: S.activo });
    var lbl = $("tLbl");
    if (lbl) lbl.textContent = Math.round(S.t).toLocaleString("es");
  }

  function renderTablaBT() {
    var filas = S.datos.orden_irrupcion || [];
    var h = "<tr><th>#</th><th>Pozo</th><th class='num'>L (ft)</th>" +
      "<th class='num'>k (md)</th><th class='num'>tBT (días)</th>" +
      "<th class='num'>años</th><th>Desde</th><th class='num'>Fuentes</th></tr>";
    if (!filas.length) {
      h += "<tr><td colspan='8'>Sin canales inyector–productor definidos.</td></tr>";
    } else {
      h += filas.map(function (f) {
        var golpe = S.t >= f.tbt;
        return '<tr class="' + (golpe ? "hit" : "") + (S.activo === f.id ? " sel" : "") +
          '"><td>' + (golpe ? "●" : f.orden) + "</td>" +
          '<td class="n"><a href="' + S.cfg.urls.calculos + "pozo/" + f.id + '/">' + E(f.nombre) + "</a></td>" +
          '<td class="num">' + miles(f.L) + "</td>" +
          '<td class="num">' + miles(f.k) + "</td>" +
          '<td class="num">' + miles(f.tbt) + "</td>" +
          '<td class="num">' + n2(f.tbt / 365.25, 2) + "</td>" +
          "<td>" + E(f.inyector) + "</td>" +
          '<td class="num">' + f.n_fuentes + "</td></tr>";
      }).join("");
    }
    $("tablaBT").innerHTML = h;
  }

  function renderFw() {
    var prods = (S.datos.productores || []);
    var s = $("selProd");
    s.innerHTML = prods.map(function (p) {
      return '<option value="' + p.id + '"' + (p.id === S.activo ? " selected" : "") + ">" + E(p.nombre) + "</option>";
    }).join("") || "<option>— sin productores —</option>";

    var r = resultadoDe(S.activo) || prods[0];
    var box = $("graficoFw"), st = $("statsFw");
    if (!r) { box.innerHTML = '<div class="vacio">Agregue un productor.</div>'; st.innerHTML = ""; return; }
    if (!r.ok) {
      box.innerHTML = '<div class="warn">' + E(r.mensaje || "No fue posible resolver este pozo.") + "</div>";
      st.innerHTML = ""; return;
    }

    box.innerHTML = BLChart.plot({
      w: 620, h: 360, xdom: [r.swi, 1 - r.sor], ydom: [0, 1],
      xlab: "Saturación de agua, Sw (fracción)", ylab: "Flujo fraccional de agua, fw",
      areas: [{ pts: r.fw_curva, color: "var(--brine)", op: 0.09 }],
      series: [
        { pts: r.fw_curva, color: "var(--brine)", w: 2.4 },
        { pts: r.tangente, color: "var(--crude)", w: 1.7, dash: "6 4" }
      ],
      rings: [
        { x: r.swf, y: r.fwf, color: "var(--ink)" },
        { x: r.sw_prom, y: 1, color: "var(--crude)", r: 4.5 }
      ],
      vlines: [{ x: r.swf, color: "var(--ink)", t: "Swf" }],
      labels: [
        { x: r.sw_prom, y: 0.945, t: "S̄w", color: "var(--crude)", a: "middle" },
        { x: r.swi + (1 - r.sor - r.swi) * 0.04, y: 0.06, t: "tangente desde (Swi, fw₀)", color: "var(--soft)" }
      ],
      alt: "Curva de flujo fraccional con la tangente de Welge"
    });

    st.innerHTML = [
      ["Sw del frente", n2(r.swf, 3), "fracción"],
      ["fw en el frente", n2(r.fwf, 3), ""],
      ["S̄w tras el frente", n2(r.sw_prom, 3), "fracción"],
      ["Irrupción", r.tbt != null ? miles(r.tbt) : "—", "días"],
      ["Distancia al inyector", r.L != null ? miles(r.L) : "—", "ft"]
    ].map(function (c, i) {
      return '<div class="stat' + (i === 3 ? " hi" : "") + '"><div class="k">' + c[0] +
        '</div><div class="v">' + c[1] + '</div><div class="u">' + c[2] + "</div></div>";
    }).join("");
  }

  function renderAvisos() {
    var a = S.datos.avisos || [];
    $("avisos").innerHTML = a.length
      ? a.map(function (m) { return '<div class="warn">' + E(m) + "</div>"; }).join("")
      : "";
  }

  function renderResultados() {
    var sl = $("tiempo");
    var tmax = S.datos.t_max || 1000;
    sl.max = tmax; sl.step = tmax / 1000;
    if (S.t > tmax) S.t = tmax;
    sl.value = S.t;
    renderMapa(); renderTablaBT(); renderFw(); renderAvisos(); refrescarEtiquetas();
  }

  /* ============================ GUARDADO ================================ */

  function encolarPozo(id) {
    S.pendientes["pozo:" + id] = true;
    programar();
  }
  function encolarPar(id) {
    S.pendientes["par:" + id] = true;
    programar();
  }

  function programar() {
    clearTimeout(S.temporizador);
    S.temporizador = setTimeout(enviar, 450);
  }

  function enviar() {
    var claves = Object.keys(S.pendientes);
    if (!claves.length) return;
    S.pendientes = {};
    marcarGuardando(true);

    var cadena = Promise.resolve();
    claves.forEach(function (clave) {
      var partes = clave.split(":"), tipo = partes[0], id = +partes[1];
      cadena = cadena.then(function () {
        if (tipo === "pozo") {
          var p = pozoPorId(id);
          if (!p) return;
          return post(S.cfg.urls.pozoBase + id + "/", p);
        }
        var q = S.pozos.pares.filter(function (z) { return z.id === id; })[0];
        if (!q) return;
        return post(S.cfg.urls.parBase + id + "/", q);
      }).then(function (res) {
        if (res && res.ok && res.analisis) S.datos = res.analisis;
        if (res && !res.ok && res.error) console.warn("Guardado:", res.error);
      });
    });

    cadena.then(function () {
      marcarGuardando(false);
      renderResultados();
    }).catch(function (e) {
      marcarGuardando(false);
      console.error(e);
    });
  }

  /* ============================= EVENTOS ================================ */

  function conectar() {
    var fichas = $("fichas");

    /* --- edicion --- */
    fichas.addEventListener("input", function (ev) {
      var el = ev.target;
      if (el.dataset.pozo) {
        var p = pozoPorId(+el.dataset.pozo);
        if (!p) return;
        var campo = el.dataset.campo;
        if (el.dataset.texto) p[campo] = el.value;
        else if (el.dataset.numsel) p[campo] = el.value ? +el.value : null;
        else p[campo] = el.value === "" ? null : parseFloat(el.value);
        if (campo === "nombre_pozo") {
          var t = document.querySelector('.well[data-w="' + p.id + '"] .nm');
          if (t) t.textContent = el.value;
        }
        encolarPozo(p.id);
      } else if (el.dataset.par) {
        var q = S.pozos.pares.filter(function (z) { return z.id === +el.dataset.par; })[0];
        if (!q) return;
        q[el.dataset.campo] = el.value === "" ? null : parseFloat(el.value);
        encolarPar(q.id);
      }
    });
    /* Los <select> no emiten "input" de forma consistente en todos los
       navegadores, asi que se atienden aparte. */
    fichas.addEventListener("change", function (ev) {
      var el = ev.target;
      if (el.tagName !== "SELECT" || !el.dataset.pozo) return;
      var p = pozoPorId(+el.dataset.pozo);
      if (!p) return;
      p[el.dataset.campo] = el.dataset.numsel ? (el.value ? +el.value : null) : el.value;
      encolarPozo(p.id);
    });

    /* --- clics --- */
    fichas.addEventListener("click", function (ev) {
      var t = ev.target;

      if (t.dataset.borrar) {
        ev.stopPropagation();
        var p = pozoPorId(+t.dataset.borrar);
        if (!confirm("¿Eliminar " + (p ? p.nombre_pozo : "este pozo") + " y sus canales?")) return;
        marcarGuardando(true);
        post(S.cfg.urls.pozoBase + t.dataset.borrar + "/borrar/").then(function (r) {
          marcarGuardando(false);
          if (!r.ok) return;
          S.datos = r.analisis; S.pozos = r.pozos;
          if (S.activo === +t.dataset.borrar) {
            S.activo = (S.datos.productores[0] || {}).id || null;
          }
          renderFichas(); renderResultados();
        });
        return;
      }

      if (t.dataset.borrarpar) {
        ev.stopPropagation();
        marcarGuardando(true);
        post(S.cfg.urls.parBase + t.dataset.borrarpar + "/borrar/").then(function (r) {
          marcarGuardando(false);
          if (!r.ok) return;
          S.datos = r.analisis; S.pozos = r.pozos;
          renderFichas(); renderResultados();
        });
        return;
      }

      if (t.dataset.agregarpar) {
        ev.stopPropagation();
        var s = $("nuevoIny_" + t.dataset.agregarpar);
        if (!s || !s.value) return;
        marcarGuardando(true);
        post(S.cfg.urls.parCrear, {
          inyector: +s.value, productor: +t.dataset.agregarpar
        }).then(function (r) {
          marcarGuardando(false);
          if (!r.ok) return;
          S.datos = r.analisis; S.pozos = r.pozos;
          renderFichas(); renderResultados();
        });
        return;
      }

      var cab = t.closest(".well-h");
      if (cab) {
        var id = +cab.dataset.toggle;
        var caja = cab.parentElement;
        var abierta = caja.classList.toggle("abierta");
        caja.classList.toggle("cerrada", !abierta);
        cab.querySelector(".chev").textContent = abierta ? "▾" : "▸";
        S.abiertas[id] = abierta;
        var p = pozoPorId(id);
        if (p && p.tipo === "PRO" && abierta) {
          S.activo = id; renderFw(); renderMapa(); renderTablaBT();
        }
      }
    });

    /* --- arrastrar para reordenar --- */
    var arrastrada = null;
    fichas.addEventListener("dragstart", function (ev) {
      var w = ev.target.closest(".well");
      if (!w) return;
      arrastrada = w;
      w.classList.add("arrastrando");
      ev.dataTransfer.effectAllowed = "move";
    });
    fichas.addEventListener("dragend", function () {
      if (arrastrada) arrastrada.classList.remove("arrastrando");
      document.querySelectorAll(".well.destino").forEach(function (e) { e.classList.remove("destino"); });
      arrastrada = null;
      S.orden = Array.prototype.map.call(fichas.children, function (c) { return +c.dataset.w; });
    });
    fichas.addEventListener("dragover", function (ev) {
      ev.preventDefault();
      var w = ev.target.closest(".well");
      if (!w || w === arrastrada || !arrastrada) return;
      document.querySelectorAll(".well.destino").forEach(function (e) { e.classList.remove("destino"); });
      w.classList.add("destino");
      var caja = w.getBoundingClientRect();
      var despues = (ev.clientY - caja.top) > caja.height / 2;
      fichas.insertBefore(arrastrada, despues ? w.nextSibling : w);
    });
    fichas.addEventListener("drop", function (ev) { ev.preventDefault(); });

    /* --- agregar pozos --- */
    function crear(tipo) {
      marcarGuardando(true);
      post(S.cfg.urls.pozoCrear, { tipo: tipo }).then(function (r) {
        marcarGuardando(false);
        if (!r.ok) return;
        S.datos = r.analisis; S.pozos = r.pozos;
        S.abiertas[r.id] = true;
        if (tipo === "PRO") S.activo = r.id;
        renderFichas(); renderResultados();
        var el = document.querySelector('.well[data-w="' + r.id + '"]');
        if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
    $("addIny").addEventListener("click", function () { crear("INY"); });
    $("addProd").addEventListener("click", function () { crear("PRO"); });
    $("contraerTodo").addEventListener("click", function () {
      S.pozos.pozos.forEach(function (p) { S.abiertas[p.id] = false; });
      renderFichas();
    });

    /* --- barra de tiempo --- */
    $("tiempo").addEventListener("input", function (e) {
      S.t = +e.target.value;
      renderMapa(); renderTablaBT();
    });
    $("play").addEventListener("click", function () {
      var b = $("play");
      if (S.anim) {
        clearInterval(S.anim); S.anim = null; b.textContent = "▶ Reproducir"; return;
      }
      var tmax = S.datos.t_max || 1000;
      if (S.t >= tmax) S.t = 0;
      b.textContent = "❚❚ Pausar";
      S.anim = setInterval(function () {
        S.t += tmax / 170;
        if (S.t >= tmax) {
          S.t = tmax; clearInterval(S.anim); S.anim = null; b.textContent = "▶ Reproducir";
        }
        $("tiempo").value = S.t;
        renderMapa(); renderTablaBT();
      }, 55);
    });

    /* --- selector de productor --- */
    $("selProd").addEventListener("change", function (e) {
      S.activo = +e.target.value;
      renderFw(); renderMapa(); renderTablaBT();
    });

    /* --- cambio de proyecto --- */
    var cp = $("cambiarProyecto");
    if (cp) cp.addEventListener("change", function (e) { location.href = e.target.value; });
  }

  /* ============================== INICIO ================================ */
  function iniciar(cfg) {
    S.cfg = cfg;
    S.datos = JSON.parse($("datosIni").textContent);
    S.pozos = JSON.parse($("pozosIni").textContent);
    S.curvas = JSON.parse($("curvasIni").textContent);
    S.opciones = JSON.parse($("opcionesIni").textContent);
    S.activo = cfg.activo;
    S.t = 0;

    // Al abrir, solo la ficha del productor en analisis queda desplegada.
    S.pozos.pozos.forEach(function (p) { S.abiertas[p.id] = (p.id === S.activo); });

    renderFichas();
    renderResultados();
    conectar();
  }

  global.BLEstudio = { iniciar: iniciar, estado: S };
})(window);
