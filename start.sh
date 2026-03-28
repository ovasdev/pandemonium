#!/bin/bash
# Start Pandemonium Telegram bot in background
cd "$(dirname "$0")"

if [ -f pandemonium.pid ] && kill -0 "$(cat pandemonium.pid)" 2>/dev/null; then
    echo "Bot is already running (PID $(cat pandemonium.pid))"
    exit 1
fi

# Unset Claude env vars so child claude processes don't think they're nested
unset CLAUDECODE
unset CLAUDE_CODE_ENTRYPOINT
nohup uv run python -m pandemonium.tgbot > pandemonium.log 2>&1 &
echo $! > pandemonium.pid
echo "Bot started (PID $!), log: pandemonium.log"
