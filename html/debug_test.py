import sys, os, re
sys.argv = ['', '../libro/capitulos/repertorio/repertorio.tex', '../libro/capitulos/repertorio']

def read_tex_with_inputs(filepath, base_dir):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    inp = re.compile(r'\\input\{([^}]+)\}')
    inputs = inp.findall(content)
    for ifile in inputs:
        ipath = os.path.join('../libro', ifile)
        if not os.path.exists(ipath):
            ipath = os.path.join(base_dir, ifile)
        if os.path.exists(ipath):
            content = content.replace(r'\input{' + ifile + '}', read_tex_with_inputs(ipath, os.path.dirname(ipath)))
        else:
            print(f'Warning: Could not find {ipath}')
            content = content.replace(r'\input{' + ifile + '}', '')
    return content

def preprocess(content):
    content = re.sub(r'\\includegraphics\[([^\]]*)\]\{([^}]+)\}', r'\n![\2](img/\2)\n', content)
    content = re.sub(r'\\includegraphics\{([^}]+)\}', r'\n![\1](img/\1)\n', content)
    content = re.sub(r'\\begin\{lilypond\}([\s\S]*?)\\end\{lilypond\}', '', content)
    content = re.sub(r'\\begin\{tikzpicture\}([\s\S]*?)\\end\{tikzpicture\}', '', content)
    return content

content = read_tex_with_inputs('../libro/capitulos/repertorio/repertorio.tex', '../libro/capitulos/repertorio')
content = preprocess(content)
with open('/tmp/repertorio_preprocessed.tex', 'w') as f:
    f.write(content)
print('Preprocessed saved. Length:', len(content))

# Also run pandoc manually
import subprocess
with open('/tmp/repertorio_pandoc.tex', 'w', encoding='utf-8') as f:
    f.write(content)
cmd = ['pandoc', '--from', 'latex', '--to', 'html5', '--standalone',
       '--template', 'template.html', '--metadata', 'title=Repertorio',
       '--output', '/tmp/repertorio_test.html', '/tmp/repertorio_pandoc.tex']
result = subprocess.run(cmd, check=True, capture_output=True)
print('Pandoc output:', len(result.stdout))
# Check if songheader appears
final = open('/tmp/repertorio_test.html').read()
if 'Bint Al' in final:
    print('Bint Al found in output!')
else:
    print('Bint Al NOT found!')
    # Show content
    print('Body sample:', final[500:1000])