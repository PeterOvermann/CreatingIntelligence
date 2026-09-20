import os
import importlib
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
# Optional: Add a NullHandler to prevent warnings if the parent app doesn't configure logging
logger.addHandler(logging.NullHandler())

# Calculate absolute path to the repo root relative to this file
current_dir = os.path.dirname(os.path.abspath(__file__))

backend = os.environ.get("MEMORY_BACKEND", "c_ffi").lower()
module_name = f".memory_{backend}"

try:
    module = importlib.import_module(module_name, package=__name__)
    Memory = module.Memory
except (ImportError, OSError) as e:
    raise ValueError(f"Backend '{backend}' failed to load: {e}")
    
# Expose Circuit to the package namespace
from .circuits import Circuit

logger.debug(f"[System] Initializing Memory using '{backend}' backend.")

__all__ = ['Circuit', 'Memory']
