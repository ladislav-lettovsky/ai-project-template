"""Tests for ``your_package.farewell``."""

from __future__ import annotations

import inspect
from typing import cast

import pytest

from your_package.farewell import farewell


def test_farewell_returns_goodbye_for_non_empty_name() -> None:
    """Covers REQ-FAREWELL-01, REQ-FAREWELL-04, and REQ-FAREWELL-05."""
    assert farewell("World") == "Goodbye, World!"

    signature = inspect.signature(farewell)
    assert signature.parameters["name"].annotation is str
    assert signature.return_annotation is str
    assert farewell.__doc__ is not None
    assert farewell.__doc__.count("Example:") == 1
    assert farewell.__doc__.count(">>>") == 1


def test_farewell_raises_value_error_on_empty_string() -> None:
    """Covers REQ-FAREWELL-02."""
    with pytest.raises(ValueError, match="name.*empty string"):
        farewell("")


@pytest.mark.parametrize("name", [None, 42, 3.14, ["x"], {"a": 1}, b"bytes"])
def test_farewell_raises_type_error_on_non_string(name: object) -> None:
    """Covers REQ-FAREWELL-03."""
    with pytest.raises(TypeError, match="name.*str.*got"):
        farewell(cast(str, name))
