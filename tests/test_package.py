"""Smoke test for package import."""


def test_version():
    from hfs_location_client import __version__

    assert __version__ == "0.1.0.dev0"


def test_all_models_importable():
    from hfs_location_client import (
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

    assert all(
        cls is not None
        for cls in [
            Building,
            Road,
            Island,
            IslandStats,
            ReverseGeocodeResult,
            GeocodeResult,
            PlusCodeResult,
            PaginatedResult,
            PaginationMeta,
            HealthStatus,
            HealthChecks,
        ]
    )


def test_all_exceptions_importable():
    from hfs_location_client import (
        AuthError,
        CircuitOpenError,
        LocationRegistryError,
        NotFoundError,
        RateLimitError,
        ServiceUnavailableError,
        ValidationError,
    )

    assert issubclass(NotFoundError, LocationRegistryError)
    assert issubclass(ValidationError, LocationRegistryError)
    assert issubclass(AuthError, LocationRegistryError)
    assert issubclass(RateLimitError, LocationRegistryError)
    assert issubclass(ServiceUnavailableError, LocationRegistryError)
    assert issubclass(CircuitOpenError, LocationRegistryError)
