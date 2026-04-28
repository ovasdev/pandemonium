# Воркфлоу: filestorage2 на marginalias.net

## Когда использовать

Когда собеседник говорит: «сохрани на маргиналии», «выложи на сервер», «загрузи на marginalias», «пошарь мне файл» (без уточнения — по умолчанию marginalias).

## Подключение

```bash
# MG_URL и MG_KEY берутся из окружения (.env загружается при старте бота).
# Если вызываешь из shell — сначала `source .env` или экспортируй вручную.
MG_URL="${MG_URL:-https://marginalias.net}"
MG_KEY="${MG_KEY:?set MG_KEY in environment}"
AUTH="Authorization: Bearer $MG_KEY"
```

- **Сервер**: https://marginalias.net (публичный)
- **Protos**: user_id=4, storage_id=5

## Данные собеседника (Zulin)

- user_id=1, storage_id=1
- passphrase: `ночь-амёба-нож-мама-мама-мама`

Для операций, требующих JWT собеседника (например, шаринг от его имени):

```bash
TOKEN=$(curl -s -X POST "$MG_URL/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"passphrase": "ночь-амёба-нож-мама-мама-мама"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

## Типичные сценарии

### Сохранить файл на marginalias

1. Загрузить: `curl -s -X POST "$MG_URL/api/files" -H "$AUTH" -F "file=@/path/to/file;filename=name.ext" -F "description=..."`
2. Запомнить `id` и `file_group_id` из ответа

### Пошарить файл с собеседником

1. Загрузить файл (или найти существующий)
2. Создать правило шаринга:
   ```bash
   curl -s -X POST "$MG_URL/api/sharing" \
     -H "$AUTH" -H "Content-Type: application/json" \
     -d '{"resource_type":"file","file_group_id":"<UUID>","visibility":"authenticated"}'
   ```

### Скачать файл с marginalias

1. Найти: `curl -s "$MG_URL/api/files?search=name" -H "$AUTH"`
2. Скачать: `curl -s "$MG_URL/api/files/{id}/download" -H "$AUTH" -o /tmp/file.ext`
3. Отправить в Telegram: `$PANDEMONIUM_SEND_FILE /tmp/file.ext`

## Связанные ресурсы

- **Скилл**: `filestorage2-api` — полный справочник API
- **Память**: `marginalias-server-creds.md`, `workflow-fs2-upload-share.md`
