---
name: sending-telegram-file
description: "Sends files to the user via Telegram Bot API. Triggers when the user asks to send, forward, share, or show a file — or when a task produces output that should be delivered as a file attachment rather than inline text. Also applies when generating reports, exports, or any content that exceeds comfortable message length."
---

# Sending Files to Telegram

Send files to the user via Telegram Bot API using the `send_file.sh` script.

## Usage

```bash
$PANDEMONIUM_SEND_FILE /absolute/path/to/file
$PANDEMONIUM_SEND_FILE /absolute/path/to/file "Optional caption"
```

- First argument: absolute path to the file (required)
- Second argument: caption (optional)
- Environment variables `PANDEMONIUM_SEND_FILE`, `PANDEMONIUM_BOT_TOKEN`, `PANDEMONIUM_CHAT_ID` are pre-set

## Examples

```bash
# Send a config file
$PANDEMONIUM_SEND_FILE /mnt/b/projects/my-app/config.yaml

# Send with caption
$PANDEMONIUM_SEND_FILE /mnt/b/projects/my-app/report.pdf "Отчёт за март"

# Generate and send
echo "data" > /tmp/output.txt
$PANDEMONIUM_SEND_FILE /tmp/output.txt "Результат"
```

## Constraints

- File must exist on disk — write to a temp file first if needed
- Max file size: 50 MB (Telegram Bot API limit)
- Script calls `sendDocument` via `curl`
- Location: `.pandemonium/tools/send_file.sh` (relative to project root)
