# Спринт 2 — Обёртка Claude Code

## Цель

Реализовать `ClaudeProcess` — класс, который запускает Claude Code как дочерний процесс, парсит поток событий и предоставляет async API для взаимодействия.

## Задачи

### 2.1 Типы событий (`claude/types.py`)

Dataclass-ы для событий Claude Code stream-json:

```python
@dataclass
class AssistantEvent:
    text: str
    usage: TokenUsage | None

@dataclass
class ToolUseEvent:
    tool: str
    input: dict

@dataclass
class ToolResultEvent:
    tool: str
    output: str

@dataclass
class ResultEvent:
    text: str
    usage: TokenUsage

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
```

Общий тип: `ClaudeEvent = AssistantEvent | ToolUseEvent | ToolResultEvent | ResultEvent`.

### 2.2 Парсер событий (`claude/events.py`)

- Функция `parse_event(line: str) -> ClaudeEvent | None`.
- Читает JSON-строку, определяет тип, возвращает типизированный объект.
- Неизвестные типы — логируются и пропускаются (None).

### 2.3 ClaudeProcess (`claude/process.py`)

Реализовать класс согласно `architecture.md` п. 3.3:

```python
class ClaudeProcess:
    async def start(self, prompt: str, project_path: Path) -> None
    async def stream_events(self) -> AsyncIterator[ClaudeEvent]
    async def send_input(self, text: str) -> None
    async def cancel(self) -> None       # SIGTERM, ждём 5 сек, SIGKILL
    async def wait(self) -> int
    def is_running(self) -> bool
```

- Запуск: `claude --output-format stream-json --verbose -p "{prompt}"`, `cwd=project_path`.
- `stream_events()` — читает stdout построчно (`readline()`), парсит через `parse_event`.
- `send_input()` — пишет в stdin + `\n` + flush.
- `cancel()` — `process.terminate()`, `asyncio.wait_for(process.wait(), timeout=5)`, при таймауте `process.kill()`.
- Stderr собирается в буфер для диагностики ошибок.

### 2.4 Простой интеграционный тест

Скрипт/тест, который запускает `ClaudeProcess` с простым промптом ("say hello") в тестовой директории, итерирует события, печатает их. Для ручной проверки.

## Критерий готовности

- `ClaudeProcess` запускает Claude Code, получает поток событий, корректно завершается.
- `cancel()` убивает процесс.
- Ошибки парсинга не роняют приложение.
