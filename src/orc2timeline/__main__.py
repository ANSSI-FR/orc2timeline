"""Entrypoint with `python -m cookiepython`."""

import sys

from .cli import entrypoint

if __name__ == "__main__":
    # Patch pickle for anyio.to_process.run_sync
    # ImportError: attempted relative import with no known parent package
    sys.modules["__main__"] = entrypoint  # type: ignore[assignment]  # pragma: no cover
    entrypoint()  # pragma: no cover
