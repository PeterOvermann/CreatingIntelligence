import os
import importlib
from dotenv import load_dotenv

# Calculate absolute path to the repo root relative to this file
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
env_path = os.path.join(repo_root, ".env")

# Load the specific .env file
load_dotenv(dotenv_path=env_path)

backend = os.environ.get("MEMORY_BACKEND", "c_ffi").lower()
module_name = f".memory_{backend}"

try:
    module = importlib.import_module(module_name, package=__name__)
    Memory = module.Memory
except (ImportError, OSError) as e:
    raise ValueError(f"Backend '{backend}' failed to load: {e}")
    
# Expose Circuit to the package namespace
from .circuits import Circuit

print(f"[System] Initializing Memory using '{backend}' backend.")