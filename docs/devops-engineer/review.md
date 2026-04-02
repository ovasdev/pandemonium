# Pandemonium Bot — Взгляд DevOps-инженера

## Первое впечатление

Pandemonium — сервис, который запускает произвольный код (Claude Code CLI с `--permission-mode bypassPermissions`) на хостовой машине. С точки зрения инфраструктуры это самый опасный компонент в нашем стеке. И одновременно — самый простой в деплое.

## Деплой и запуск

### Текущая модель

Бот запускается через `start.sh`, перезапускается через `restart.sh` или Telegram-команду `/reboot`. Нет Docker, нет systemd unit, нет process manager. Это bare-metal Python-процесс.

Для single-instance на домашнем сервере — приемлемо. Но:

- **Нет автоматического перезапуска при крэше.** Если бот упал ночью — утром обнаружишь мёртвый процесс. В FileStorage2 у нас systemd с `Restart=always` и `WatchdogSec`.
- **Нет лог-ротации.** `logging.basicConfig` пишет в stdout. Если stdout перенаправлен в файл — файл растёт бесконечно. Нужен `RotatingFileHandler` или journald.
- **`/reboot` — self-restart через spawn + SIGTERM.** Это работает, но хрупко. `cmd_reboot` создаёт detached shell, который ждёт смерти текущего процесса и запускает `start.sh`. Если `start.sh` не найден или не исполняемый — бот мёртв, а перезапуска не будет. Нет health check, нет fallback.

### Что я бы настроил

**Вариант 1: systemd unit** (минимальный, для текущего сервера):

```ini
[Unit]
Description=Pandemonium Telegram Bot
After=network.target

[Service]
Type=simple
User=alyx
WorkingDirectory=/mnt/b/projects/pandemonium-bot
ExecStart=/usr/bin/env uv run python -m pandemonium.tgbot
Restart=always
RestartSec=5
WatchdogSec=60

[Install]
WantedBy=multi-user.target
```

Это решает: автоперезапуск, journald для логов, `systemctl restart pandemonium` вместо `/reboot`.

**Вариант 2: Docker** (для изоляции):

```dockerfile
FROM python:3.12-slim
# Install claude CLI, uv, etc.
COPY . /app
WORKDIR /app
RUN uv sync
CMD ["uv", "run", "python", "-m", "pandemonium.tgbot"]
```

Но Docker создаёт проблему: Claude Code работает с файловой системой проектов. В контейнере нужно маунтить все проекты как volumes. А `--permission-mode bypassPermissions` внутри контейнера не добавляет безопасности — Claude всё равно может писать куда угодно в маунтированных volumes.

**Мой выбор: systemd без Docker.** Claude Code нужен прямой доступ к файловой системе. Контейнеризация добавляет сложность без реальной изоляции.

## Мониторинг

### Чего не хватает

1. **Health endpoint.** Нет HTTP-сервера для проверки alive/ready. Для простого мониторинга — добавить aiohttp server на localhost:8080/health, который отвечает `{"status": "ok", "active_sessions": 0, "uptime": 3600}`.

2. **Metrics.** Нет метрик: количество запросов, средний response time, token usage over time, error rate. Для начала хватит текстового файла или SQLite query. Для production — Prometheus exporter.

3. **Alerting.** Нет уведомлений при: крэше, длинном запросе (> 10 мин), превышении token budget, ошибках Claude Code. Telegram сам может быть каналом алертов (бот пишет в админский чат).

### Что уже есть

- `_recover_interrupted_requests` — при старте помечает незавершённые запросы как ошибки. Это хорошо: нет зомби-сессий после рестарта.
- Логирование через `logging` — структурированно, с уровнями. Можно парсить.
- `meta.json` с токенами — audit trail.

## Безопасность на уровне инфраструктуры

### `--permission-mode bypassPermissions`

Это значит: Claude Code может читать, писать, удалять файлы, запускать команды — без подтверждения. На хостовой машине. С правами пользователя `alyx`.

Это не баг — это design decision для удалённого управления через Telegram. Но:

- Claude Code имеет доступ к `~/.ssh`, `~/.gnupg`, `~/.config`, всем проектам
- Если промпт скомпрометирован (prompt injection через reply chain или загруженный файл), Claude может выполнить произвольные команды
- `extra_env` передаёт `PANDEMONIUM_BOT_TOKEN` дочернему процессу — при утечке это полный доступ к боту

**Минимальные меры:**
- Запускать бот от отдельного пользователя с ограниченными правами
- Ограничить доступ Claude Code к проектным директориям через `--allowedTools` или chroot
- Не передавать `BOT_TOKEN` в env дочернего процесса (использовать файл с restrictive permissions)

### SQLite файл

`pandemonium.db` хранится в `~/.pandemonium/sessions/`. Содержит user IDs, request history, token usage. Нет шифрования, нет access control сверх файловой системы. Для single-user setup — приемлемо. При утечке — потеря приватности, но не безопасности.

## Graceful shutdown

Реализация грамотная:
1. SIGTERM → set event → wait for polling task
2. Cancel active session → notify user → kill subprocess
3. Close DB → close bot session

Это правильный порядок. В FileStorage2 у нас тот же паттерн: SIGTERM → drain connections → flush writes → exit.

Но нет timeout на graceful shutdown. Если `session_manager.shutdown()` зависнет (Claude Code не реагирует на SIGTERM), бот зависнет навсегда. Нужен overall shutdown timeout: 30 секунд, потом force exit.

## Файловая система

### Storage layout

```
~/.pandemonium/sessions/
├── pandemonium.db
├── pandemonium-bot/
│   ├── request_1/
│   │   ├── request.md
│   │   ├── stream_log.md
│   │   ├── report.md
│   │   └── meta.json
│   └── request_2/
│       └── ...
├── downloader/
│   └── ...
└── uploads/
    └── ...
```

Хорошая структура. Но `stream_log.md` может расти неограниченно (длинные сессии Claude). Нет ротации, нет лимита размера. Для диска 500GB — не проблема. Для Raspberry Pi — может быть.

### Uploads

`uploads/` — скачанные из Telegram файлы. Нет очистки. Файлы накапливаются навечно. Нужен cron job или TTL-based cleanup (удалять файлы старше 7 дней).

## Рекомендации по приоритету

1. **systemd unit** — 10 минут работы, решает 80% проблем с reliability
2. **Health endpoint** — простой aiohttp сервер, 30 строк кода
3. **Shutdown timeout** — `asyncio.wait_for(shutdown(), timeout=30)`
4. **Uploads cleanup** — cron или встроенный periodic task
5. **Log rotation** — `RotatingFileHandler` или redirect stdout в journald
6. **Separate user** — `useradd pandemonium`, ограниченные права на проекты

## Резюме

Pandemonium — минимальный по инфраструктуре сервис. Нет Docker, нет orchestration, нет monitoring. Для MVP на домашнем сервере — это плюс: меньше движущих частей. Но при выходе за рамки «один пользователь, один сервер» — нужны systemd, health checks, log rotation, cleanup. Код готов к этим улучшениям: архитектура не мешает, нет hard-coded paths, конфиг отделён от логики. Добавить инфраструктуру — вопрос часов, не дней.

Главный risk — `bypassPermissions`. Это осознанный trade-off, но его нужно документировать и минимизировать blast radius.
