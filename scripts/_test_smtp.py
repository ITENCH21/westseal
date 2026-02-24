"""Быстрая проверка SMTP Mail.ru"""
import smtplib, ssl

ctx = ssl.create_default_context()
try:
    with smtplib.SMTP_SSL("smtp.mail.ru", 465, context=ctx, timeout=10) as s:
        s.login("westseal@mail.ru", "xm22x001CkW1ovE8z7Mz")
        print("SMTP OK — авторизация прошла")
except Exception as e:
    print(f"SMTP ERROR: {e}")
