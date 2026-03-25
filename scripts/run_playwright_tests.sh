#!/bin/bash
# ============================================================
# Playwright Bot Test Runner
# ============================================================
# Prerequisites:
#   pip install playwright opencv-python-headless numpy requests
#   playwright install chromium
#
# Before running:
#   1. Start your backend:  cd backend && uvicorn main:app --port 8000
#   2. Start your frontend: cd frontend && npm run dev
#
# Usage:
#   bash run_playwright_tests.sh [attempts]
# ============================================================

ATTEMPTS=${1:-20}
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTDIR="logs/playwright-tests/${TIMESTAMP}"
mkdir -p "$OUTDIR"

echo "========================================"
echo "Playwright Bot Tests — ${TIMESTAMP}"
echo "Attempts per strategy: ${ATTEMPTS}"
echo "Output: ${OUTDIR}/"
echo "========================================"

# --- Line Tracing CAPTCHA ---
echo ""
echo "=== LINE TRACING CAPTCHA ==="
python playwright_line_bot.py \
    --strategy all \
    --attempts "$ATTEMPTS" \
    --output "${OUTDIR}/line_results.json" \
    2>&1 | tee "${OUTDIR}/line_output.txt"

# --- Image Intersection CAPTCHA ---
echo ""
echo "=== IMAGE INTERSECTION CAPTCHA ==="
python playwright_image_bot.py \
    --strategy all \
    --attempts "$ATTEMPTS" \
    --output "${OUTDIR}/image_results.json" \
    2>&1 | tee "${OUTDIR}/image_output.txt"

echo ""
echo "========================================"
echo "All tests complete. Results in ${OUTDIR}/"
echo "========================================"
