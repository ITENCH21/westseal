#!/bin/bash
# ============================================================
# EURO-SEAL — Импорт товаров для пустых категорий с mkt-rti.ru
# Запускать из папки проекта: bash run_import.sh
# ============================================================

cd "$(dirname "$0")"
source .venv/bin/activate

# Список пустых категорий (slug = часть URL на mkt-rti.ru)
CATEGORIES=(
  "kolca_uplatnitelnye"
  "grjazesemniki"
  "napravljajuwie_gidrocilindrov"
  "manzhety_armirovannye"
  "manzheti_shevronnie"
  "pnevmaticheskoe_uplotnenija"
  "podsh"
  "specialnye_uplotnenija"
  "shaiba"
  "amortizatori_dlya_elektropriv"
  "koltsa_obzhimnie_usit"
  "koltsa_zashchitnye"
  "koltsa_stopornye"
)

TOTAL=${#CATEGORIES[@]}
COUNT=0

for SLUG in "${CATEGORIES[@]}"; do
  COUNT=$((COUNT + 1))
  echo ""
  echo "======================================================"
  echo "[$COUNT/$TOTAL] Импорт категории: $SLUG"
  echo "======================================================"
  python manage.py import_mkt_rti --category "$SLUG" --sleep 0.5
  echo "Готово: $SLUG"
done

echo ""
echo "======================================================"
echo "✅ Импорт завершён. Всего обработано: $TOTAL категорий."
echo "======================================================"
