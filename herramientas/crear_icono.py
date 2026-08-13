"""Genera BFW-9000.ico para el acceso directo de Windows.

Busca la imagen de origen en este orden:

  1. icono/*.ico   el icono propio, si usted puso uno ahi
  2. core/static/core/img/logo.png
  3. la marca dibujada: cuadro oscuro, mancha de agua y los dos pozos

Sea cual sea, la cuadra y produce un icono multi-resolucion (256, 128, 64, 48,
32 y 16 px). Eso importa: un .ico con una sola imagen de 256 px se ve borroso
en la barra de tareas, porque Windows lo reduce al vuelo. Con las resoluciones
pequenas incluidas, cada tamano se dibuja nitido.

Todo en Python puro: decodifica PNG y BMP y escribe PNG con zlib, sin Pillow.

    python herramientas/crear_icono.py
"""
import struct
import sys
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_ICONO = RAIZ / "icono"
LOGO = RAIZ / "core" / "static" / "core" / "img" / "logo.png"
SALIDA = RAIZ / "BFW-9000.ico"

TAMANOS = (256, 128, 64, 48, 32, 16)


# ===========================================================================
# Lectura de PNG
# ===========================================================================
def _trozos(datos: bytes):
    if datos[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("no es un PNG")
    i = 8
    while i < len(datos):
        (largo,) = struct.unpack(">I", datos[i:i + 4])
        tipo = datos[i + 4:i + 8]
        yield tipo, datos[i + 8:i + 8 + largo]
        i += 12 + largo


def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def leer_png(datos: bytes):
    """Devuelve (pixeles RGBA como lista de filas, ancho, alto)."""
    ancho = alto = prof = tipo_color = interlace = None
    paleta, trns, idat = b"", b"", bytearray()

    for tipo, cuerpo in _trozos(datos):
        if tipo == b"IHDR":
            ancho, alto, prof, tipo_color, _, _, interlace = struct.unpack(">IIBBBBB", cuerpo)
        elif tipo == b"PLTE":
            paleta = cuerpo
        elif tipo == b"tRNS":
            trns = cuerpo
        elif tipo == b"IDAT":
            idat += cuerpo
        elif tipo == b"IEND":
            break

    if prof != 8:
        raise ValueError(f"profundidad {prof} bits no soportada (se espera 8)")
    if interlace:
        raise ValueError("PNG entrelazado no soportado")

    canales = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(tipo_color)
    if canales is None:
        raise ValueError(f"tipo de color {tipo_color} no soportado")

    crudo = zlib.decompress(bytes(idat))
    paso = ancho * canales
    filas_bytes, previa = [], bytearray(paso)
    pos = 0
    for _ in range(alto):
        filtro = crudo[pos]
        pos += 1
        linea = bytearray(crudo[pos:pos + paso])
        pos += paso
        for x in range(paso):
            a = linea[x - canales] if x >= canales else 0
            b = previa[x]
            c = previa[x - canales] if x >= canales else 0
            if filtro == 1:
                linea[x] = (linea[x] + a) & 0xFF
            elif filtro == 2:
                linea[x] = (linea[x] + b) & 0xFF
            elif filtro == 3:
                linea[x] = (linea[x] + (a + b) // 2) & 0xFF
            elif filtro == 4:
                linea[x] = (linea[x] + _paeth(a, b, c)) & 0xFF
        filas_bytes.append(linea)
        previa = linea

    # ---- a RGBA ----
    pixeles = []
    for linea in filas_bytes:
        fila = []
        for x in range(ancho):
            o = x * canales
            if tipo_color == 6:
                fila.append(tuple(linea[o:o + 4]))
            elif tipo_color == 2:
                fila.append((linea[o], linea[o + 1], linea[o + 2], 255))
            elif tipo_color == 0:
                g = linea[o]
                fila.append((g, g, g, 255))
            elif tipo_color == 4:
                g = linea[o]
                fila.append((g, g, g, linea[o + 1]))
            else:                                    # paleta
                i = linea[o]
                r, g, b = paleta[i * 3:i * 3 + 3]
                a = trns[i] if i < len(trns) else 255
                fila.append((r, g, b, a))
        pixeles.append(fila)
    return pixeles, ancho, alto


# ===========================================================================
# Lectura de ICO
# ===========================================================================
def leer_bmp_de_ico(datos: bytes):
    """Decodifica una imagen BMP incrustada en un .ico (32 bpp).

    Dentro de un ICO el BMP no lleva cabecera de archivo: arranca en el
    BITMAPINFOHEADER, la altura viene duplicada porque incluye la mascara AND,
    y las filas van de abajo hacia arriba.
    """
    (tam_cab, ancho, alto2, _planos, bpp) = struct.unpack("<IiiHH", datos[:16])
    alto = alto2 // 2
    if bpp != 32:
        raise ValueError(f"BMP de {bpp} bits no soportado (se espera 32)")

    inicio = tam_cab
    filas = []
    for y in range(alto):
        o = inicio + (alto - 1 - y) * ancho * 4      # de abajo hacia arriba
        fila = []
        for x in range(ancho):
            b, g, r, a = datos[o + x * 4: o + x * 4 + 4]
            fila.append((r, g, b, a))
        filas.append(fila)
    return filas, ancho, alto


def leer_ico(ruta: Path):
    """Devuelve (pixeles RGBA, lado) de la imagen mas grande del .ico."""
    d = ruta.read_bytes()
    _res, tipo, n = struct.unpack("<HHH", d[:6])
    if tipo != 1 or n == 0:
        raise ValueError("no es un .ico valido")

    mejor = None
    for i in range(n):
        o = 6 + 16 * i
        w, h, _c, _r, _pl, _bpp, sz, off = struct.unpack("<BBBBHHII", d[o:o + 16])
        lado = w or 256
        if mejor is None or lado > mejor[0]:
            mejor = (lado, off, sz)

    lado, off, sz = mejor
    cuerpo = d[off:off + sz]
    if cuerpo[:8] == b"\x89PNG\r\n\x1a\n":
        return leer_png(cuerpo)
    return leer_bmp_de_ico(cuerpo)


def buscar_icono_propio():
    """Primer .ico dentro de la carpeta icono/, si existe."""
    if not CARPETA_ICONO.is_dir():
        return None
    for p in sorted(CARPETA_ICONO.glob("*.ico")):
        return p
    return None


# ===========================================================================
# Escritura de PNG
# ===========================================================================
def _trozo(tipo: bytes, datos: bytes) -> bytes:
    return (struct.pack(">I", len(datos)) + tipo + datos
            + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF))


def escribir_png(pixeles, ancho, alto) -> bytes:
    crudo = bytearray()
    for fila in pixeles:
        crudo.append(0)
        for r, g, b, a in fila:
            crudo += bytes((r, g, b, a))
    return (b"\x89PNG\r\n\x1a\n"
            + _trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 6, 0, 0, 0))
            + _trozo(b"IDAT", zlib.compress(bytes(crudo), 9))
            + _trozo(b"IEND", b""))


# ===========================================================================
# Transformaciones
# ===========================================================================
def cuadrar(pixeles, ancho, alto):
    """Centra la imagen en un lienzo cuadrado del color de sus esquinas."""
    if ancho == alto:
        return pixeles, ancho

    esquinas = [pixeles[0][0], pixeles[0][-1], pixeles[-1][0], pixeles[-1][-1]]
    r = sum(c[0] for c in esquinas) // 4
    g = sum(c[1] for c in esquinas) // 4
    b = sum(c[2] for c in esquinas) // 4
    a = sum(c[3] for c in esquinas) // 4
    relleno = (r, g, b, a)

    lado = max(ancho, alto)
    dx, dy = (lado - ancho) // 2, (lado - alto) // 2
    salida = [[relleno] * lado for _ in range(lado)]
    for y in range(alto):
        salida[y + dy][dx:dx + ancho] = pixeles[y]
    return salida, lado


def redimensionar(pixeles, lado_origen, lado_destino):
    """Promedio por caja. Suficiente y estable para reducir un icono."""
    if lado_destino == lado_origen:
        return pixeles
    escala = lado_origen / lado_destino
    salida = []
    for y in range(lado_destino):
        y0, y1 = int(y * escala), max(int((y + 1) * escala), int(y * escala) + 1)
        fila = []
        for x in range(lado_destino):
            x0, x1 = int(x * escala), max(int((x + 1) * escala), int(x * escala) + 1)
            sr = sg = sb = sa = n = 0
            for yy in range(y0, min(y1, lado_origen)):
                for xx in range(x0, min(x1, lado_origen)):
                    r, g, b, a = pixeles[yy][xx]
                    sr += r * a; sg += g * a; sb += b * a; sa += a; n += 1
            if n == 0:
                fila.append((0, 0, 0, 0))
            elif sa == 0:
                fila.append((0, 0, 0, 0))
            else:
                # promedio ponderado por alfa, para no ensuciar los bordes
                fila.append((sr // sa, sg // sa, sb // sa, sa // n))
        salida.append(fila)
    return salida


def dibujar_marca(lado=256):
    """Marca de respaldo cuando no hay logo.png."""
    FONDO, AGUA, INY, PROD = (22, 33, 31), (22, 104, 122), (63, 163, 95), (194, 90, 30)
    radio_esq = lado * 0.22
    filas = []
    for y in range(lado):
        fila = []
        for x in range(lado):
            u, v = x / lado, y / lado
            dx, dy = min(x, lado - 1 - x), min(y, lado - 1 - y)
            alfa = 1.0
            if dx < radio_esq and dy < radio_esq:
                d = ((radio_esq - dx) ** 2 + (radio_esq - dy) ** 2) ** 0.5
                alfa = max(0.0, min(1.0, radio_esq - d + 0.5))
            if alfa <= 0:
                fila.append((0, 0, 0, 0))
                continue
            color = FONDO
            ddx, ddy = u - 0.44, v - 0.56
            r = (ddx * ddx + ddy * ddy) ** 0.5
            proy = (ddx * 0.788 + ddy * -0.616) / max(r, 1e-6)
            if r < 0.185 + 0.115 * max(0.0, proy) ** 6:
                color = AGUA
            if ((u - 0.44) ** 2 + (v - 0.56) ** 2) ** 0.5 < 0.052:
                color = INY
            if ((u - 0.656) ** 2 + (v - 0.37) ** 2) ** 0.5 < 0.044:
                color = PROD
            fila.append((*color, round(255 * alfa)))
        filas.append(fila)
    return filas, lado


# ===========================================================================
# Empaquetado ICO multi-resolucion
# ===========================================================================
def escribir_ico(imagenes, destino: Path):
    """`imagenes` es una lista de (lado, bytes_png)."""
    n = len(imagenes)
    cabecera = struct.pack("<HHH", 0, 1, n)
    desplazamiento = 6 + 16 * n
    entradas, cuerpo = b"", b""
    for lado, png in imagenes:
        d = 0 if lado >= 256 else lado
        entradas += struct.pack("<BBBBHHII", d, d, 0, 0, 1, 32, len(png), desplazamiento)
        cuerpo += png
        desplazamiento += len(png)
    destino.write_bytes(cabecera + entradas + cuerpo)


def _cargar_origen():
    """Devuelve (pixeles, lado, descripcion) segun la prioridad de fuentes."""
    propio = buscar_icono_propio()
    if propio:
        try:
            px, ancho, alto = leer_ico(propio)
            return px, ancho, alto, f"icono/{propio.name} ({ancho}x{alto})"
        except Exception as exc:
            print(f"  No se pudo leer {propio.name} ({exc}); se prueba con logo.png.")

    if LOGO.exists():
        try:
            px, ancho, alto = leer_png(LOGO.read_bytes())
            return px, ancho, alto, f"logo.png ({ancho}x{alto})"
        except Exception as exc:
            print(f"  No se pudo leer logo.png ({exc}); se usa la marca dibujada.")

    px, lado = dibujar_marca()
    return px, lado, lado, "marca dibujada"


def main():
    pixeles, ancho, alto, origen = _cargar_origen()
    pixeles, lado = cuadrar(pixeles, ancho, alto)
    if lado != ancho or lado != alto:
        origen += f" -> cuadrado {lado}x{lado}"
    ancho = alto = lado

    base = ancho
    imagenes = []
    for t in TAMANOS:
        if t > base and t != max(TAMANOS):
            continue
        chico = redimensionar(pixeles, base, min(t, base))
        imagenes.append((min(t, base), escribir_png(chico, min(t, base), min(t, base))))

    # sin duplicados de tamano
    vistos, unicas = set(), []
    for lado, png in imagenes:
        if lado not in vistos:
            vistos.add(lado)
            unicas.append((lado, png))

    escribir_ico(unicas, SALIDA)
    print(f"  Icono creado: {SALIDA}")
    print(f"  Origen: {origen}")
    print(f"  Resoluciones: {', '.join(str(l) for l, _ in unicas)} px")
    print(f"  Tamano: {SALIDA.stat().st_size / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
