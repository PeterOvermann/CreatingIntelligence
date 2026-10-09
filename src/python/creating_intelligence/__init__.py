
# __init__.py

import os
import importlib
import logging
import warnings

import sys

if sys.maxsize <= 2**32:
    raise ImportError("creating-intelligence requires 64-bit Python.")
    

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# MEMORY_BACKEND selects the backend explicitly ("c_ffi" or "python").
# If unset, the C backend is tried first, with the pure-Python one as fallback.
_requested = os.environ.get("MEMORY_BACKEND")
backend = (_requested or "c_ffi").lower()

try:
    _module = importlib.import_module(f".memory_{backend}", package=__name__)
except (ImportError, OSError, AttributeError) as e:
    if _requested is None and backend == "c_ffi":
        warnings.warn(
            f"C memory backend unavailable, using the Python backend. ({e})",
            RuntimeWarning,
            stacklevel=2,
        )
        backend = "python"
        _module = importlib.import_module(".memory_python", package=__name__)
    else:
        raise ImportError(f"Backend '{backend}' failed to load: {e}") from e

Memory = _module.Memory

# Expose Circuit to the package namespace
from .circuits import Circuit

logger.debug(f"[System] Initializing Memory using '{backend}' backend.")

__all__ = ['Circuit', 'Memory']