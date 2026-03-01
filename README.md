# hfs-location-client

Python client library for the [HFS Location Registry API](https://lr.highfunctioningsolutions.com). Provides both async and sync adapters with automatic retry, circuit breaker protection, and typed Pydantic response models.

## Install

```bash
pip install hfs-location-client
```

Or from source:

```bash
pip install git+https://github.com/High-Functioning-Solutions/hfs-location-client.git
```

## Quick Start

### Async Client (Quart, FastAPI)

```python
from hfs_location_client import LocationRegistryClient

async def main():
    async with LocationRegistryClient(
        base_url="https://lr.highfunctioningsolutions.com/api/v1",
        api_key="lr_live_key_...",
    ) as client:
        # Reverse geocode coordinates in Nassau
        result = await client.reverse_geocode(25.048, -77.355)
        print(f"Plus Code: {result.plus_code}")

        # Search buildings near a point
        buildings = await client.search_buildings(
            lat=25.048, lng=-77.355, radius_m=500,
        )
        for b in buildings.data:
            print(f"  {b.plus_code} ({b.confidence_tier})")

        # List all islands
        islands = await client.list_islands()
        print(f"Islands: {len(islands)}")
```

### Sync Client (Flask, Django, scripts)

```python
from hfs_location_client import LocationRegistrySyncClient

with LocationRegistrySyncClient(
    base_url="https://lr.highfunctioningsolutions.com/api/v1",
    api_key="lr_live_key_...",
) as client:
    health = client.health_check()
    print(f"API status: {health.status}")

    islands = client.list_islands()
    for island in islands:
        print(f"  {island.name} ({island.building_count} buildings)")
```

## API Methods

Both clients expose identical methods:

| Method | Returns | Description |
|--------|---------|-------------|
| `get_building(plus_code)` | `Building` | Get building by Plus Code |
| `search_buildings(...)` | `PaginatedResult[Building]` | Search with spatial/attribute filters |
| `get_road(road_id)` | `Road` | Get road by UUID |
| `search_roads(...)` | `PaginatedResult[Road]` | Search roads |
| `reverse_geocode(lat, lng)` | `ReverseGeocodeResult` | Coordinates to nearest location |
| `geocode(query)` | `list[GeocodeResult]` | Text search for locations |
| `encode_plus_code(lat, lng)` | `PlusCodeResult` | Encode coordinates to Plus Code |
| `decode_plus_code(code)` | `PlusCodeResult` | Decode Plus Code to coordinates |
| `validate_plus_code(code)` | `bool` | Check if Plus Code is valid |
| `list_islands()` | `list[Island]` | List all 19 island groups |
| `get_island(id_or_name)` | `Island` | Get island by ID or name |
| `get_island_stats(id_or_name)` | `IslandStats` | Coverage statistics for an island |
| `health_check()` | `HealthStatus` | API readiness check |

## Error Handling

All API errors are mapped to typed exceptions:

```python
from hfs_location_client import LocationRegistrySyncClient
from hfs_location_client.exceptions import (
    NotFoundError,
    ValidationError,
    AuthError,
    RateLimitError,
    CircuitOpenError,
)

client = LocationRegistrySyncClient(base_url, api_key)

try:
    building = client.get_building("INVALID+CODE")
except NotFoundError:
    print("Building not found")
except ValidationError:
    print("Invalid request parameters")
except AuthError:
    print("Invalid or missing API key")
except RateLimitError as e:
    print(f"Rate limited, retry after {e.retry_after}s")
except CircuitOpenError:
    print("Circuit breaker open — API may be down")
```

| HTTP Status | Exception | Description |
|-------------|-----------|-------------|
| 400, 422 | `ValidationError` | Invalid request |
| 401, 403 | `AuthError` | Authentication failed |
| 404 | `NotFoundError` | Resource not found |
| 429 | `RateLimitError` | Rate limit exceeded (auto-retried) |
| 5xx | `ServiceUnavailableError` | Server error (auto-retried) |

## Configuration

```python
client = LocationRegistryClient(
    base_url="https://lr.highfunctioningsolutions.com/api/v1",
    api_key="lr_live_key_...",
    timeout=5.0,                    # Request timeout (seconds)
    max_retries=3,                  # Retry attempts for 429/5xx
    circuit_breaker_threshold=3,    # Failures before circuit opens
    circuit_breaker_reset=30.0,     # Seconds before retry after open
)
```

## Resilience

- **Retry**: 429 and 5xx errors are automatically retried with exponential backoff. 429 responses respect the `Retry-After` header.
- **Circuit Breaker**: After consecutive failures, the circuit opens and requests fail fast with `CircuitOpenError`. Automatically recovers after the reset timeout.

## Development

```bash
pip install -e '.[dev]'
pytest tests/ -v --ignore=tests/integration
ruff check src/
mypy src/
```

Integration tests require a running LR API:

```bash
export LR_API_KEY="lr_live_key_..."
export LR_BASE_URL="http://localhost:5001/api/v1"
pytest tests/integration/ -v -m integration
```

## License

MIT
