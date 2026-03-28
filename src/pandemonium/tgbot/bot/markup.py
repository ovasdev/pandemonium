"""Convert markdown text to Telegram HTML.

Telegram supports a subset of HTML: <b>, <i>, <code>, <pre>, <blockquote>, <a>.
This converter handles the most common markdown patterns from Claude output.
"""

import re
from html import escape


def md_to_telegram_html(text: str) -> str:
    """Convert markdown to Telegram-compatible HTML.

    Handles: fenced code blocks, inline code, bold, italic, links, headers.
    Falls back to escaped plain text for anything unsupported.
    """
    # First, extract fenced code blocks to protect them from other transforms
    blocks: list[str] = []

    def _save_block(m: re.Match) -> str:
        lang = m.group(1) or ""
        code = escape(m.group(2).strip())
        idx = len(blocks)
        if lang:
            blocks.append(f'<pre><code class="language-{escape(lang)}">{code}</code></pre>')
        else:
            blocks.append(f"<pre>{code}</pre>")
        return f"\x00BLOCK{idx}\x00"

    result = re.sub(
        r"```(\w*)\n(.*?)```",
        _save_block,
        text,
        flags=re.DOTALL,
    )

    # Escape HTML in remaining text (not inside code blocks)
    result = escape(result)

    # Inline code (must be before bold/italic to avoid conflicts)
    result = re.sub(r"`([^`]+)`", r"<code>\1</code>", result)

    # Bold: **text** or __text__
    result = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", result)
    result = re.sub(r"__(.+?)__", r"<b>\1</b>", result)

    # Italic: *text* or _text_ (but not inside words like file_name)
    result = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"<i>\1</i>", result)

    # Headers → bold
    result = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", result, flags=re.MULTILINE)

    # Links: [text](url)
    result = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', result)

    # Restore code blocks
    for i, block in enumerate(blocks):
        result = result.replace(f"\x00BLOCK{i}\x00", block)

    return result


# Telegram message limit is 4096 chars; keep margin for safety
_MAX_MESSAGE_LEN = 4000


def truncate_html(html: str, limit: int = _MAX_MESSAGE_LEN) -> str:
    """Truncate HTML text, trying to avoid breaking tags."""
    if len(html) <= limit:
        return html
    # Simple truncation — cut and close any open tags would be complex,
    # so just cut before limit and strip any partial tag at the end
    cut = html[:limit]
    # Remove any partial tag at the end
    last_lt = cut.rfind("<")
    last_gt = cut.rfind(">")
    if last_lt > last_gt:
        cut = cut[:last_lt]
    return cut + "..."
