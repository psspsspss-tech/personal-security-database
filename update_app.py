import re

with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', encoding='utf-8') as f:
    text = f.read()

new_text = re.sub(
    r'<div class="breach-item-name">🔴 \$\{b\.name\}</div>\s*<div class="breach-item-date">Date: \$\{b\.date \|\| \'Unknown\'\}</div>\s*<div class="breach-item-desc">\$\{b\.description\?\.replace\(/<\[\^>\]\*>/g, \'\'\) \|\| \'\'\}</div>',
    r'''<div class="breach-item-name">
              🔴 ${b.domain ? `<a href="https://${b.domain}" target="_blank" rel="noopener noreferrer" style="color:var(--primary);text-decoration:none;">${b.name}</a>` : b.name}
            </div>
            <div class="breach-item-date">Date: ${b.date || 'Unknown'}</div>
            <div class="breach-item-desc">${b.description?.replace(/<[^>]*>/g, '') || ''}</div>
            ${b.exposed_data && b.exposed_data.length > 0 ? `<div style="margin-top:8px;font-size:12px;color:var(--text-muted);"><strong>Compromised Data:</strong> ${b.exposed_data.join(', ')}</div>` : ''}''',
    text
)

if new_text != text:
    with open(r'C:\Users\acer\Desktop\Security Suite\dashboard\app.js', 'w', encoding='utf-8') as f:
        f.write(new_text)
    print('Successfully updated app.js')
else:
    print('Failed to find and replace the content')
