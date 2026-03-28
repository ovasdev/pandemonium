#!/bin/bash
# Stop Pandemonium Telegram bot gracefully
cd "$(dirname "$0")"

if [ ! -f pandemonium.pid ]; then
    echo "No PID file found, bot is not running"
    exit 1
fi

PID=$(cat pandemonium.pid)

if ! kill -0 "$PID" 2>/dev/null; then
    echo "Process $PID is not running, cleaning up"
    rm -f pandemonium.pid
    exit 0
fi

echo "Stopping bot (PID $PID)..."
kill -TERM "$PID"

# Wait up to 10 seconds for graceful shutdown
for i in $(seq 1 10); do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "Bot stopped"
        rm -f pandemonium.pid
        exit 0
    fi
    sleep 1
done

echo "Force killing..."
kill -9 "$PID" 2>/dev/null
rm -f pandemonium.pid
echo "Bot killed"
