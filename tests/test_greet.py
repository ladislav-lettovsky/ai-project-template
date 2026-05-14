"""Tests for ``your_package.greet``."""

from __future__ import annotations

import inspect
from typing import cast

import pytest

from your_package.greet import greet


def test_greet_returns_hello_for_non_empty_name() -> None:
    """Covers REQ-GREET-01, REQ-GREET-04, and REQ-GREET-05."""
    assert greet("World") == "Hello, World!"

    signature = inspect.signature(greet)
    assert signature.parameters["name"].annotation is str
    assert signature.return_annotation is str
    assert greet.__doc__ is not None
    assert greet.__doc__.count("Example:") == 1
    assert greet.__doc__.count(">>>") == 1


def test_greet_raises_value_error_on_empty_string() -> None:
    """Covers REQ-GREET-02."""
    with pytest.raises(ValueError, match="name.*empty string"):
        greet("")


@pytest.mark.parametrize("name", [None, 42, 3.14, ["x"], {"a": 1}, b"bytes"])
def test_greet_raises_type_error_on_non_string(name: object) -> None:
    """Covers REQ-GREET-03."""
    with pytest.raises(TypeError, match="name.*str.*got"):
        greet(cast(str, name))
