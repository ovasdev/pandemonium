#!/usr/bin/env bash
# Send a file to the user via Telegram Bot API.
# Requires env vars: PANDEMONIUM_BOT_TOKEN, PANDEMONIUM_CHAT_ID
# Usage: send_file.sh <file_path> [caption]

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: send_file.sh <file_path> [caption]" >&2
    exit 1
fi

FILE_PATH="$1"
CAPTION="${2:-}"

if [ ! -f "$FILE_PATH" ]; then
    echo "Error: file not found: $FILE_PATH" >&2
    exit 1
fi

if [ -z "${PANDEMONIUM_BOT_TOKEN:-}" ] || [ -z "${PANDEMONIUM_CHAT_ID:-}" ]; then
    echo "Error: PANDEMONIUM_BOT_TOKEN and PANDEMONIUM_CHAT_ID must be set" >&2
    exit 1
fi

API_URL="https://api.telegram.org/bot${PANDEMONIUM_BOT_TOKEN}/sendDocument"

CURL_ARGS=(
    -s -S
    -F "chat_id=${PANDEMONIUM_CHAT_ID}"
    -F "document=@${FILE_PATH}"
)

if [ -n "$CAPTION" ]; then
    CURL_ARGS+=(-F "caption=${CAPTION}")
fi

RESPONSE=$(curl "${CURL_ARGS[@]}" "$API_URL")

# Check if the request was successful
OK=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok', False))" 2>/dev/null || echo "False")

if [ "$OK" = "True" ]; then
    echo "File sent successfully: $(basename "$FILE_PATH")"
else
    echo "Error sending file: $RESPONSE" >&2
    exit 1
fi
