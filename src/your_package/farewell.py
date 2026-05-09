"""Farewell helpers."""


def farewell(name: str) -> str:
    """Return a farewell for ``name``.

    Example:
        >>> farewell("World")
        'Goodbye, World!'
    """
    if not isinstance(name, str):
        msg = f"name must be a str, got {type(name).__name__}"
        raise TypeError(msg)
    if name == "":
        msg = "name must not be an empty string"
        raise ValueError(msg)

    return f"Goodbye, {name}!"
