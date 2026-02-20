import re

HELP_TRIGGERS = re.compile(
    r"^\s*(мне\s+)?(нужна?\s+помощь|помогите|поможите|помоги\b|есть\s+вопросы?|help)[!?.,\s]*$",
    re.IGNORECASE | re.UNICODE,
)

tests = [
    ("Мне нужна помощь", True),
    ("нужна помощь", True),
    ("помогите", True),
    ("помогите!", True),
    ("Помогите пожалуйста", False),   # есть доп. слово
    ("есть вопрос", True),
    ("есть вопросы", True),
    ("help", True),
    ("манжета 40мм", False),
    ("Здравствуйте", False),
    ("Мне нужна помощь!", True),
]
all_ok = True
for t, expected in tests:
    m = bool(HELP_TRIGGERS.search(t))
    status = "OK" if m == expected else "FAIL"
    if m != expected:
        all_ok = False
    print(f"{status}  match={m!r}  input={t!r}")
print("\nВсе OK!" if all_ok else "\nЕСТЬ ОШИБКИ!")
