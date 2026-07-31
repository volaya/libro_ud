#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convierte el libro LaTeX + LilyPond (en ../libro) a un libro HTML en este directorio.
"""
import os
import re
import subprocess
import html as htmlmod
import shutil
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, '..', 'libro')
OUT_DIR = BASE_DIR
IMG_DIR = os.path.join(OUT_DIR, 'img')
CHAPTERS_DIR = os.path.join(OUT_DIR, 'chapters')
TEMPLATE = os.path.join(OUT_DIR, 'template.html')
IMAGENES_DIR = os.path.join(INPUT_DIR, 'imagenes')

CHAPTERS = [
    ('capitulos/elud/elud.tex', 'El ud'),
    ('capitulos/musicaarabe/musicaarabe.tex', 'La música árabe'),
    ('capitulos/maqam/maqam.tex', 'El maqam'),
    ('capitulos/ornamentacion/ornamentacion.tex', 'Ornamentación'),
    ('capitulos/taqsim/taqsim.tex', 'Taqsim'),
]

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
    try:
        p = subprocess.run(cmd, capture_output=True, cwd=cwd)
        return (p.returncode == 0, p.stdout.decode('utf-8', 'replace'),
                p.stderr.decode('utf-8', 'replace'))
    except FileNotFoundError as exc:
        return (False, '', str(exc))


def read_inputs(fp, seen=None):
    if seen is None:
        seen = set()
    real = os.path.realpath(fp)
    if real in seen:
        return ''
    seen.add(real)
    with open(fp, encoding='utf-8') as fh:
        content = fh.read()

    def repl(m):
        rel = m.group(1)
        cand = os.path.join(os.path.dirname(fp), rel)
        if not os.path.exists(cand):
            cand = os.path.join(INPUT_DIR, rel)
        if os.path.exists(cand):
            return read_inputs(cand, seen)
        return ''
    return re.sub(r'\\input\{([^}]+)\}', repl, content)


def compile_lilypond(code, out_png, workdir):
    """Compila un bloque de LilyPond a PNG y lo recorta. Devuelve True si OK."""
    job = os.path.splitext(out_png)[0]
    ly_name = os.path.basename(job)
    ly = os.path.join(workdir, ly_name + '.ly')
    with open(ly, 'w', encoding='utf-8') as fh:
        fh.write(code)
    run(['lilypond', '--png', '-dresolution=200', '-o',
         os.path.join(workdir, ly_name), ly], cwd=workdir)
    produced = os.path.join(workdir, ly_name + '.png')
    result = os.path.exists(produced)
    if result:
        shutil.copy(produced, out_png)
        trim_lilypond_png(out_png)
    for ext in ('.ly', '.png', '.pdf', '-1.png', '-systems.tex',
                '-systems.count', '-systems.texi'):
        p = os.path.join(workdir, ly_name + ext)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    return result


def compile_tikz(code, out_png, workdir):
    name = os.path.splitext(os.path.basename(out_png))[0]
    tex = os.path.join(workdir, name + '.tex')
    body = code
    body = body.replace(r'\hflat',
                        r'$\raisebox{-.1ex}{\textsf{\tiny b}\hspace{-.3em}}$')
    body = body.replace(r'\dsharp', r'$\sharp$')
    body = re.sub(r'\\emph\{([^}]*)\}', r'\1', body)
    body = re.sub(r'\\textsc\{([^}]*)\}', r'\1', body)
    body = re.sub(r'\\resizebox\{[^}]*\}\{[^}]*\}\{', '', body)
    body = body.replace(r'\begin{center}', '').replace(r'\end{center}', '')
    depth = 0
    cleaned = []
    for ch in body:
        if ch == '{':
            depth += 1
            cleaned.append(ch)
        elif ch == '}':
            if depth > 0:
                depth -= 1
                cleaned.append(ch)
        else:
            cleaned.append(ch)
    body = ''.join(cleaned)
    with open(tex, 'w', encoding='utf-8') as fh:
        fh.write(TIKZ_PREAMBLE + body + '\n\\end{document}\n')
    run(['pdflatex', '-interaction=nonstopmode', name + '.tex'], cwd=workdir)
    pdf = os.path.join(workdir, name + '.pdf')
    result = False
    if os.path.exists(pdf):
        run(['pdftoppm', '-png', '-r', '200', pdf,
             os.path.join(workdir, name)], cwd=workdir)
        cand = os.path.join(workdir, name + '-1.png')
        if not os.path.exists(cand):
            cand = os.path.join(workdir, name + '.png')
        if os.path.exists(cand):
            shutil.copy(cand, out_png)
            trim_simple_png(out_png)
            result = True
    for ext in ('.tex', '.pdf', '.aux', '.log', '-1.png', '.png'):
        p = os.path.join(workdir, name + ext)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    return result


def trim_simple_png(png_path):
    """Recorta bordes blancos de una PNG genérica (para tikz)."""
    try:
        from PIL import Image, ImageOps
    except ImportError:
        return
    img = Image.open(png_path).convert('RGBA')
    inverted = Image.new('RGB', img.size, (0, 0, 0))
    inverted.paste(img.convert('RGB'), mask=img.split()[-1])
    inv = ImageOps.invert(inverted)
    bbox = inv.getbbox()
    if bbox and bbox != (0, 0, img.size[0], img.size[1]):
        img = img.crop(bbox)
        img.save(png_path, 'PNG')


def preproc(content, base_name):
    workdir = os.path.join(IMG_DIR, '_work')
    os.makedirs(workdir, exist_ok=True)
    score_counter = [0]

    def lily_sub(m):
        score_counter[0] += 1
        code = m.group(1)
        png_name = 'lilypond-{}-{:03d}.png'.format(base_name, score_counter[0])
        png_path = os.path.join(IMG_DIR, png_name)
        if compile_lilypond(code, png_path, workdir):
            return '@@IMG@@../img/{}@@ENDIMG@@'.format(png_name)
        return ''
    content = re.sub(r'\\begin\{lilypond\}([\s\S]*?)\\end\{lilypond\}',
                     lily_sub, content)

    tikz_counter = [0]

    def tikz_sub(m):
        tikz_counter[0] += 1
        code = m.group(1)
        png_name = 'tikz-{}-{:03d}.png'.format(base_name, tikz_counter[0])
        png_path = os.path.join(IMG_DIR, png_name)
        if compile_tikz(code, png_path, workdir):
            return '@@IMG@@../img/{}@@ENDIMG@@'.format(png_name)
        return ''
    content = re.sub(r'\\begin\{tikzpicture\}([\s\S]*?)\\end\{tikzpicture\}',
                     tikz_sub, content)
    content = re.sub(r'\\begin\{center\}\s*(@@IMG@@[^@]*@@ENDIMG@@)\s*\\end\{center\}',
                     r'\1', content)
    content = re.sub(r'\\begin\{samepage\}', '', content)
    content = re.sub(r'\\end\{samepage\}', '', content)
    return content


def replace_custom_commands(content):
    content = content.replace(r'\hflat', '\u266D\u00BD')
    content = content.replace(r'\dsharp', '\u266F')
    content = re.sub(r'\\upbow\b', '\u2191', content)
    content = re.sub(r'\\downbow\b', '\u2193', content)
    emph_cmds = ['yins', 'yinsb', 'Yins', 'ashnas', 'ashnasb', 'maqamaat',
                 'maqamaatb', 'maqam', 'maqamb', 'Maqam', 'taqsim', 'taqsimb',
                 'taqasim', 'taqasimb']
    for cmd in emph_cmds:
        content = re.sub(r'\\' + cmd + r'\b',
                         r'\\emph{' + cmd + '}', content)
    return content

def postproc(h):
    h = htmlmod.unescape(h)

    def marker_img(m):
        src = m.group(1)
        return '<img src="{}" style="display:block;margin:1em auto;max-width:100%;" />'.format(src)

    h = re.sub(r'@@IMG@@([^@]+\.png)@@ENDIMG@@', marker_img, h)

    def fix_static_img(m):
        tag = m.group(0)
        src = m.group(1)
        if src.startswith(('../', 'http', '/', 'data:')):
            return tag
        new_src = '../img/' + src
        return tag.replace('src="%s"' % src, 'src="%s"' % new_src)

    h = re.sub(r'<img[^>]*src="([^"]+)"[^>]*/>', fix_static_img, h)

    def song(m):
        return ('<div class="songheader" style="text-align:center;margin:1.5em 0;">'
                '<h2 style="margin:0;">{0}</h2>'
                '<p style="margin:0;">{1}</p>'
                '<p style="margin:0;"><em>Maqam: {2}</em></p></div>').format(
                    m.group(1), m.group(2), m.group(3))

    h = re.sub(r'\\songheader\{([^}]+)\}\{([^}]+)\}\{([^}]+)\}', song, h)

    def img(m):
        path = m.group(2)
        m2 = re.search(r'width=([0-9.]+)\\textwidth', m.group(1))
        if m2:
            w = str(round(float(m2.group(1)) * 100)) + '%'
        else:
            w = '100%'
        fname = os.path.basename(path)
        return '<img src="../img/{0}" width="{1}" style="display:block;margin:1em auto;" />'.format(fname, w)

    h = re.sub(r'\\includegraphics\[([^\]]*)\]\{([^}]+)\}', img, h)
    h = re.sub(r'\\includegraphics\{([^}]+)\}',
               '<img src="../img/\1" style="display:block;margin:1em auto;" />', h)

    h = re.sub(r'\\audioclip\{[^}]*\}', '', h)
    h = re.sub(r'\\textsc\{([^}]*)\}', r'<span style="font-variant:small-caps;">\1</span>', h)
    h = re.sub(r'\\ref\{[^}]*\}', '', h)
    h = re.sub(r'\\label\{[^}]*\}', '', h)
    h = h.replace('\266D', '♭').replace('\2191', '↑').replace('\2193', '↓')

    return h




def trim_lilypond_png(png_path):
    """Recorta el banner 'engraved by lilypond' y espacios en blanco de una PNG."""
    try:
        from PIL import Image
    except ImportError:
        return
    img = Image.open(png_path).convert('RGBA')
    w, h = img.size

    # 1. Recortar bordes blancos exteriores con getbbox (invirtiendo colores).
    inverted = Image.new('RGB', img.size, (0, 0, 0))
    inverted.paste(img.convert('RGB'), mask=img.split()[-1])  # usar alpha como mask
    from PIL import ImageOps
    inv = ImageOps.invert(inverted)
    bbox = inv.getbbox()
    if bbox:
        img = img.crop(bbox)
        w, h = img.size

    # 2. Recortar el texto 'engraved by lilypond' en la base.
    #    El texto grisáceo aparece en la última fracción de la imagen.
    #    Analizamos la zona inferior píxel a píxel.
    cut_h = max(int(h * 0.10), 1)
    bottom = img.crop((0, h - cut_h, w, h))
    pix = bottom.load()
    cut_from = None
    for y in range(cut_h - 1, -1, -1):
        all_white = True
        for x in range(0, w, 3):
            px = pix[x, y]
            if px[0] < 250 or px[1] < 250 or px[2] < 252:
                all_white = False
                break
        if not all_white:
            cut_from = y
            break
    if cut_from is not None and cut_from < cut_h - 2:
        keep = h - cut_h + cut_from
        img = img.crop((0, 0, w, keep))
    img.save(png_path, 'PNG')


