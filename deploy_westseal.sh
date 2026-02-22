#!/bin/bash
# =============================================================
#  WESTSEAL — деплой на сервер Beget (46.173.26.75)
#  Запускать на сервере: bash deploy_westseal.sh
# =============================================================
set -e

PROJECT_DIR="/home/ivan/euro-seal"   # ⚠ замени на реальный путь к проекту
VENV_DIR="$PROJECT_DIR/.venv"
NGINX_CONF="/etc/nginx/sites-available/euroseal"  # ⚠ проверь имя файла

echo "===== 1. Получаем последние изменения из GitHub ====="
cd "$PROJECT_DIR"
git pull origin main

echo "===== 2. Обновляем зависимости ====="
source "$VENV_DIR/bin/activate"
pip install -r requirements.txt --quiet

echo "===== 3. Применяем миграции ====="
python manage.py migrate --noinput

echo "===== 4. Собираем статику ====="
python manage.py collectstatic --noinput

echo "===== 5. Компилируем переводы ====="
python manage.py compilemessages

echo "===== 6. Обновляем .env (euro-seal.ru → westseal.ru) ====="
if grep -q "euro-seal.ru" .env 2>/dev/null; then
    sed -i 's/euro-seal\.ru/westseal.ru/g' .env
    echo "  .env обновлён"
else
    echo "  .env уже содержит westseal.ru — пропускаем"
fi

echo ""
echo "  Проверяем ключевые переменные в .env:"
grep -E "SITE_URL|ALLOWED_HOSTS|CSRF_TRUSTED_ORIGINS" .env || true

echo "===== 7. Обновляем nginx конфиг ====="
if [ -f "$NGINX_CONF" ]; then
    # Заменяем server_name
    sed -i 's/euro-seal\.ru/westseal.ru/g' "$NGINX_CONF"
    echo "  nginx конфиг обновлён: $NGINX_CONF"
    nginx -t && echo "  Синтаксис nginx OK"
else
    echo "  ⚠ Файл $NGINX_CONF не найден!"
    echo "  Найди конфиг командой: grep -rl 'euro-seal' /etc/nginx/"
fi

echo "===== 8. Выпускаем SSL-сертификат для westseal.ru ====="
# Проверяем, есть ли уже сертификат
if [ -d "/etc/letsencrypt/live/westseal.ru" ]; then
    echo "  Сертификат уже существует — обновляем"
    certbot renew --cert-name westseal.ru
else
    echo "  Выпускаем новый сертификат"
    certbot --nginx -d westseal.ru -d www.westseal.ru \
        --non-interactive --agree-tos \
        --email info@westseal.ru
fi

echo "===== 9. Перезапускаем nginx ====="
systemctl reload nginx && echo "  nginx перезагружен"

echo "===== 10. Перезапускаем приложение ====="
# Определяем имя сервиса (попробуем несколько вариантов)
for SVC in euroseal euro-seal westseal daphne gunicorn; do
    if systemctl is-active --quiet "$SVC" 2>/dev/null; then
        systemctl restart "$SVC"
        echo "  Сервис $SVC перезапущен"
        break
    fi
done

# Если supervisord:
if command -v supervisorctl &>/dev/null; then
    supervisorctl restart all 2>/dev/null && echo "  supervisor: сервисы перезапущены" || true
fi

echo ""
echo "============================================="
echo "  ДЕПЛОЙ ЗАВЕРШЁН"
echo "  Проверь сайт: https://westseal.ru"
echo "============================================="
