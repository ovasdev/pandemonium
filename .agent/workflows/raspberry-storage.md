# Воркфлоу: filestorage2 на Raspberry Pi (малинка)

## Когда использовать

Когда собеседник говорит: «сохрани на малинку», «загрузи на малинку», «покажи файлы на малинке», «пошарь с малинки», «raspberry storage», «pi storage».

## Подключение

```bash
PI_URL="http://192.168.1.105:4733"
PI_KEY="sk-fs2-3lLwrQ1VoMEK4Zls8JAcSB2qdQpROdatYZvDS8TaSZRv"
AUTH="Authorization: Bearer $PI_KEY"
```

- **Сервер**: Raspberry Pi 5 (minion), LAN 192.168.1.105, порт 4733
- **Доступ**: только из локальной сети

## Типичные сценарии

### Сохранить файл на малинку

1. Загрузить: `curl -s -X POST "$PI_URL/api/files" -H "$AUTH" -F "file=@/path/to/file"`
2. Запомнить `id` и `file_group_id` из ответа
3. Опционально протегировать

### Скачать файл с малинки

1. Найти файл: `curl -s "$PI_URL/api/files?search=name" -H "$AUTH"`
2. Скачать: `curl -s "$PI_URL/api/files/{id}/download" -H "$AUTH" -o /tmp/file.ext`
3. Отправить в Telegram: `$PANDEMONIUM_SEND_FILE /tmp/file.ext "Подпись"`

### Пошарить файл с малинки

1. Найти файл и его `file_group_id`
2. Создать правило: `curl -s -X POST "$PI_URL/api/sharing" -H "$AUTH" -H "Content-Type: application/json" -d '{"resource_type":"file","file_group_id":"<UUID>","visibility":"authenticated"}'`

### Проверить здоровье

```bash
curl -s http://192.168.1.105:4733/api/health
```

## Связанные ресурсы

- **Скилл**: `filestorage2-api` — полный справочник API
- **SSH**: `ssh zulin@192.168.1.105` — прямой доступ к серверу (см. память `raspberry-pi-server.md`)
