import re
with open('/Users/ivan/евро сеал/locale/en/LC_MESSAGES/django.po', 'r', encoding='utf-8') as f:
    content = f.read()
matches = re.findall(r'msgid "([^"]+)"\nmsgstr ""\n\n', content)
print(f"Truly empty translations: {len(matches)}")
for m in matches:
    print(f"  EMPTY: {repr(m[:90])}")
