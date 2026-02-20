import re
GREET_TRIGGERS = re.compile(
    r"^\s*(привет|здравствуй\w*|добрый\s+\w+|хай|hello|hi)[!.,\s]*$",
    re.IGNORECASE | re.UNICODE,
)
tests = [
    ("здравствуйте", True),
    ("здравствуйте!", True),
    ("Здравствуйте ", True),
    ("привет", True),
    ("здравствуй", True),
    ("Добрый день", True),
    ("хай", True),
    ("Мне нужна помощь", False),
    ("здравствуйте хотел бы купить манжету", False),
    ("PTFE", False),
    ("Здравствуйте!", True),
]
all_ok = True
for t, expected in tests:
    m = bool(GREET_TRIGGERS.search(t))
    status = "OK" if m == expected else "FAIL"
    if m != expected:
        all_ok = False
    print(f"{status}  match={m!r}  input={t!r}")
print("\nВсе OK!" if all_ok else "\nЕСТЬ ОШИБКИ!")
