#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recorta las imágenes de partitura generadas por LilyPond para quedarse
únicamente con el pentagrama (la parte superior de la imagen).

Las imágenes generadas por LilyPond tienen esta estructura:

    +------------------------------------+
    |             pentagrama             |  <- se conserva
    |                                    |
    |         (espacio en blanco)        |  <- se elimina
    |                                    |
    |    engraved by LilyPond v2.24.x    |  <- texto del pie, se elimina
    +------------------------------------+

El script:
  1. Elimina los márgenes blancos exteriores de la imagen.
  2. Localiza la banda de texto inferior ("engraved by LilyPond").
  3. Recorta la imagen por encima de esa banda.
  4. Elimina el espacio en blanco sobrante que queda bajo el pentagrama.

Uso:
    python3 recortar_partituras.py [opciones] [rutas...]

    rutas:
        Ficheros .png, directorios o patrones glob. Si no se indica
        ninguna ruta, se procesan todos los "lilypond-*.png" del
        directorio html/img del libro.

Opciones:
    --outdir DIR     Guarda los recortes en DIR en lugar de sobrescribir
                     el fichero original.
    --threshold N    Brillo máximo (0-255) para considerar un píxel como
                     "tinta". Por defecto 200.
    --step N         Muestreo horizontal al analizar cada fila. Por
                     defecto 2.
    --padding N      Margen blanco en píxeles alrededor del pentagrama.
                     Por defecto 0.
    --dry-run        Muestra qué se haría sin modificar ningún fichero.
"""

import argparse
import glob as globmod
import os
import sys

from PIL import Image, ImageChops, ImageOps


# Directorio de imágenes del libro HTML, relativo a la carpeta de scripts.
DEFAULT_HTML_IMG = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "html", "img",
)


def has_magic(s):
    """Devuelve True si `s` contiene metacaracteres de glob."""
    return any(c in s for c in "*?[")


def content_bbox(img):
    """
    Devuelve la caja (left, top, right, bottom) de los píxeles que no son
    blancos, o None si la imagen es completamente blanca.
    """
    rgb = img.convert("RGB")
    white = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, white)
    return diff.getbbox()


def find_bottom_text_top(img, threshold, step):
    """
    Busca el bloque de texto inferior ("engraved by LilyPond").

    Devuelve la coordenada y de la primera fila de ese bloque, o None si
    no se detecta ningún bloque que se parezca a un texto de pie.
    """
    gray = img.convert("L")
    width, height = gray.size
    pixels = list(gray.getdata())

    def row_is_dark(y):
        """¿Contiene la fila `y` algún píxel más oscuro que `threshold`?"""
        start = y * width
        for x in range(0, width, step):
            if pixels[start + x] < threshold:
                return True
        return False

    # Agrupar las filas oscuras consecutivas en bandas.
    bands = []
    in_band = False
    start = 0
    for y in range(height):
        dark = row_is_dark(y)
        if dark and not in_band:
            in_band = True
            start = y
        elif not dark and in_band:
            bands.append((start, y - 1))
            in_band = False
    if in_band:
        bands.append((start, height - 1))

    if not bands:
        return None

    # La banda más baja es la candidata a texto del pie.
    top, bottom = bands[-1]

    # El texto del pie no debe arrancar en la fila 0: ahí está el
    # pentagrama, que no se debe recortar.
    if top <= 0:
        return None

    # El texto es una línea pequeña; una banda demasiado alta no es texto.
    if (bottom - top + 1) > height * 0.25:
        return None

    return top


def crop_lilypond(img, threshold=200, step=2, padding=0):
    """
    Recorta la imagen para quedarse solo con el pentagrama superior.

    Devuelve una nueva imagen en modo RGB.
    """
    # Normalizar: aplanar la transparencia sobre fondo blanco.
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        background.alpha_composite(img)
        img = background
    img = img.convert("RGB")

    # 1) Quitar los márgenes blancos exteriores: quedan pentagrama + texto.
    bbox = content_bbox(img)
    if bbox is None:
        return img
    img = img.crop(bbox)

    # 2) Recortar por encima del texto del pie.
    text_top = find_bottom_text_top(img, threshold, step)
    if text_top is not None:
        img = img.crop((0, 0, img.width, text_top))

    # 3) Quitar el espacio en blanco que quedaba bajo el pentagrama.
    bbox = content_bbox(img)
    if bbox is not None:
        img = img.crop(bbox)

    # 4) Margen blanco opcional alrededor del resultado.
    if padding:
        img = ImageOps.expand(img, border=padding, fill=(255, 255, 255))

    return img


def collect_files(paths):
    """Expande ficheros, directorios y patrones glob a una lista de .png."""
    files = []
    for p in paths:
        if os.path.isdir(p):
            files.extend(sorted(
                os.path.join(p, f) for f in os.listdir(p)
                if f.lower().endswith(".png")
            ))
        elif has_magic(p):
            files.extend(sorted(globmod.glob(p)))
        else:
            files.append(p)

    # Eliminar duplicados conservando el orden.
    seen = set()
    unique = []
    for f in files:
        key = os.path.abspath(f)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Recorta las imágenes de partitura de LilyPond "
                    "(elimina el espacio en blanco y el texto "
                    "'engraved by LilyPond' inferior).")
    parser.add_argument(
        "paths", nargs="*",
        help="ficheros .png, directorios o patrones glob")
    parser.add_argument("--outdir", default=None,
                        help="directorio donde guardar los recortes")
    parser.add_argument("--threshold", type=int, default=200,
                        help="brillo máximo para considerar un píxel "
                             "como tinta (0-255)")
    parser.add_argument("--step", type=int, default=2,
                        help="muestreo horizontal al analizar cada fila")
    parser.add_argument("--padding", type=int, default=0,
                        help="margen blanco alrededor del pentagrama")
    parser.add_argument("--dry-run", action="store_true",
                        help="solo mostrar las acciones, sin escribir nada")
    args = parser.parse_args(argv)

    if args.paths:
        files = collect_files(args.paths)
    else:
        files = sorted(globmod.glob(
            os.path.join(DEFAULT_HTML_IMG, "lilypond-*.png")))

    if not files:
        print("No se encontraron imágenes que procesar.")
        return 1

    if args.outdir and not args.dry_run:
        os.makedirs(args.outdir, exist_ok=True)

    processed = 0
    errors = 0
    for src in files:
        dest = (os.path.join(args.outdir, os.path.basename(src))
                if args.outdir else src)
        if args.dry_run:
            print("[dry-run] {0} -> {1}".format(src, dest))
            processed += 1
            continue
        try:
            with Image.open(src) as img:
                result = crop_lilypond(
                    img, args.threshold, args.step, args.padding)
            result.save(dest, "PNG")
            print("Recortada: {0} -> {1} ({2}x{3})".format(
                src, dest, result.width, result.height))
            processed += 1
        except Exception as exc:
            print("Error en {0}: {1}".format(src, exc), file=sys.stderr)
            errors += 1

    print("\nProcesadas: {0} correctas, {1} con error.".format(
        processed, errors))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

