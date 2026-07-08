with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    text = f.read()

start = text.find('async function checkBreach()')
end = text.find('function updateScore()', start)
with open('C:/Users/acer/Desktop/Security Suite/check_breach_catch.txt', 'w', encoding='utf-8') as f:
    f.write(text[start:end])
