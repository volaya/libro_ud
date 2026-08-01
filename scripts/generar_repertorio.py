#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import glob as globmod
import os
import re
import subprocess
import sys
import tempfile
from PIL import Image, ImageChops, ImageOps

DEFAULT_HTML_IMG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "html", "img")
DEFAULT_INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "libro", "capitulos", "repertorio")
ARABIC_LY = "/usr/share/lilypond/2.22.1/ly/arabic.ly"
LILYPOND_BLOCK_RE = re.compile(r'\\begin\{lilypond\}.*?(.*?)\\end\{lilypond\}', re.DOTALL)

def has_magic(s):
    return any(c in s for c in "*?[")

def content_bbox(img):
    rgb = img.convert("RGB")
    white = Image.new("RGB", rgb.size, (255, 255, 255))
    diff = ImageChops.difference(rgb, white)
    return diff.getbbox()

def find_bottom_text_top(img, threshold, step):
    gray = img.convert("L")
    width, height = gray.size
    pixels = list(gray.getdata())
    def row_is_dark(y):
        start = y * width
        for x in range(0, width, step):
            if pixels[start + x] < threshold:
                return True
        return False
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
    for s, e in reversed(bands):
        if s > 0 and (e - s + 1) <= height * 0.25:
            return s
    return None

def crop_lilypond(img, threshold=200, step=2, padding=0):
    bbox = content_bbox(img)
    if bbox is not None:
        img = img.crop(bbox)
    bottom = find_bottom_text_top(img, threshold, step)
    if bottom is not None:
        img = img.crop((0, 0, img.width, bottom))
    bbox = content_bbox(img)
    if bbox is not None:
        img = img.crop(bbox)
    if padding:
        img = ImageOps.expand(img, border=padding, fill=(255, 255, 255))
    return img

def extract_lilypond_blocks(tex_path):
    with open(tex_path, encoding="utf-8") as f:
        text = f.read()
    blocks = []
    for m in LILYPOND_BLOCK_RE.finditer(text):
        body = m.group(1)
        body = re.sub(r'\\emph\{([^}]*)\}', r'\1', body)
        body = re.sub(r'\\textsc\{([^}]*)\}', r'\1', body)
        body = re.sub(r'\\resizebox\{[^}]*\}\{[^}]*\}\{', '', body)
        body = re.sub(r'\\begin\{center\}', '', body)
        body = re.sub(r'\\end\{center\}', '', body)
        body = body.replace('\\hflat', '\\flat')
        body = body.replace('\\dsharp', '\\sharp')
        open_braces = body.count('{')
        close_braces = body.count('}')
        if open_braces > close_braces:
            body += '}' * (open_braces - close_braces)
        blocks.append(body)
    return blocks

def compile_lilypond_block(block_code, tmpdir, index):
    ly_content = (
        '\version "2.22.1"\n'
        + block_code + "\n"
    )
    ly_path = os.path.join(tmpdir, f"repertorio_{index:03d}.ly")
    with open(ly_path, "w", encoding="utf-8") as f:
        f.write(ly_content)
    proc = subprocess.run(
        ["lilypond", "--png", "-o", os.path.join(tmpdir, f"repertorio_{index:03d}"), ly_path],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(f"  [lilypond stderr] {proc.stderr[:500]}", file=sys.stderr)
    png_path = os.path.join(tmpdir, f"repertorio_{index:03d}.png")
    png_alt = os.path.join(tmpdir, f"repertorio_{index:03d}.page1.png")
    if os.path.exists(png_path):
        return png_path
    if os.path.exists(png_alt):
        return png_alt
    return None


def collect_files(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            files.extend(sorted(
                os.path.join(p, f) for f in os.listdir(p)
                if f.lower().endswith(".tex")
            ))
        elif has_magic(p):
            files.extend(sorted(globmod.glob(p)))
        else:
            files.append(p)
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
        description="Genera PNG de partituras del capítulo de repertorio.")
    parser.add_argument("paths", nargs="*",
                        help="ficheros .tex, directorios o patrones glob")
    parser.add_argument("--outdir", default=None,
                        help="directorio donde guardar los PNG")
    parser.add_argument("--dry-run", action="store_true",
                        help="solo mostrar qué se haría sin escribir nada")
    parser.add_argument("--threshold", type=int, default=200,
                        help="brillo máximo para tinta (0-255)")
    parser.add_argument("--step", type=int, default=2,
                        help="muestreo horizontal al analizar filas")
    args = parser.parse_args(argv)

    if args.paths:
        tex_files = collect_files(args.paths)
    else:
        tex_files = sorted(globmod.glob(
            os.path.join(DEFAULT_INPUT_DIR, "*.tex")))

    if not tex_files:
        print("No se encontraron ficheros .tex de repertorio.")
        return 1

    outdir = args.outdir or DEFAULT_HTML_IMG
    if not args.dry_run:
        os.makedirs(outdir, exist_ok=True)

    tasks = []
    for tex_path in tex_files:
        if not os.path.exists(tex_path):
            print(f"Aviso: {tex_path} no existe, se salta.")
            continue
        blocks = extract_lilypond_blocks(tex_path)
        for i, code in enumerate(blocks, 1):
            tasks.append((tex_path, i, code))

    if not tasks:
        print("No se encontraron bloques \\begin{lilypond} en los ficheros.")
        return 1

    print(f"Encontradas {len(tasks)} partituras en {len(tex_files)} ficheros.")

    processed = 0
    errors = 0
    global_index = 1

    with tempfile.TemporaryDirectory(prefix="lilypond_repertorio_") as tmpdir:
        for tex_path, block_index, block_code in tasks:
            base_name = f"lilypond-repertorio-{global_index:03d}"
            dest = os.path.join(outdir, base_name + ".png")
            if args.dry_run:
                print(f"[dry-run] {tex_path} (bloque {block_index}) -> {dest}")
                processed += 1
                global_index += 1
                continue
            try:
                png_src = compile_lilypond_block(block_code, tmpdir, block_index)
                if png_src is None:
                    print(
                        f"Error: no se generó PNG para {tex_path} bloque {block_index}",
                        file=sys.stderr,
                    )
                    errors += 1
                    continue
                with Image.open(png_src) as img:
                    result = crop_lilypond(img, args.threshold, args.step)
                result.save(dest, "PNG")
                print(f"OK: {dest} ({result.width}x{result.height})")
                processed += 1
                global_index += 1
            except Exception as exc:
                print(
                    f"Error en {tex_path} bloque {block_index}: {exc}",
                    file=sys.stderr,
                )
                errors += 1

    print(f"\\nProcesadas: {processed} correctas, {errors} con error.")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
