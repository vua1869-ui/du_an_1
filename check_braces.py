import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

scripts = re.findall(r'<script>(.*?)</script>', text, re.DOTALL)
script = scripts[-1]

ob = script.count('{')
cb = script.count('}')
print('Braces:', ob, cb)

op = script.count('(')
cp = script.count(')')
print('Parens:', op, cp)

obk = script.count('[')
cbk = script.count(']')
print('Brackets:', obk, cbk)
