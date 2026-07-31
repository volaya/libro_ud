#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genera los PNG con los esquemas de diapasón (diagramas del mástil del ud)
a partir del código TikZ de los capítulos del libro.

Los esquemas de diapasón están definidos como bloques ``tikzpicture``
dentro de los ficheros .tex de los capítulos (p. ej.
``libro/capitulos/maqam/nahawand.tex``). El script expande los
``\\input{...}`` del capítulo, extrae los bloques en orden y compila cada
uno de ellos por separado:

    1. Se escribe un documento standalone con el preámbulo TikZ (que
       incluye la macro \\fretboard) y el bloque envuelto en
       ``\\begin{tikzpicture} ... \\end{tikzpicture}``.
    2. Se compila con pdflatex.
    3. Se convierte el PDF a PNG con pdftoppm.
    4. Se recortan los márgenes blancos.

Los PNG se nombran ``tikz-<base>-<NNN>.png`` (p. ej. ``tikz-maqam-001.png``)
en el directorio de salida, siguiendo la misma numeración que usa el
conversor HTML del libro.

Uso:
    python3 generar_diapasones.py [opciones] [fichero.tex ...]

    Si no se indica ningún fichero, se procesa el capítulo de maqam
    (``libro/capitulos/maqam/maqam.tex``).

Opciones:
    --outdir DIR     Directorio de salida para los PNG. Por defecto
                     ``html/img`` (relativo a la raíz del libro).
    --workdir DIR    Directorio de trabajo temporal. Por defecto usa
                     ``tempfile.mkdtemp()``.
    --keep-workdir   No elimina el directorio de trabajo temporal.
    --base NOMBRE    Prefijo de los PNG. Por defecto se deduce del nombre
                     del fichero .tex (p. ej. ``maqam`` -> ``tikz-maqam-001.png``).
    --dpi N          Resolución de salida de pdftoppm. Por defecto 200.
    --force          Regenera las imágenes aunque ya existan.
    --dry-run        Muestra las acciones sin escribir nada.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageChops


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TEX = os.path.join(ROOT, "libro", "capitulos", "maqam", "maqam.tex")
DEFAULT_OUTDIR = os.path.join(ROOT, "html", "img")


FRETBOARD_MACRO = r"""
\newcommand{\fretboard} {
\begin{scope}[xscale=-15,yscale=.2,line width=.5]
    \xdef\x{1}
    \draw[line width=1.5] (1,.56) -- (1,6.44);
    \foreach \fret in {0,...,10}{
      \foreach \str in {1,...,6}{
        \coordinate (\str-\fret) at (\x,\str);
      }
      \pgfmathsetmacro\x{\x * 0.97193715634}
      \xdef\x{\x}
      \ifthenelse{\isodd{\fret}} {\draw (\x,.95) -- (\x,6.05);}{}
    }
    \foreach \str in {1,...,6}{
      \draw [line width=0.2](1,\str-.05) -- (0.97153194115*\x,\str-.05);
      \draw [line width=0.2](1,\str+.05) -- (0.97153194115*\x,\str+.05);
    }
      \draw[line width=1] (1,0.65) -- (0.97153194115*\x,0.65);
      \draw[line width=1] (1,6.35) -- (0.97153194115*\x,6.35);
  \end{scope}
}
"""

TIKZ_PREAMBLE = (
    r"\documentclass[border=2pt]{standalone}" "\n"
    r"\usepackage{tikz}" "\n"
    r"\usetikzlibrary{calc,arrows}" "\n"
    r"\usepackage{ifthen}" "\n"
    r"\usepackage{amsmath}" "\n"
    + FRETBOARD_MACRO +
    r"\begin{document}" "\n"
)

def run(cmd, cwd=None):
    """Ejecuta un comando y devuelve (ok, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, capture_output=True, cwd=cwd)
        return (p.returncode == 0,
                p.stdout.decode("utf-8", "replace"),
                p.stderr.decode("utf-8", "replace"))
    except FileNotFoundError:
        return (False, "", "comando no encontrado: " + cmd[0])


def read_inputs(fp, seen=None):
    """Expande recursivamente los ``\\input{...}`` de un fichero .tex."""
    if seen is None:
        seen = set()
    real = os.path.realpath(fp)
    if real in seen:
        return ""
    seen.add(real)
    with open(fp, encoding="utf-8") as fh:
        content = fh.read()

    def repl(m):
        rel = m.group(1)
        cand = os.path.join(os.path.dirname(fp), rel)
        if not os.path.exists(cand):
            cand = os.path.join(ROOT, "libro", rel)
        if os.path.exists(cand):
            return read_inputs(cand, seen)
        return ""

    return re.sub(r"\\input\{([^}]+)\}", repl, content)


def extract_tikz_blocks(content):
    """Devuelve los bloques ``tikzpicture`` en orden de aparición."""
    return re.findall(r"\\begin\{tikzpicture\}([\s\S]*?)\\end\{tikzpicture\}",
                      content)


def prepare_body(code):
    """Aplica al cuerpo del bloque las sustituciones de macros necesarias."""
    body = code
    body = body.replace(
        r"\hflat",
        r"$\raisebox{-.1ex}{\textsf{\tiny b}\hspace{-.3em}}$")
    body = body.replace(r"\dsharp", r"$\sharp$")
    body = re.sub(r"\\emph\{([^}]*)\}", r"\1", body)
    body = re.sub(r"\\textsc\{([^}]*)\}", r"\1", body)
    body = re.sub(r"\\resizebox\{[^}]*\}\{[^}]*\}\{", "", body)
    body = body.replace(r"\begin{center}", "").replace(r"\end{center}", "")

    # Equilibrar llaves (elimina llaves huérfanas de \resizebox, etc.)
    depth = 0
    cleaned = []
    for ch in body:
        if ch == "{":
            depth += 1
            cleaned.append(ch)
        elif ch == "}":
            if depth > 0:
                depth -= 1
                cleaned.append(ch)
        else:
            cleaned.append(ch)
    return "".join(cleaned)


def trim_white(png_path):
    """Recorta los márgenes blancos exteriores de una imagen PNG."""
    img = Image.open(png_path).convert("RGB")
    white = Image.new("RGB", img.size, (255, 255, 255))
    bbox = ImageChops.difference(img, white).getbbox()
    if bbox and bbox != (0, 0, img.size[0], img.size[1]):
        img.crop(bbox).save(png_path, "PNG")


def compile_tikz(code, out_png, workdir, dpi):
    """
    Compila un bloque ``tikzpicture`` a PNG.

    Devuelve True si el proceso completo (pdflatex + pdftoppm) tiene éxito.
    """
    name = os.path.splitext(os.path.basename(out_png))[0]
    tex_path = os.path.join(workdir, name + ".tex")
    body = prepare_body(code)

    with open(tex_path, "w", encoding="utf-8") as fh:
        fh.write(TIKZ_PREAMBLE + "\\begin{tikzpicture}" + body
                 + "\n\\end{tikzpicture}\n\n\\end{document}\n")

    ok, _out, _err = run(
        ["pdflatex", "-interaction=nonstopmode", os.path.basename(tex_path)],
        cwd=workdir)
    pdf_path = os.path.join(workdir, name + ".pdf")
    if not ok or not os.path.exists(pdf_path):
        return False

    ok, _out, _err = run(
        ["pdftoppm", "-png", "-r", str(dpi), pdf_path,
         os.path.join(workdir, name)], cwd=workdir)
    cand = os.path.join(workdir, name + "-1.png")
    if not os.path.exists(cand):
        cand = os.path.join(workdir, name + ".png")
    if not os.path.exists(cand):
        return False

    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    shutil.copy(cand, out_png)
    trim_white(out_png)

    for ext in (".tex", ".pdf", ".aux", ".log", "-1.png", ".png"):
        p = os.path.join(workdir, name + ext)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Genera los PNG de los esquemas de diapasón a partir "
                    "del código TikZ de los capítulos del libro.")
    parser.add_argument(
        "texfiles", nargs="*",
        help="ficheros .tex de capítulo (por defecto el capítulo de maqam)")
    parser.add_argument("--outdir", default=DEFAULT_OUTDIR,
                        help="directorio de salida para los PNG")
    parser.add_argument("--workdir", default=None,
                        help="directorio de trabajo temporal")
    parser.add_argument("--keep-workdir", action="store_true",
                        help="conservar el directorio de trabajo temporal")
    parser.add_argument("--base", default=None,
                        help="prefijo para los nombres de los PNG")
    parser.add_argument("--dpi", type=int, default=200,
                        help="resolución de pdftoppm (por defecto 200)")
    parser.add_argument("--force", action="store_true",
                        help="regenerar aunque los PNG ya existan")
    parser.add_argument("--dry-run", action="store_true",
                        help="mostrar las acciones sin escribir nada")
    args = parser.parse_args(argv)

    texfiles = args.texfiles or [DEFAULT_TEX]

    if args.workdir:
        workdir = args.workdir
        os.makedirs(workdir, exist_ok=True)
        own_tmp = False
    else:
        tmp = tempfile.mkdtemp(prefix="diapasones_")
        workdir = tmp
        own_tmp = True

    generated = 0
    skipped = 0
    errors = 0
    try:
        for tex in texfiles:
            if not os.path.exists(tex):
                print("No existe el fichero: {0}".format(tex),
                      file=sys.stderr)
                errors += 1
                continue

            base = args.base or os.path.splitext(os.path.basename(tex))[0]
            content = read_inputs(tex)
            blocks = extract_tikz_blocks(content)
            if not blocks:
                print("No se encontraron bloques tikzpicture en {0}".format(tex))
                continue

            print("{0}: {1} esquemas de diapasón".format(tex, len(blocks)))
            for i, code in enumerate(blocks, start=1):
                png_name = "tikz-{0}-{1:03d}.png".format(base, i)
                out_png = os.path.join(args.outdir, png_name)
                if args.dry_run:
                    print("  [dry-run] {0}".format(png_name))
                    generated += 1
                    continue
                if os.path.exists(out_png) and not args.force:
                    print("  omitido (ya existe): {0}".format(png_name))
                    skipped += 1
                    continue
                if compile_tikz(code, out_png, workdir, args.dpi):
                    print("  generado: {0}".format(png_name))
                    generated += 1
                else:
                    print("  ERROR compilando: {0}".format(png_name),
                          file=sys.stderr)
                    errors += 1
    finally:
        if own_tmp and not args.keep_workdir:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\nGenerados: {0}, omitidos: {1}, errores: {2}.".format(
        generated, skipped, errors))
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

