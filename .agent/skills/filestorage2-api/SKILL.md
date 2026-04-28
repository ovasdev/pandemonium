---
name: filestorage2-api
description: "Universal reference for filestorage2 server REST API. Triggers when working with any filestorage2 instance — uploading, downloading, searching, tagging, sharing files, managing collections. Server-agnostic: specific server configs live in workflows."
---

# filestorage2 — API Reference

Универсальный справочник по API filestorage2. Конкретные серверы (адреса, ключи) — в воркфлоу.

## MCP vs curl

Если сервер filestorage2 зарегистрирован как MCP в Claude Code (`mcp__filestorage2__*`) — предпочитай MCP-инструменты (`upload_file`, `search_files`, `list_files`, `attach_tags`, `add_files_to_collection` и т.д.) над curl. Этот документ — справочник HTTP API, полезен как fallback и для понимания того, что MCP делает под капотом.

## Authentication

```
Authorization: Bearer <API_KEY>
```

API keys имеют префикс `sk-fs2-`. Передаются в заголовке `Authorization: Bearer`.

## Идентификаторы: id vs UUID

Сервер использует два типа идентификаторов:

- **Числовой `id`** (целое) — возвращается в ответах, используется в путях ресурсов первого класса: `/api/files/{id}` (GET/PATCH/DELETE по файлу, download, thumbnail, versions), а также как значение query-параметров фильтрации (`tag_ids`, `collection_ids`).
- **UUID** (`file_group_id`, `tag.uuid`, `collection.uuid`) — используется во **всех связочных** эндпоинтах (присвоение/снятие тегов, bulk-операции, sharing).

**Правило:** в путях вида `/api/files/{FGID}/tags`, `/api/tags/{TAG_UUID}/files`, `/api/sharing/...` и в телах связочных запросов (`tag_uuids`, `file_group_ids`) — **только UUID**. Числовой id здесь вернёт 400 `UUID parsing failed`. В теле связочных запросов поле называется `tag_uuids`/`file_group_ids`, **не** `tag_ids`/`file_ids`.

## Files

### Upload

```bash
curl -s -X POST "$BASE_URL/api/files" \
  -H "Authorization: Bearer $API_KEY" \
  -F "file=@/path/to/file;filename=display-name.ext" \
  -F "description=Optional description"
```

Response: file object с `id`, `file_group_id` (UUID), `original_filename`, `file_size`, `mime_type`, `uploaded_at`.

### List

```bash
curl -s "$BASE_URL/api/files?limit=50&offset=0" \
  -H "Authorization: Bearer $API_KEY"
```

Query params:
| Param | Description |
|---|---|
| `limit`, `offset` | Пагинация |
| `search` | По имени файла |
| `tag_ids` | CSV: `1,2,3` |
| `collection_ids` | CSV |
| `type` | MIME категория: `image`, `document`, `video`, `audio` |
| `date_from`, `date_to` | ISO 8601 |
| `sort`, `order` | Сортировка |
| `deleted` | Включать удалённые |

Response: `{"items": [...], "total": N, "offset": 0, "limit": 50}`

### Full-text search

```bash
curl -s "$BASE_URL/api/files/search?q=keyword&limit=20" \
  -H "Authorization: Bearer $API_KEY"
```

### Get metadata

```bash
curl -s "$BASE_URL/api/files/{id}" -H "Authorization: Bearer $API_KEY"
```

### Update metadata

```bash
curl -s -X PATCH "$BASE_URL/api/files/{id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"description": "new desc", "original_filename": "new-name.ext"}'
```

### Download

```bash
curl -s "$BASE_URL/api/files/{id}/download" \
  -H "Authorization: Bearer $API_KEY" -o output.ext
```

Supports `Range` header for partial content (206).

### Thumbnail (images)

```bash
curl -s "$BASE_URL/api/files/{id}/thumbnail?size=200" \
  -H "Authorization: Bearer $API_KEY" -o thumb.jpg
```

Sizes: `200` (default), `600`.

### Delete (soft)

```bash
curl -s -X DELETE "$BASE_URL/api/files/{id}" -H "Authorization: Bearer $API_KEY"
```

### Versions

```bash
# List versions
curl -s "$BASE_URL/api/files/{id}/versions" -H "Authorization: Bearer $API_KEY"

# Upload new version
curl -s -X POST "$BASE_URL/api/files/{id}/versions" \
  -H "Authorization: Bearer $API_KEY" -F "file=@/path/to/new-version"

# Rollback
curl -s -X POST "$BASE_URL/api/files/{id}/rollback" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"target_version_id": 1}'
```

### Deduplication

```bash
curl -s -X POST "$BASE_URL/api/files/check-hash" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sha256_hash": "abcdef..."}'
# Response: {"exists": true, "file_id": 1, "file_group_id": "uuid"}
```

## Tags

```bash
# List all tags
curl -s "$BASE_URL/api/tags" -H "Authorization: Bearer $API_KEY"

# Create tag
curl -s -X POST "$BASE_URL/api/tags" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "TagName", "color": "#ff5733"}'

# Update tag
curl -s -X PATCH "$BASE_URL/api/tags/{id}" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "New name", "color": "#hex"}'

# Delete tag
curl -s -X DELETE "$BASE_URL/api/tags/{id}" -H "Authorization: Bearer $API_KEY"

# Get file's tags (UUID в пути — file_group_id)
curl -s "$BASE_URL/api/files/{file_group_id}/tags" -H "Authorization: Bearer $API_KEY"

# Tag a file (UUID в пути, tag_uuids в теле)
curl -s -X POST "$BASE_URL/api/files/{file_group_id}/tags" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tag_uuids": ["<tag-uuid-1>", "<tag-uuid-2>"]}'

# Remove tag from file (оба параметра — UUID)
curl -s -X DELETE "$BASE_URL/api/files/{file_group_id}/tags/{tag_uuid}" \
  -H "Authorization: Bearer $API_KEY"

# Bulk tag files (UUID тега в пути, file_group_ids в теле)
curl -s -X POST "$BASE_URL/api/tags/{tag_uuid}/files" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"file_group_ids": ["<fgid-1>", "<fgid-2>"]}'
```

## Collections

```bash
# List collections
curl -s "$BASE_URL/api/collections" -H "Authorization: Bearer $API_KEY"

# Create collection
curl -s -X POST "$BASE_URL/api/collections" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Collection", "description": "..."}'

# Add files to collection (UUID в пути, file_group_ids в теле)
curl -s -X POST "$BASE_URL/api/collections/{collection_uuid}/files" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"file_group_ids": ["<fgid-1>", "<fgid-2>"]}'
```

## Sharing (v2)

```bash
# Create share rule — authenticated (all logged-in users)
curl -s -X POST "$BASE_URL/api/sharing" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"resource_type":"file","file_group_id":"<UUID>","visibility":"authenticated"}'

# Create share rule — specific user (by user UUID)
curl -s -X POST "$BASE_URL/api/sharing" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"resource_type":"file","file_group_id":"<UUID>","visibility":"user","target_user_uuid":"<USER_UUID>"}'

# Create share rule — collection to specific user
curl -s -X POST "$BASE_URL/api/sharing" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"resource_type":"collection","collection_uuid":"<UUID>","visibility":"user","target_user_uuid":"<USER_UUID>"}'

# Create share rule — link-only with optional password & expiry
curl -s -X POST "$BASE_URL/api/sharing" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"resource_type":"file","file_group_id":"<UUID>","visibility":"link_only","password":"secret","expires_at":"2026-12-31T23:59:59Z","max_downloads":10}'

# List share rules (optionally filter by resource_type, file_group_id, tag_uuid, collection_uuid)
curl -s "$BASE_URL/api/sharing" -H "Authorization: Bearer $API_KEY"
curl -s "$BASE_URL/api/sharing?resource_type=file&file_group_id=<UUID>" -H "Authorization: Bearer $API_KEY"

# Delete share rule
curl -s -X DELETE "$BASE_URL/api/sharing/{uuid}" -H "Authorization: Bearer $API_KEY"
```

### Visibility levels

| Visibility | Description | Required fields |
|---|---|---|
| `public` | Доступен всем без авторизации | — |
| `authenticated` | Доступен всем залогиненным пользователям | — |
| `user` | Доступен конкретному пользователю | `target_user_uuid` |
| `link_only` | Доступен только по прямой ссылке (+ опц. пароль) | — |

### Optional fields for create

| Field | Type | Description |
|---|---|---|
| `target_user_uuid` | string (UUID) | UUID пользователя-получателя (для `visibility: "user"`) |
| `password` | string | Пароль для доступа (для `link_only`) |
| `expires_at` | ISO 8601 datetime | Срок действия правила |
| `max_downloads` | integer | Лимит скачиваний |

### Response fields

В ответе `target_user_uuid` и `target_user_name` присутствуют, если правило адресное (`visibility: "user"`).
`has_password: true` — если задан пароль. Сам пароль не возвращается.

Resource types: `file`, `tag`, `collection`.

## Health

```bash
curl -s "$BASE_URL/api/health"
# {"status": "ok", "database": "connected", "minio": "connected"}
```

## Limits

- Rate limit: 120 req/min
- Upload size: server-configurable (`max_upload_size`)
- Filename: 1-255 chars
- Tag name: 1-100 chars
