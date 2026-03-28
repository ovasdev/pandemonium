---
name: managing-bot
description: "Manages the Pandemonium bot lifecycle: restart, stop, check status. Triggers when the user asks to restart, reboot, stop, shut down, kill, or check if the bot is running. Also triggers on phrases like 'бот завис', 'перезапусти', 'останови', 'выключи', 'рестарт'."
---

# Managing the Pandemonium Bot

Control the bot process: restart or stop.

## Decision Tree

```
What does the user want?
├─ Restart/reboot → bash /mnt/b/projects/telegram-code-agent/restart.sh
├─ Stop/shutdown  → bash /mnt/b/projects/telegram-code-agent/stop.sh
└─ Status check   → check if pandemonium.pid exists and process is alive
```

## Restart

```bash
bash /mnt/b/projects/telegram-code-agent/restart.sh
```

Stops the bot (SIGTERM → wait → SIGKILL), starts it again in background, writes new PID to `pandemonium.pid`. Logs go to `pandemonium.log`. Env vars `CLAUDECODE` and `CLAUDE_CODE_ENTRYPOINT` are automatically unset.

**Warn the user:** Telegram connection will briefly drop during restart.

## Stop

```bash
bash /mnt/b/projects/telegram-code-agent/stop.sh
```

Reads PID from `pandemonium.pid`, sends SIGTERM, waits up to 10 seconds, then SIGKILL if needed. Removes `pandemonium.pid`.

**Warn the user:** After stopping, Telegram communication is lost. Confirm intent before proceeding.

## Status Check

```bash
# Check if bot process is running
cat /mnt/b/projects/telegram-code-agent/pandemonium.pid 2>/dev/null && ps -p $(cat /mnt/b/projects/telegram-code-agent/pandemonium.pid) > /dev/null 2>&1 && echo "Running" || echo "Not running"
```
