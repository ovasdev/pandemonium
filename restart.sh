#!/bin/bash
# Restart Pandemonium Telegram bot: stop then start
cd "$(dirname "$0")"

echo "=== Restarting Pandemonium bot ==="

# Stop if running
if [ -f pandemonium.pid ]; then
    PID=$(cat pandemonium.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping bot (PID $PID)..."
        kill -TERM "$PID"

        for i in $(seq 1 10); do
            if ! kill -0 "$PID" 2>/dev/null; then
                echo "Bot stopped"
                break
            fi
            sleep 1
        done

        if kill -0 "$PID" 2>/dev/null; then
            echo "Force killing..."
            kill -9 "$PID" 2>/dev/null
        fi
    else
        echo "Process $PID is not running, cleaning up"
    fi
    rm -f pandemonium.pid
else
    echo "Bot was not running"
fi

# Start
unset CLAUDECODE
unset CLAUDE_CODE_ENTRYPOINT
nohup uv run python -m pandemonium.tgbot > pandemonium.log 2>&1 &
echo $! > pandemonium.pid
echo "Bot started (PID $!), log: pandemonium.log"
