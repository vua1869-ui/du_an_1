# -*- coding: utf-8 -*-
import re

with open('ai/vision.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_desc_rule = '''  "description": "Một đoạn văn bản phân tích ngắn (2-3 câu) nhận xét chi tiết về mâm cơm này: có nhiều dầu mỡ không, cân bằng dinh dưỡng chưa (nhiều tinh bột/rau/thịt), và món ăn này có phù hợp để giảm cân hay không.",'''

content = re.sub(r'"description":\s*"1-2 câu nhận xét tổng quan.*?",', new_desc_rule, content)

with open('ai/vision.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Prompt Fixed successfully!")
