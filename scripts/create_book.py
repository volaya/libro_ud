import json
import os
from subprocess import call

LILYPONDPATH = r"C:\Program Files (x86)\LilyPond\usr\bin"
PYTHONPATH = os.path.join(LILYPONDPATH, "python.exe")
LILYPONBDBOOKPATH = os.path.join(LILYPONDPATH, "lilypond-book.py")
BOOKPATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "libro")

FRETS = 11

def run_lilypond():
    os.chdir(BOOKPATH)
    call([PYTHONPATH, LILYPONBDBOOKPATH, "--pdf", "--output", "output", "libro.lytex"])


def run_latex():
    os.chdir(os.path.join(BOOKPATH, "output"))
    call(["pdflatex", "libro.tex"])


diagram_template = r'''
\begin{center}
\resizebox{.8\textwidth}{!}{
\begin{tikzpicture}[
    ynode/.style={scale=.35,inner sep=1pt}]
  \fretboard
%s
\end{tikzpicture}
}
\end{center}
'''

diagram_note_template = r'''
\draw[%s, fill=%s] (%s-%s) circle [radius=0.09] node[scale=.30] {};
\node[ynode] at (%s-%s) {\small %s};
'''

allnotes = ["do", "rebsb", "reb", "resb", "re", "mibsb", "mib", "misb", "mi", "fasb", "fa", "solbsb", "solb",
            "solsb", "sol", "labsb", "lab", "lasb", "la", "sibsb", "sib", "sisb", "si", "dosb"]


def _notetitle(n):
    title = n.capitalize()
    title = title.replace("sb", r"\hflat")
    title = title.replace("b", r"$\flat$")
    title = title.replace("s", r"$\sharp$")
    return title


snippetsfolder = os.path.join(os.path.dirname(os.path.dirname(__file__)), "libro", "snippets")


def generate_maqamat_snippets():

    maqamaatfile = os.path.join(os.path.dirname(__file__), "maqamaat.json")
    with open(maqamaatfile) as f:
        maqamaat = json.load(f)

    lilypond_maqam_template = r'''
    \subsection{Maqam %s}
    \begin{center}
    \resizebox{.8\textwidth}{!}{
    \begin{lilypond}
    \include "arabic.ly"

    #(set-default-paper-size "half letter")

    left-bracket-path = #'(
        (moveto 0 0)
        (lineto 0 -2)
        )

    right-bracket-path = #'(
        (moveto 0 0)
        (lineto 0 -2)
        )

    repeat-spanner-start-markup = \markup {
        \general-align #Y #CENTER
        \path #0.25 #left-bracket-path
        }

    repeat-spanner-stop-markup = \markup {
         \general-align #Y #CENTER
         \path #0.25 #right-bracket-path

        }

    scale = \relative do {

    \accidentalStyle forget
    \cadenzaOn
    \override TextSpanner.style = #'line
    \override TextSpanner.font-shape = #'caps
    \override TextSpanner.bound-details.right.text = \repeat-spanner-stop-markup
    \override TextSpanner.bound-details.left.text = \repeat-spanner-start-markup

    %s
    \bar "|"
    }

    \layout {
      indent = #0
      \context {
        \Score
        supportNonIntegerFret = ##t
      }
      \context {
          \TabStaff
        stringTunings = \stringTuning <do, fa, la, re sol do'>
        }
      \context {
          \Staff
          \remove "Time_signature_engraver"
        }

    }

    <<
      \new Staff << \clef "G_8" \scale \bar "|.">>
      \new TabStaff << \scale>>
    >>
    \end{lilypond}
    }
    \end{center}

    '''

    lilypond_jins_template = r'''
    \once \override TextSpanner.bound-details.right.padding = #%i
    \once \override TextSpanner.bound-details.left.padding = #%i
    \textSpannerUp
    \tweak color #grey %s1 ^ "  %s"
    \startTextSpan
    %s
    \stopTextSpan
    '''
    alternative_names = {"solb":"fad"}

    strings = ["do", "sol", "re", "la", "fa", "do"]
    for maqam in maqamaat:
        diagram = ""
        lilypond_maqam = ""
        maqamnotes = []
        ajnas = maqam["ajnas"]
        for ijins, jins in enumerate(ajnas):
            jinsnotes = jins[1].split(" ")
            maqamnotes.extend(["".join([c for c in n if c.isalpha()]) for n in jinsnotes])
            if ajnas[0][1].split(" ")[-1] == ajnas[1][1].split(" ")[0]:
                paddingright = -5 if ijins == 0 else 0
                paddingleft = 1 if ijins == 1 else 0
                if ijins == 0:
                    jinsnotes = jinsnotes[:-1]
            else:
                paddingright = 0
                paddingleft = 0
            lilypond_maqam += (lilypond_jins_template %
                (paddingright, paddingleft, f"{jinsnotes[0]}", jins[0], " ".join(jinsnotes[1:])))
        for istring, string in enumerate(strings):
            idx = allnotes.index(string)
            for fret in range(FRETS):
                pos = (idx + fret) % len(allnotes)
                note = allnotes[pos]
                if note in maqamnotes or alternative_names.get(note) in maqamnotes:
                    color = "red!50" if note == maqamnotes[0] else "blue!50"
                    if note in maqamnotes:
                        notetitle = _notetitle(note)
                    else:
                        notetitle = _notetitle(alternative_names.get(note))
                    diagram += (diagram_note_template % (color, color, 6-istring, fret, 6-istring, fret, notetitle))

        name = maqam["name"]
        snippetfile = os.path.join(snippetsfolder, f"{name}.tex")
        with open(snippetfile, "w") as f:
            f.write(lilypond_maqam_template % (maqam["title"], lilypond_maqam))
            f.write(diagram_template % (diagram))


def generate_full_fretboard():
    diagram = ""
    strings = ["do", "sol", "re", "la", "fa", "do"]
    for istring, string in enumerate(strings):
        idx = allnotes.index(string)
        for fret in range(FRETS):
            pos = (idx + fret) % len(allnotes)
            note = allnotes[pos]
            if not note.endswith("sb"):
                color = "blue!50"
                notetitle = _notetitle(note)
                diagram += (diagram_note_template % (color, color, 6-istring, fret, 6-istring, fret, notetitle))

    snippetfile = os.path.join(snippetsfolder, f"diapason.tex")
    with open(snippetfile, "w") as f:
        f.write(diagram_template % (diagram))


os.makedirs(snippetsfolder, exist_ok=True)
generate_maqamat_snippets()
generate_full_fretboard()
run_lilypond()
run_latex()
