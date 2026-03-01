# hfs-location-client

Python client library for [HFS Location Registry](https://github.com/High-Functioning-Solutions/location-registry-api) API.

Provides async and sync HTTP adapters with circuit breaker, retry, and typed Pydantic response models.

## Status

**v0.1.0-dev** — Under development. Not yet ready for production use.

## Requirements

- Python >= 3.11
- Location Registry API running and accessible

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check src/
mypy src/
```

## License

MIT
