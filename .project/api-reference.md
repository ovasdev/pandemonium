# API Reference — все классы и функции

## config.py

```python
class PandemoniumError(Exception): ...           # Базовое исключение
class ConfigError(PandemoniumError): ...         # Ошибки конфига

class TelegramConfig(BaseModel):
    bot_token: str

class UserConfig(BaseModel):
    telegram_id: int
    name: str

class ProjectConfig(BaseModel):
    id: str
    name: str
    path: Path                           # Валидируется: должен существовать

class StorageConfig(BaseModel):
    base_path: Path = Path("~/.pandemonium/sessions")  # Expanduser в validator + model_post_init

class TokenBudgetConfig(BaseModel):
    per_request_limit: int = 0           # 0 = unlimited

class TimeoutsConfig(BaseModel):
    request_max_seconds: int = 1800      # 30 мин

class AppConfig(BaseModel):
    telegram: TelegramConfig
    allowed_users: list[UserConfig]
    projects: list[ProjectConfig]
    storage: StorageConfig = StorageConfig()
    token_budget: TokenBudgetConfig = TokenBudgetConfig()
    timeouts: TimeoutsConfig = TimeoutsConfig()

    @property allowed_user_ids -> set[int]
    @property default_project -> ProjectConfig    # Первый проект
    def get_user_name(telegram_id: int) -> str | None

def load_config(path: Path) -> AppConfig
def resolve_config_path() -> Path                # CLI args / $PANDEMONIUM_CONFIG / ~/.pandemonium/config.yaml
```

## db.py

```python
async def init_db(path: Path | str = ":memory:") -> aiosqlite.Connection

# Requests
async def create_request(db, project_id, user_id, request_number, message_id=None,
                         status_msg_id=None, chat_id=None) -> int
async def update_request_status(db, request_id: int, status: str, **kwargs)
    # kwargs: tokens_input, tokens_output, error_text
    # Auto-sets completed_at for terminal states (completed, cancelled, error)
async def get_active_request(db, project_id: str) -> Row | None
async def get_request_by_status_msg(db, status_msg_id: int) -> Row | None
async def get_recent_requests(db, project_id: str, limit=10) -> list[Row]
async def get_token_totals(db, project_id: str) -> dict  # {input, output, total}

# Interactions
async def create_interaction(db, request_id, sub_number, type_, direction,
                             content, message_id=None) -> int
async def get_interaction_by_message(db, message_id: int) -> Row | None
async def get_next_sub_number(db, request_id: int) -> int
```

## claude/types.py

```python
@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int

class SystemEvent:       subtype: str, session_id: str | None = None
class AssistantEvent:    text: str, usage: TokenUsage | None = None
class ToolUseEvent:      tool: str, input: dict = field(default_factory=dict)
class ToolResultEvent:   tool: str, output: str
class ResultEvent:       text: str, usage: TokenUsage, is_error: bool = False
class PermissionRequestEvent:  tool: str, description: str
class InputRequestEvent:       question: str

type ClaudeEvent = SystemEvent | AssistantEvent | ToolUseEvent | ...
```

## claude/events.py

```python
def parse_event(line: str) -> ClaudeEvent | None
    # Парсит JSON-строку из stdout claude subprocess
```

## claude/process.py

```python
class ClaudeProcess:
    async def start(prompt: str, project_path: Path, *,
                    resume_session_id: str | None = None) -> None
        # Команда: claude --print --output-format stream-json --verbose
        #          --max-turns 50 --permission-mode bypassPermissions
        #          [--resume {session_id}] {prompt}
        # Фильтрует env: убирает CLAUDECODE, CLAUDE_CODE_ENTRYPOINT

    async def stream_events() -> AsyncIterator[ClaudeEvent]
    async def send_input(text: str) -> None
    async def send_permission(allowed: bool) -> None
        # Отправляет: {"type": "permission", "allowed": bool}
    async def cancel() -> None     # SIGTERM → 5s → SIGKILL
    async def wait() -> int        # exit code
    def is_running() -> bool
    @property stderr_output -> str
```

## session/state.py

```python
class SessionState(Enum):
    IDLE, RUNNING, AWAITING_INPUT, COMPLETED, CANCELLED, ERROR

@dataclass
class ActiveSession:
    request_id: int
    request_number: int
    project_id: str
    chat_id: int
    user_message_id: int
    status_message_id: int
    state: SessionState
    claude_process: ClaudeProcess
    typing_task: asyncio.Task | None = None
    process_task: asyncio.Task | None = None
    sub_counter: int = 0
    pending_response: asyncio.Future | None = None
```

## session/buffer.py

```python
class StreamBuffer:
    def __init__(self, flush_callback: Callable[[str], Awaitable[None]],
                 interval: float = 2.5, max_size: int = 3500)
    async def append(text: str) -> None   # Accumulate, auto-flush on size
    async def flush() -> None
    async def close() -> None             # Flush + cancel timer
```

## session/manager.py

```python
class SessionManager:
    def __init__(self, config: AppConfig, database: aiosqlite.Connection,
                 storage: ProtocolStorage, bot: Bot)

    async def create_request(project_id, user_id, chat_id, message_id,
                             status_message_id, prompt) -> int  # request_number
    async def cancel_request(request_id: int) -> None
    async def handle_permission_response(request_id, allowed: bool) -> None
    async def handle_user_reply(request_id, text: str) -> None
    async def shutdown() -> None
    def clear_session() -> None          # Сброс session_id

    @property active_session -> ActiveSession | None
    @property is_shutting_down -> bool
    @property claude_session_id -> str | None
```

## storage/protocol.py

```python
class ProtocolStorage:
    def __init__(self, base_path: Path)

    def next_request_number(project_id: str) -> int
    async def save_request(project_id, number, content) -> Path
    async def save_interaction(project_id, req_number, sub_number,
                               content, is_response: bool) -> Path
    async def append_stream_log(project_id, req_number, chunk)
    async def save_report(project_id, req_number, content) -> Path
    async def save_error(project_id, req_number, error) -> Path
    async def save_meta(project_id, req_number, meta: dict) -> Path
```

## bot/handlers.py

```python
router = Router(name="main")

@router.message(Command("start"))
async def cmd_start(message, config)

@router.message(Command("status"))
async def cmd_status(message, config, db, session_manager)

@router.message(Command("history"))
async def cmd_history(message, config, db)

@router.message(Command("clear"))
async def cmd_clear(message, session_manager)

@router.message(Command("tokens"))
async def cmd_tokens(message, config, db)

@router.message(F.reply_to_message & F.text & ~F.text.startswith("/"))
async def handle_reply_message(message, session_manager, db)

@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message, config, session_manager)
```

## bot/callbacks.py

```python
router = Router(name="callbacks")

# callback_data: "cancel:{request_id}"
async def on_cancel(callback, session_manager)

# callback_data: "perm:{request_id}:{allow|deny}"
async def on_permission(callback, session_manager)
```

## bot/middleware.py

```python
class AuthMiddleware(BaseMiddleware):
    def __init__(self, allowed_ids: set[int])
    # Блокирует Message и CallbackQuery от неавторизованных
```

## bot/retry.py

```python
async def telegram_retry(fn: Callable[[], Awaitable[T]],
                          max_retries: int = 3) -> T | None
```

## bot/formatters.py

```python
def welcome_message(user_name: str, project_name: str) -> str
def format_status_message(request_number: int, state: SessionState) -> str
def format_history(rows: list) -> str
def format_tokens(project_name: str, total_requests: int, totals: dict) -> str
def format_active_status(request_number: int, created_at: str) -> str
```

## bot/markup.py

```python
def md_to_telegram_html(text: str) -> str
def truncate_html(html: str, limit: int = 4000) -> str
```

## main.py

```python
async def _recover_interrupted_requests(database, storage)
async def main() -> None
def cli() -> None
```
