import os
p='/home/volaya/sources/libro_ud/html/convert.py'
c=open(p,encoding='utf-8').read()
c=c.replace("    for f in re.findall(r'\\\\\\\\input\\\\\\\\{([^}]+)\\\}', c):","    for f in re.findall(r'\\\\\\\\\\\\\\\\input\\\\\\\\\\\\\\\\{([^}]+)\\\\\\\\\\\\\\\\\}', c):")
c=c.replace("            c = c.replace(r'\\\\\\\\input{' + f + '}', read_inputs(p, os.path.dirname(p)))","            c = c.replace(r'\\\\\\\\\\\\\\\\input{' + f + '}', read_inputs(p, os.path.dirname(p)))")
c=c.replace("            c = c.replace(r'\\\\\\\\input{' + f + '}', '')","            c = c.replace(r'\\\\\\\\\\\\\\\\input{' + f + '}', '')")
open(p,'w',encoding='utf-8').write(c)
print('fixed')
