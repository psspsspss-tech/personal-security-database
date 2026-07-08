with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\index.html', encoding='utf-8') as f:
    text = f.read()
start = text.find('id="panel-breach"')
print(text[start:start+800])
