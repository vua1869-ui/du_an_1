# -*- coding: utf-8 -*-
with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("replace(/\\\\n/g, '<br>')", "replace(/\\n/g, '<br>')")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed to single backslash!")
