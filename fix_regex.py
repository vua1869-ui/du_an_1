# -*- coding: utf-8 -*-
with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# The file currently has:
# replace(/
# /g, '<br>')
# We need to replace it with:
# replace(/\\n/g, '<br>')

# It appears twice.
content = content.replace("replace(/\n/g, '<br>')", "replace(/\\\\n/g, '<br>')")

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed newlines in JS regex!")
