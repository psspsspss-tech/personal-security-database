"""
fix_unicode_buttons.py
Fixes corrupted unicode characters in dashboard/app.js
All replacements use safe ASCII-compatible unicode escape sequences.
"""
import re, os, sys

app_js = os.path.join(os.path.dirname(__file__), 'dashboard', 'app.js')

with open(app_js, 'r', encoding='utf-8') as f:
    content = f.read()

original = content

# Map of corrupted literals -> correct safe replacement
# We use chr() so this file stays pure ASCII and encoding-safe.
CHECK = '\u2713'    # ✓  (small check mark)
CHECK_HEAVY = '\u2714'  # ✔  (heavy check mark)
CROSS = '\u2715'   # ✕  (multiplication x)
BOLT  = '\u26a1'   # ⚡  (lightning)
WARN  = '\u26a0'   # ⚠  (warning)

replacements = [
    # ── Acknowledge buttons: "✓? Acknowledged" / "✓? Acknowledge" ──
    # The current file has: CHECK + '?' + space + 'Acknowledged'
    # The '?' is a UTF-8 corruption artifact of ≈ U+003F or a misread byte
    (CHECK + '? Acknowledged', CHECK + ' Acknowledged'),
    (CHECK + '? Acknowledge',  CHECK + ' Acknowledge'),

    # ── Approve buttons: '? Approve' / '? Approve Device' / '? Approve & Whitelist' ──
    # Current file shows a lone '?' before 'Approve' — should be CHECK
    ('>' + '? Approve & Whitelist',  '>' + CHECK + ' Approve \u0026 Whitelist'),
    ('>' + '? Approve Device',       '>' + CHECK + ' Approve Device'),
    ('>' + '? Approve</button>',     '>' + CHECK + ' Approve</button>'),

    # ── Revoke button: '??? Revoke' -> '✕ Revoke' ──
    ('??? Revoke',  CROSS + ' Revoke'),
    ('?? Revoke',   CROSS + ' Revoke'),

    # ── Wake button: '? Wake' -> '⚡ Wake' ──
    ('>' + '? Wake',  '>' + BOLT + ' Wake'),

    # ── confirmApprove toast: CHECK + ' ' + name should stay, but fix if corrupted ──
    # "showToast(`✓ ${name}" is already correct in original, keep as-is
]

changes = 0
for old, new in replacements:
    count = content.count(old)
    if count > 0:
        content = content.replace(old, new)
        # encode to ascii with backslash-replace for safe printing on cp1252
        old_safe = repr(old[:30]).encode('ascii', 'backslashreplace').decode('ascii')
        new_safe = repr(new[:30]).encode('ascii', 'backslashreplace').decode('ascii')
        print(f"[OK] Replaced {count}x: {old_safe} -> {new_safe}")
        changes += count
    else:
        old_safe = repr(old[:40]).encode('ascii', 'backslashreplace').decode('ascii')
        print(f"[--] Not found: {old_safe}")

if changes == 0:
    print("\nNo changes needed — file may already be clean.")
else:
    with open(app_js, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\nDone! {changes} replacement(s) written to {app_js}")
