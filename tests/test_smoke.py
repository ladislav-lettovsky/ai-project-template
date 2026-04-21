"""Smoke test — proves the package is importable and the test harness works.

Replace or delete once you have real tests. Kept trivial so `just check`
passes immediately on a fresh fork.
"""


def test_package_is_importable() -> None:
    """The package directory exists and is importable as a module."""
    import your_package  # noqa: F401

    # After renaming `your_package`, update this import accordingly.
