import re
import os.path
import shutil
from subprocess import call

LILYPONDPATH = r"C:\Program Files (x86)\LilyPond\usr\bin" 
PYTHONPATH = os.path.join("LILYPONDPATH", "python.exe")
LILYPONBDBOOKPATH = os.path.join(LILYPONDPATH, "lilypond-book.py")
BOOKPATH = os.path.join(os.dirname(os.path.dirname(__file__)), "libro", "libro.lytex")
OUTPUTTEXFILE = os.path.join(os.dirname(os.path.dirname(__file__)), "libro", "output", "libro.tex")

call([PYTHONPATH, LILYPONBDBOOKPATH, BOOKPATH, "--pdf", "output"])
call(["pdflatex", OUTPUTTEXFILE])
