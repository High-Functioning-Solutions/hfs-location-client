"""HFS Location Client — Python client for Location Registry API."""

__version__ = "0.1.0.dev0"

from hfs_location_client.client import LocationRegistryClient
from hfs_location_client.exceptions import (
    AuthError,
    CircuitOpenError,
    LocationRegistryError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from hfs_location_client.models import (
    Building,
    GeocodeResult,
    HealthChecks,
    HealthStatus,
    Island,
    IslandStats,
    PaginatedResult,
    PaginationMeta,
    PlusCodeResult,
    ReverseGeocodeResult,
    Road,
)
from hfs_location_client.sync_client import LocationRegistrySyncClient

__all__ = [
    # Version
    "__version__",
    # Clients
    "LocationRegistryClient",
    "LocationRegistrySyncClient",
    # Models
    "Building",
    "Road",
    "Island",
    "IslandStats",
    "ReverseGeocodeResult",
    "GeocodeResult",
    "PlusCodeResult",
    "PaginatedResult",
    "PaginationMeta",
    "HealthStatus",
    "HealthChecks",
    # Exceptions
    "LocationRegistryError",
    "NotFoundError",
    "ValidationError",
    "AuthError",
    "RateLimitError",
    "ServiceUnavailableError",
    "CircuitOpenError",
]
