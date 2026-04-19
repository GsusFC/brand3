#!/bin/bash
set -u
cd "$(dirname "$0")"

VALIDATION_DIR="validation-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$VALIDATION_DIR"
LOG_FILE="$VALIDATION_DIR/_run.log"
ERROR_FILE="$VALIDATION_DIR/_errors.log"

echo "Brand3 validation batch started at $(date)" | tee "$LOG_FILE"
echo "Output dir: $VALIDATION_DIR" | tee -a "$LOG_FILE"
echo "---" | tee -a "$LOG_FILE"

BRANDS=(
  "01-ath21|https://ath21.com|ATH21"
  "02-a16z|https://a16z.com|A16Z"
  "03-uber|https://uber.com|Uber"
  "04-airbnb|https://airbnb.com|Airbnb"
  "05-on|https://on.com|On"
  "06-tutellus|https://tutellus.com|Tutellus"
  "07-tecnocasa|https://tecnocasa.es|Tecnocasa"
  "08-mercadolibre|https://mercadolibre.com|MercadoLibre"
  "09-zora|https://zora.co|Zora"
  "10-elcorteingles|https://elcorteingles.es|El Corte Ingles"
  "11-harrods|https://harrods.com|Harrods"
  "12-elevenlabs|https://elevenlabs.io|ElevenLabs"
)

TOTAL=${#BRANDS[@]}
COUNT=0
SUCCESS=0
FAILED=0

for entry in "${BRANDS[@]}"; do
  COUNT=$((COUNT + 1))
  SLUG="${entry%%|*}"
  REST="${entry#*|}"
  URL="${REST%%|*}"
  NAME="${REST#*|}"

  echo "" | tee -a "$LOG_FILE"
  echo "[$COUNT/$TOTAL] $NAME ($URL)" | tee -a "$LOG_FILE"
  echo "  started: $(date +%H:%M:%S)" | tee -a "$LOG_FILE"

  STDOUT_FILE="$VALIDATION_DIR/${SLUG}.stdout.log"
  STDERR_FILE="$VALIDATION_DIR/${SLUG}.stderr.log"

  START_TS=$(date +%s)
  python main.py analyze "$URL" "$NAME" > "$STDOUT_FILE" 2> "$STDERR_FILE"
  EXIT_CODE=$?
  END_TS=$(date +%s)
  DURATION=$((END_TS - START_TS))

  if [ $EXIT_CODE -eq 0 ]; then
    SUCCESS=$((SUCCESS + 1))
    echo "  OK (${DURATION}s)" | tee -a "$LOG_FILE"
  else
    FAILED=$((FAILED + 1))
    echo "  FAILED exit=$EXIT_CODE (${DURATION}s)" | tee -a "$LOG_FILE"
    echo "[$NAME] exit=$EXIT_CODE - see $STDERR_FILE" >> "$ERROR_FILE"
  fi
done

echo "" | tee -a "$LOG_FILE"
echo "---" | tee -a "$LOG_FILE"
echo "Batch finished at $(date)" | tee -a "$LOG_FILE"
echo "Total: $TOTAL | Success: $SUCCESS | Failed: $FAILED" | tee -a "$LOG_FILE"

if [ $FAILED -gt 0 ]; then
  echo ""
  echo "ERRORS:"
  cat "$ERROR_FILE"
fi
