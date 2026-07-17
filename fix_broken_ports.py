html_path = r"C:\Users\acer\Desktop\Security Suite\dashboard\index.html"
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Let's find the exact string that is broken
broken_section_start = html.find('<!-- ──────────── PORTS TAB ──────────── -->')
if broken_section_start != -1:
    event_log_start = html.find('<!-- ──────────── EVENT LOG TAB ──────────── -->', broken_section_start)
    if event_log_start != -1:
        # Check if it's the broken one
        between_text = html[broken_section_start:event_log_start]
        if '<tr>' in between_text and '</section>' not in between_text:
            # IT IS BROKEN! Delete this chunk
            html = html[:broken_section_start] + html[event_log_start:]
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
            print("DELETED BROKEN PORTS TAB!")
        else:
            print("Not the broken one")
    else:
        print("Event log tab not found after ports tab")
else:
    print("Ports tab not found")
