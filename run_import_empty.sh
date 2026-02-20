#!/bin/bash
# Импорт только пустых категорий
set -e
cd "$(dirname "$0")"

PYTHON=".venv/bin/python"
SLEEP=0.3  # задержка между запросами (сек)

CATEGORIES=(
  amortizatori_dlya_elektroprivodov_nasosov
  grjazesemniki
  koltsa_obzhimnie_usit
  koltsa_zashchitnye
  koltsa_stopornye
  kolca_uplatnitelnye
  manzhety_armirovannye
  napravljajuwie_gidrocilindrov
  pnevmaticheskoe_uplotnenija
  podsh
  specialnye_uplotnenija
  shaiba
  manzheti_shevronnie
)

LOG="data/import_mkt_rti.log"
echo "$(date): Starting import for ${#CATEGORIES[@]} empty categories" >> "$LOG"

for CAT in "${CATEGORIES[@]}"; do
  echo ">>> Importing category: $CAT"
  "$PYTHON" manage.py import_mkt_rti \
    --category "$CAT" \
    --sleep "$SLEEP" \
    --log-file "$LOG" \
    || echo "WARNING: category $CAT failed, continuing..."
  echo "--- done $CAT ---"
done

echo "$(date): All empty categories done." >> "$LOG"
echo "=== Import completed ==="
