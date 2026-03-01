"""Smoke test for package import."""


def test_version():
    from hfs_location_client import __version__

    assert __version__ == "0.1.0.dev0"
