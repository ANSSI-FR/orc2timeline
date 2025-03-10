"""Main module."""

from .cli import entrypoint
from .core import process
from .info import __author__, __copyright__, __description__, __email__, __version__

__all__ = [
    "__author__",
    "__copyright__",
    "__description__",
    "__email__",
    "__version__",
    "entrypoint",
    "process",
]
