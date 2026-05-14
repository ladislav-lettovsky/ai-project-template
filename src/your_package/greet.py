"""Greeting helpers."""


def greet(name: str) -> str:
    """Return a greeting for ``name``.

    Example:
        >>> greet("World")
        'Hello, World!'
    """
    if not isinstance(name, str):
        msg = f"name must be a str, got {type(name).__name__}"
        raise TypeError(msg)
    if name == "":
        msg = "name must not be an empty string"
        raise ValueError(msg)

    return f"Hello, {name}!"
