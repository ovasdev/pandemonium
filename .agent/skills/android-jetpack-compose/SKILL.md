---
name: android-jetpack-compose
description: "Provides modern Android development patterns with Kotlin, Jetpack Compose, Hilt, Room, WorkManager, Retrofit, and Material3. Triggers when writing or reviewing Android app code using Compose UI, setting up Hilt DI, working with Room database, implementing WorkManager tasks, or building Retrofit API clients. Also applies when the user asks about Compose state management, navigation, Material3 theming, or Android architecture (MVVM, Clean Architecture). Does NOT trigger for project-specific fs2 workflow questions — use developing-fs2-android for those."
compatibility: "Requires Android SDK, Kotlin 2.0+, Gradle"
metadata:
  version: "1.0.0"
  category: "android"
---

# Android Jetpack Compose Patterns

Modern Android development patterns: Kotlin + Compose + Hilt + Room + Retrofit + WorkManager.

> See also: `developing-fs2-android` (project-specific workflow for FileStorage2)

## Decision Tree

```
What are you building?
├─ UI screen              → "Compose UI" section
├─ State management       → "ViewModel + StateFlow"
├─ Dependency injection   → "Hilt DI"
├─ Local database         → "Room Database"
├─ Network layer          → "Retrofit + OkHttp"
├─ Background work        → "WorkManager"
├─ Navigation             → "Compose Navigation"
└─ Theming                → "Material3 Theme"
```

## Compose UI

### Screen structure

```kotlin
@Composable
fun FeatureScreen(
    viewModel: FeatureViewModel = hiltViewModel(),
    onNavigate: (String) -> Unit = {},
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = { /* TopAppBar */ },
    ) { padding ->
        when {
            uiState.isLoading -> CircularProgressIndicator()
            uiState.error != null -> ErrorMessage(uiState.error!!)
            else -> FeatureContent(
                state = uiState,
                onAction = viewModel::onAction,
                modifier = Modifier.padding(padding),
            )
        }
    }
}
```

### Key principles

- Screens are `@Composable` functions, not classes
- State flows down, events flow up (unidirectional data flow)
- Use `collectAsStateWithLifecycle()` — not `collectAsState()` — to respect lifecycle
- Hoist state: screens receive state + callbacks, don't own business logic
- Use `LaunchedEffect(key)` for side effects triggered by state changes
- Use `remember { }` for expensive computations within composition
- Use `derivedStateOf { }` when state depends on other state

### Lists

```kotlin
LazyColumn {
    items(
        items = fileList,
        key = { it.id },  // stable keys for efficient recomposition
    ) { file ->
        FileListItem(file = file, onClick = { onFileClick(file.id) })
    }
}
```

### Dialogs and Bottom Sheets

```kotlin
// State-driven dialog
if (uiState.showDeleteDialog) {
    AlertDialog(
        onDismissRequest = { viewModel.dismissDeleteDialog() },
        title = { Text("Delete?") },
        confirmButton = {
            TextButton(onClick = { viewModel.confirmDelete() }) { Text("Delete") }
        },
        dismissButton = {
            TextButton(onClick = { viewModel.dismissDeleteDialog() }) { Text("Cancel") }
        },
    )
}

// Bottom sheet
ModalBottomSheet(onDismissRequest = { /* ... */ }) {
    // Content
}
```

## ViewModel + StateFlow

```kotlin
@HiltViewModel
class FeatureViewModel @Inject constructor(
    private val repository: FeatureRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(FeatureUiState())
    val uiState = _uiState.asStateFlow()

    init {
        loadData()
    }

    fun onAction(action: FeatureAction) {
        when (action) {
            is FeatureAction.Refresh -> loadData()
            is FeatureAction.Delete -> deleteItem(action.id)
        }
    }

    private fun loadData() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true) }
            try {
                val data = repository.getData()
                _uiState.update { it.copy(items = data, isLoading = false) }
            } catch (e: Exception) {
                _uiState.update { it.copy(error = e.message, isLoading = false) }
            }
        }
    }
}

data class FeatureUiState(
    val items: List<ItemModel> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
)

sealed interface FeatureAction {
    data object Refresh : FeatureAction
    data class Delete(val id: Long) : FeatureAction
}
```

### Patterns

- Expose `StateFlow`, not `MutableStateFlow` — use `.asStateFlow()`
- Use `_uiState.update { }` — thread-safe atomic updates
- Use `sealed interface` for actions (type-safe, exhaustive `when`)
- One ViewModel per screen, injected via `hiltViewModel()`

## Hilt DI

### Setup

```kotlin
// Application
@HiltAndroidApp
class MyApp : Application()

// Activity
@AndroidEntryPoint
class MainActivity : ComponentActivity()

// ViewModel — auto-injected
@HiltViewModel
class MyViewModel @Inject constructor(
    private val repo: MyRepository,
) : ViewModel()

// Worker
@HiltWorker
class MyWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val api: MyApi,  // normal injection
) : CoroutineWorker(context, params)
```

### Modules

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {
    @Provides
    @Singleton
    fun provideRetrofit(): Retrofit = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .addConverterFactory(MoshiConverterFactory.create())
        .build()

    @Provides
    @Singleton
    fun provideApi(retrofit: Retrofit): MyApi =
        retrofit.create(MyApi::class.java)
}

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {
    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext ctx: Context): AppDatabase =
        Room.databaseBuilder(ctx, AppDatabase::class.java, "app.db")
            .addMigrations(/* ... */)
            .build()

    @Provides
    fun provideMyDao(db: AppDatabase): MyDao = db.myDao()
}
```

## Room Database

### Entity

```kotlin
@Entity(
    tableName = "items",
    indices = [Index(value = ["server_id"], unique = true)],
)
data class ItemEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    @ColumnInfo(name = "server_id") val serverId: String,
    @ColumnInfo(name = "name") val name: String,
    @ColumnInfo(name = "created_at", defaultValue = "0") val createdAt: Long = 0,
)
```

### DAO

```kotlin
@Dao
interface ItemDao {
    @Query("SELECT * FROM items WHERE server_id = :serverId")
    suspend fun getByServerId(serverId: String): ItemEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(item: ItemEntity)

    @Query("DELETE FROM items WHERE id = :id")
    suspend fun deleteById(id: Long)

    @Transaction
    suspend fun replaceAll(items: List<ItemEntity>) {
        deleteAll()
        insertAll(items)
    }
}
```

### Migration (critical — errors crash the app)

```kotlin
val MIGRATION_N_NP1 = object : Migration(N, N + 1) {
    override fun migrate(db: SupportSQLiteDatabase) {
        db.execSQL("ALTER TABLE items ADD COLUMN description TEXT NOT NULL DEFAULT ''")
        db.execSQL("CREATE INDEX IF NOT EXISTS index_items_created_at ON items(created_at)")
    }
}
```

**Rules:**
- `@ColumnInfo(defaultValue = "...")` must match the SQL `DEFAULT` exactly
- Indices in `@Entity(indices = [...])` must also appear as `CREATE INDEX` in migration
- Always register migration in the DI module: `.addMigrations(MIGRATION_N_NP1)`
- Room validates schema at startup — mismatches = crash with no recovery

## Retrofit + OkHttp

```kotlin
interface MyApi {
    @GET("api/items")
    suspend fun getItems(
        @Query("offset") offset: Int = 0,
        @Query("limit") limit: Int = 50,
    ): PaginatedResponse<ItemDto>

    @POST("api/items")
    suspend fun createItem(@Body body: CreateItemRequest): ItemDto

    @Multipart
    @POST("api/upload")
    suspend fun uploadFile(
        @Part file: MultipartBody.Part,
        @Part("metadata") metadata: RequestBody,
    ): UploadResponse
}
```

### Repository pattern (network-first, cache-fallback)

```kotlin
class ItemRepository @Inject constructor(
    private val api: MyApi,
    private val dao: ItemDao,
) {
    suspend fun getItems(): List<ItemDto> = try {
        val remote = api.getItems()
        dao.replaceAll(remote.items.map { it.toEntity() })
        remote.items
    } catch (e: Exception) {
        val cached = dao.getAll()
        if (cached.isEmpty()) throw e
        cached.map { it.toDto() }
    }
}
```

## WorkManager

```kotlin
@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val repository: ItemRepository,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = try {
        repository.syncAll()
        Result.success()
    } catch (e: Exception) {
        if (runAttemptCount < 3) Result.retry() else Result.failure()
    }
}

// Scheduling
class SyncScheduler @Inject constructor(
    private val workManager: WorkManager,
) {
    fun schedulePeriodicSync() {
        val request = PeriodicWorkRequestBuilder<SyncWorker>(1, TimeUnit.HOURS)
            .setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build())
            .build()
        workManager.enqueueUniquePeriodicWork("sync", ExistingPeriodicWorkPolicy.KEEP, request)
    }
}
```

## Compose Navigation

```kotlin
object Routes {
    const val HOME = "home"
    const val DETAIL = "detail/{itemId}"
    fun detail(id: Long) = "detail/$id"
}

@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = Routes.HOME) {
        composable(Routes.HOME) {
            HomeScreen(onItemClick = { id -> navController.navigate(Routes.detail(id)) })
        }
        composable(
            route = Routes.DETAIL,
            arguments = listOf(navArgument("itemId") { type = NavType.LongType }),
        ) { backStackEntry ->
            val itemId = backStackEntry.arguments?.getLong("itemId") ?: return@composable
            DetailScreen(itemId = itemId, onBack = { navController.popBackStack() })
        }
    }
}
```

## Material3 Theme

```kotlin
@Composable
fun AppTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colorScheme = if (darkTheme) darkColorScheme() else lightColorScheme()
    MaterialTheme(colorScheme = colorScheme, content = content)
}

// Usage: colors from theme, not hardcoded
Text(text = "Hello", color = MaterialTheme.colorScheme.onSurface)
Icon(imageVector = Icons.Default.Search, tint = MaterialTheme.colorScheme.primary)
```

## Images (Coil 3)

```kotlin
AsyncImage(
    model = imageUrl,
    contentDescription = "Photo",
    contentScale = ContentScale.Crop,
    modifier = Modifier.size(120.dp).clip(RoundedCornerShape(8.dp)),
)
```
