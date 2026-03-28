---
name: claude-cli-integration
description: "Provides patterns for integrating with Claude Code CLI as a subprocess with stream-json output. Triggers when working on the ClaudeProcess component, parsing Claude Code events, or debugging subprocess communication. Also applies when modifying how Pandemonium bot spawns, communicates with, or terminates the claude process."
compatibility: "Requires Claude Code CLI installed"
---

# Claude Code CLI Integration

Patterns for running Claude Code as a subprocess with JSON event streaming.

## Launching with JSON Streaming

```bash
claude --output-format stream-json --verbose -p "prompt text" --max-turns 50
```

| Flag | Purpose |
|---|---|
| `--output-format stream-json` | JSON objects, one per line on stdout |
| `--verbose` | **Required** with stream-json, otherwise Claude exits with error |
| `-p "prompt"` | Non-interactive mode |
| `--max-turns N` | Iteration limit |

## Event Format (stdout)

Each line is a JSON object:

```json
{"type": "system", "subtype": "init", "session_id": "..."}

{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "..."}]}, "usage": {"input_tokens": 100, "output_tokens": 50}}

{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "tool_use", "id": "...", "name": "Write", "input": {...}}]}}

{"type": "result", "result": "final text", "usage": {"input_tokens": 5000, "output_tokens": 1200}, "is_error": false}
```

## Python Subprocess

```python
process = await asyncio.create_subprocess_exec(
    "claude",
    "--output-format", "stream-json",
    "--verbose",
    "-p", prompt,
    cwd=str(project_path),
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)

async for line in process.stdout:
    event = json.loads(line.decode())
    match event.get("type"):
        case "assistant": ...
        case "result": ...
```

## Critical: Environment Variables

Child `claude` processes inherit env vars that make them think they're nested. **Must unset** both `CLAUDECODE` and `CLAUDE_CODE_ENTRYPOINT` before spawning — otherwise the subprocess behaves incorrectly.

## Lifecycle

- Claude Code may go silent for extended periods (thinking) — not a hang
- stderr contains diagnostics — buffer for debugging
- Exit code 0 = success, non-zero = error
- Cancellation: `process.terminate()`, wait 5s, then `process.kill()`
- Input: `process.stdin.write(data)` + `process.stdin.drain()`
