---
name: developing-fs2-android
description: "Guides development workflow for the FileStorage2 Android app — a Kotlin/Compose/Hilt/Room/WorkManager client at /mnt/b/projects/filestorage2/android/. ALWAYS use this skill when the user works on, discusses, or asks about the fs2 Android app, even if they just say 'android', 'приложение', 'клиент', or 'мобилка'. Covers: adding screens, API endpoints, Room migrations, sync logic, bug fixes, and build. Also triggers on mentions of filestorage2, fs2, or any file path under /mnt/b/projects/filestorage2/android/. Does NOT apply to the fs2 Rust server or generic Android questions unrelated to this project."
compatibility: "Requires Android SDK, Kotlin 2.0+, Gradle, Java 17"
metadata:
  project-path: "/mnt/b/projects/filestorage2/android/"
  version: "1.0.0"
---

# Developing FileStorage2 Android

Workflow guide for the FileStorage2 Android app. For architecture reference and gotchas, see the `filestorage2-android` skill.

> See also: `filestorage2-android` (architecture reference), `android-jetpack-compose` (general patterns)

## Before Starting

1. Read `_memory/_index.md` at `/mnt/b/projects/filestorage2/android/_memory/` — contains review findings and improvement plan
2. Check git log for recent changes in the area being modified
3. Verify the server is running if the task involves network features:
   ```bash
   curl http://localhost:4733/api/health
   ```

## Decision Tree

```
What type of task?
├─ New screen/feature     → "Adding a Screen" below
├─ New API endpoint       → "Adding an API Endpoint"
├─ Database change        → "Room Migration" (CRITICAL — follow exactly)
├─ Sync/upload change     → "Modifying Sync Logic"
├─ Bug fix                → "Bug Fix Workflow"
├─ UI-only change         → Edit the @Composable directly, update ViewModel if state changes
└─ Build/release          → "Build Commands"
```

## Adding a Screen

Follow this order — each step depends on the previous:

1. **DTO** (if new data): `data/remote/dto/ApiDtos.kt` — add data class
2. **API endpoint**: `data/remote/FileStorageApi.kt` — add Retrofit method
3. **Cache entity** (if offline needed): `data/local/entity/` — new entity + DAO + migration
4. **Repository**: `data/` — create `XxxRepository.kt` with network-first, cache-fallback pattern
5. **DI**: Register repository in `di/NetworkModule.kt` or `di/DatabaseModule.kt`
6. **ViewModel**: `ui/xxx/XxxViewModel.kt` — `@HiltViewModel`, expose `StateFlow<UiState>`
7. **Screen**: `ui/xxx/XxxScreen.kt` — `@Composable`, collect state via `collectAsStateWithLifecycle()`
8. **Navigation**: `navigation/AppNavigation.kt` — add route constant + `composable()` entry

Pattern references for each step: `references/task-patterns.md`

## Adding an API Endpoint

1. Add method to `FileStorageApi.kt`:
   ```kotlin
   @GET("api/xxx")
   suspend fun getXxx(@Query("param") param: String): XxxResponse
   ```
2. Add response DTO to `ApiDtos.kt` (or relevant DTO file)
3. Add repository method with cache fallback if needed
4. Wire into ViewModel

## Room Migration (CRITICAL)

Room migration errors crash the app on startup with no recovery. Follow this exactly:

1. **Increment version** in `AppDatabase.kt`: `version = N+1`
2. **Add migration object** in `AppDatabase.Companion`:
   ```kotlin
   val MIGRATION_N_NP1 = object : Migration(N, N+1) {
       override fun migrate(db: SupportSQLiteDatabase) {
           db.execSQL("ALTER TABLE xxx ADD COLUMN yyy TEXT NOT NULL DEFAULT ''")
       }
   }
   ```
3. **Register migration** in `di/DatabaseModule.kt`: `.addMigrations(MIGRATION_N_NP1)`
4. **Update entity** with matching `@ColumnInfo(defaultValue = "...")` — must match the SQL DEFAULT exactly
5. **Add indices** in both migration SQL (`CREATE INDEX`) and entity annotation (`@Entity(indices = [...])`)
6. **Test**: build and run — Room validates schema at startup

Common mistake: forgetting `@ColumnInfo(defaultValue = ...)` when the migration has `DEFAULT`. Room schema validation will crash.

## Modifying Sync Logic

The sync system has 4 phases (see `filestorage2-android` skill for details). When modifying:

1. **Understand the phase** — which of the 4 phases does this change affect?
2. **Check SyncWorker.kt** — main orchestrator, runs phases sequentially with Mutex
3. **Check UploadManager.kt** — handles concurrent uploads with Semaphore
4. **Watch for race conditions** — cache updates need `@Transaction` in DAOs
5. **Test with real device** — sync bugs are hard to reproduce in emulators

Key files: `SyncWorker.kt`, `UploadManager.kt`, `FileScannerService.kt`, `SyncScheduler.kt`, `SyncStatusTracker.kt`

## Bug Fix Workflow

1. **Read the bug description** and identify which layer is affected (UI / ViewModel / Repository / DB / Sync)
2. **Check `_memory/review-2026-03-13.md`** — 22 known issues documented with severity
3. **Reproduce** — understand the trigger condition
4. **Fix in the right layer** — don't patch symptoms in UI when the root cause is in data
5. **Check for similar patterns** — the same bug pattern may exist in other files

## Known Critical Issues

These are documented in `_memory/review-2026-03-13.md`:

- Missing `serverUrl` in Phase 3 upload — new files get empty server_url
- Race conditions in cache updates — unprotected delete+insert
- No runtime permissions for READ_MEDIA_IMAGES/VIDEO on API 33+
- NPE in `FileScannerService` — `DocumentFile.listFiles()` returns null
- Non-atomic token updates in SecureStorage

## Build Commands

```bash
cd /mnt/b/projects/filestorage2/android

# Debug build
./gradlew assembleDebug
# → app/build/outputs/apk/debug/app-debug.apk

# Release build
./gradlew assembleRelease

# Clean build (when things break)
./gradlew clean assembleDebug

# Check compilation without building APK
./gradlew compileDebugKotlin
```

## Server (for testing)

```bash
# Start server
cd /mnt/b/projects/filestorage2/server
RUST_LOG=info,tower_http=debug nohup ./target/release/filestorage2 --config config.toml >> server.log 2>&1 &

# Docker services (PostgreSQL + MinIO)
cd /mnt/b/projects/filestorage2
docker compose -f docker-compose.dev.yml up -d

# Health check
curl http://localhost:4733/api/health
```

## Pre-Commit Checklist

**Critical**
- [ ] App builds: `./gradlew assembleDebug`
- [ ] Room migration matches entity annotations (defaultValue, indices)
- [ ] No hardcoded URLs or tokens

**Important**
- [ ] New DAOs registered in `DatabaseModule.kt`
- [ ] New repositories registered in DI modules
- [ ] Navigation routes added for new screens
- [ ] StateFlow exposed as `.asStateFlow()` (not mutable)

## Project Structure Quick Reference

```
com.filestorage2.android/
├── di/              — Hilt modules (Network, Database)
├── data/
│   ├── remote/      — FileStorageApi, DTOs, interceptors
│   ├── local/       — Room DB (v9), entities, DAOs, mappers
│   └── *Repository  — 12 repositories
├── sync/            — SyncWorker, UploadManager, FileScannerService
├── ui/              — MVVM screens (files, dashboard, settings, federation, invites)
└── navigation/      — Single-activity Compose nav
```
