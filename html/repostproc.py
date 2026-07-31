#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-aplica postproc a los HTML ya generados."""
import os
import sys
sys.path.insert(0, '/home/volaya/sources/libro_ud/html')
os.chdir('/home/volaya/sources/libro_ud/html')
import convert

for fname in os.listdir(convert.CHAPTERS_DIR):
    if not fname.endswith('.html'):
        continue
    p = os.path.join(convert.CHAPTERS_DIR, fname)
    with open(p, encoding='utf-8') as fh:
        h = fh.read()
    h = convert.postproc(h)
    with open(p, 'w', encoding='utf-8') as fh:
        fh.write(h)
    print('Repostprocesado:', fname)
