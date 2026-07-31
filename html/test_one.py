#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueba la conversión de un solo capítulo para diagnosticar."""
import os
import sys
sys.path.insert(0, '/home/volaya/sources/libro_ud/html')
os.chdir('/home/volaya/sources/libro_ud/html')

import convert

# Probar solo el capítulo de ornamentación (el más corto)
relpath = 'capitulos/ornamentacion/ornamentacion.tex'
title = 'Ornamentación'
tex_path = os.path.join(convert.INPUT_DIR, relpath)
base_name = 'ornamentacion'
print('Procesando:', title)

expanded = convert.read_inputs(tex_path)
print('Longitud tras expandir input:', len(expanded))
expanded = convert.replace_custom_commands(expanded)
print('Longitud tras sustituir comandos:', len(expanded))
expanded = convert.preproc(expanded, base_name)
print('Longitud tras preproc:', len(expanded))

tmp_tex = os.path.join(convert.IMG_DIR, '_work', base_name + '_preproc.tex')
os.makedirs(os.path.dirname(tmp_tex), exist_ok=True)
with open(tmp_tex, 'w', encoding='utf-8') as fh:
    fh.write(expanded)

out_html = os.path.join(convert.CHAPTERS_DIR, base_name + '.html')
ok, o, e = convert.run(['pandoc', '--from', 'latex', '--to', 'html5',
                         '--standalone', '--template', convert.TEMPLATE,
                         '--metadata', 'title=' + title,
                         '--output', out_html, tmp_tex])
print('Pandoc ok:', ok)
if not ok:
    print('Pandoc stderr:', e[:1000])

with open(out_html, encoding='utf-8') as fh:
    h = fh.read()
h = convert.postproc(h)
with open(out_html, 'w', encoding='utf-8') as fh:
    fh.write(h)
print('HTML generado. Imágenes en el HTML:', h.count('<img'))
print('Hecho.')
