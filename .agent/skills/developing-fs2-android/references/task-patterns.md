# Task Patterns — FileStorage2 Android

Detailed code patterns for common development tasks. Referenced from SKILL.md.

## Adding a New Screen (Full Example)

### 1. DTO

```kotlin
// In data/remote/dto/ApiDtos.kt (or separate file for large DTOs)
@JsonClass(generateAdapter = true)
data class WidgetResponse(
    val id: Long,
    val name: String,
    val createdAt: String,
)
```

### 2. API Endpoint

```kotlin
// In data/remote/FileStorageApi.kt
@GET("api/widgets")
suspend fun getWidgets(
    @Query("offset") offset: Int = 0,
    @Query("limit") limit: Int = 50,
): PaginatedResponse<WidgetResponse>

@POST("api/widgets")
suspend fun createWidget(@Body body: CreateWidgetRequest): WidgetResponse
```

### 3. Cache Entity (if offline needed)

```kotlin
// In data/local/entity/CachedWidgetEntity.kt
@Entity(tableName = "cached_widgets")
data class CachedWidgetEntity(
    @PrimaryKey val id: Long,
    val name: String,
    @ColumnInfo(name = "cached_at", defaultValue = "0") val cachedAt: Long = 0,
)
```

### 4. DAO

```kotlin
// In data/local/dao/CachedWidgetDao.kt
@Dao
interface CachedWidgetDao {
    @Query("SELECT * FROM cached_widgets ORDER BY name")
    suspend fun getAll(): List<CachedWidgetEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(widgets: List<CachedWidgetEntity>)

    @Query("DELETE FROM cached_widgets")
    suspend fun deleteAll()
}
```

### 5. Repository

```kotlin
// In data/WidgetRepository.kt
class WidgetRepository @Inject constructor(
    private val api: FileStorageApi,
    private val dao: CachedWidgetDao,
) {
    suspend fun getWidgets(): List<WidgetResponse> = try {
        val response = api.getWidgets()
        dao.upsertAll(response.items.map { it.toEntity() })
        response.items
    } catch (e: Exception) {
        val cached = dao.getAll()
        if (cached.isEmpty()) throw e
        cached.map { it.toResponse() }
    }
}
```

### 6. DI Registration

```kotlin
// In di/DatabaseModule.kt — add DAO provider
@Provides
fun provideCachedWidgetDao(db: AppDatabase): CachedWidgetDao = db.cachedWidgetDao()

// In AppDatabase.kt — add to @Database annotation
@Database(entities = [..., CachedWidgetEntity::class], version = N+1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun cachedWidgetDao(): CachedWidgetDao
}
```

### 7. ViewModel

```kotlin
// In ui/widgets/WidgetViewModel.kt
@HiltViewModel
class WidgetViewModel @Inject constructor(
    private val repository: WidgetRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(WidgetUiState())
    val uiState = _uiState.asStateFlow()

    init { loadWidgets() }

    fun refresh() = loadWidgets()

    private fun loadWidgets() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, error = null) }
            try {
                val widgets = repository.getWidgets()
                _uiState.update { it.copy(widgets = widgets, isLoading = false) }
            } catch (e: Exception) {
                _uiState.update { it.copy(error = e.message, isLoading = false) }
            }
        }
    }
}

data class WidgetUiState(
    val widgets: List<WidgetResponse> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
)
```

### 8. Screen

```kotlin
// In ui/widgets/WidgetScreen.kt
@Composable
fun WidgetScreen(
    viewModel: WidgetViewModel = hiltViewModel(),
    onNavigateBack: () -> Unit = {},
) {
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    // ... Scaffold + content
}
```

### 9. Navigation

```kotlin
// In navigation/AppNavigation.kt — add route
const val WIDGETS = "widgets"

// In NavHost
composable(Routes.WIDGETS) {
    WidgetScreen(onNavigateBack = { navController.popBackStack() })
}
```

## Pagination Pattern

The project uses offset-based pagination:

```kotlin
// ViewModel
fun loadMore() {
    if (uiState.value.isLoadingMore || !uiState.value.hasMorePages) return
    viewModelScope.launch {
        _uiState.update { it.copy(isLoadingMore = true) }
        val offset = uiState.value.items.size
        val response = repository.getItems(offset = offset, limit = PAGE_SIZE)
        _uiState.update { state ->
            state.copy(
                items = state.items + response.items,
                hasMorePages = response.items.size == PAGE_SIZE,
                isLoadingMore = false,
            )
        }
    }
}

// Screen — trigger load at end of list
LazyColumn {
    items(uiState.items, key = { it.id }) { item -> ItemRow(item) }
    if (uiState.hasMorePages) {
        item {
            LaunchedEffect(Unit) { viewModel.loadMore() }
            CircularProgressIndicator()
        }
    }
}
```

## Filter Pattern

```kotlin
data class ActiveFilters(
    val type: String? = null,
    val dateFrom: String? = null,
    val dateTo: String? = null,
    val tagIds: List<Long> = emptyList(),
    val collectionId: Long? = null,
) {
    val isActive: Boolean get() = type != null || dateFrom != null || tagIds.isNotEmpty() || collectionId != null
}

// In ViewModel — reset pagination on filter change
fun updateFilters(filters: ActiveFilters) {
    _uiState.update { it.copy(activeFilters = filters, items = emptyList(), hasMorePages = true) }
    loadItems()
}
```

## Error Handling in Repositories

```kotlin
// Network-first with cache fallback
suspend fun getData(): List<Item> = try {
    val remote = api.getData()
    cacheLocally(remote)
    remote
} catch (e: Exception) {
    val cached = dao.getCached()
    if (cached.isEmpty()) throw e  // no fallback available
    cached
}

// Fire-and-forget with logging
suspend fun syncSilently() = try {
    api.sync()
} catch (e: Exception) {
    Log.w(TAG, "Sync failed", e)
    // Don't rethrow — caller doesn't need to know
}
```
