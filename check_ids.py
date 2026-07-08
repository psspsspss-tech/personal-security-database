import re
with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    text = f.read()

for i, m in enumerate(re.finditer(r'<input[^>]*id="([^"]+)"', text)):
    if 'breach' in m.group(1):
        print(f"Found input with id: {m.group(1)}")
