"""Message formatting helpers for Telegram output (HTML mode)."""

from datetime import datetime, timezone
from html import escape

from pandemonium.tgbot.session.state import SessionState


def welcome_message(user_name: str, project_name: str) -> str:
    """Format the /start welcome message."""
    return (
        f"Hello, <b>{escape(user_name)}</b>!\n\n"
        f"Active project: <code>{escape(project_name)}</code>\n\n"
        "Send me a text message and I'll forward it to Claude Code."
    )


_STATUS_LABELS: dict[SessionState, str] = {
    SessionState.RUNNING: "Running...",
    SessionState.AWAITING_INPUT: "Waiting for your input...",
    SessionState.COMPLETED: "Done",
    SessionState.CANCELLED: "Cancelled",
    SessionState.ERROR: "Error",
}


def format_status_message(request_number: int, state: SessionState) -> str:
    """Format the status message shown above Cancel button."""
    label = _STATUS_LABELS.get(state, state.value)
    return f"Request #{request_number}: {label}"


def format_error_message(error_text: str) -> str:
    """Format an error message for the user."""
    truncated = error_text[:3900] if len(error_text) > 3900 else error_text
    return f"Error: {escape(truncated)}"


_STATUS_ICONS: dict[str, str] = {
    "completed": "\u2705",
    "error": "\u274c",
    "cancelled": "\u23f9",
    "running": "\u23f3",
    "awaiting_input": "\u2753",
    "pending": "\u23f3",
}


def format_history(rows: list) -> str:
    """Format /history output from DB rows."""
    if not rows:
        return "No requests yet."
    lines: list[str] = []
    for row in rows:
        status = row["status"]
        icon = _STATUS_ICONS.get(status, "")
        tokens = row["tokens_input"] + row["tokens_output"]
        date = row["created_at"][:10] if row["created_at"] else "?"
        prompt_preview = escape(row.get("prompt", "")[:40]) if row.get("prompt") else ""
        lines.append(
            f"{icon} <b>#{row['request_number']}</b>  {status}  {date}  {tokens:,} tok"
            + (f"\n    <i>{prompt_preview}</i>" if prompt_preview else "")
        )
    return "\n".join(lines)


def format_tokens(project_name: str, total_requests: int, totals: dict) -> str:
    """Format /tokens output."""
    return (
        f"Project: <b>{escape(project_name)}</b>\n"
        f"Total requests: {total_requests}\n"
        f"Tokens: <b>{totals['total']:,}</b> "
        f"(input: {totals['input']:,}, output: {totals['output']:,})"
    )


def format_active_status(request_number: int, created_at: str) -> str:
    """Format /status output for an active request."""
    try:
        start = datetime.fromisoformat(created_at)
        elapsed = datetime.now(timezone.utc) - start
        minutes, seconds = divmod(int(elapsed.total_seconds()), 60)
        duration = f"{minutes} min {seconds} sec"
    except (ValueError, TypeError):
        duration = "?"
    return f"Request #{request_number} — running ({duration})"
