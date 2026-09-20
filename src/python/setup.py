import os
import shutil
import sys
import platform
from setuptools import setup, Extension

if not shutil.which("dot"):
    sys.stderr.write(
        "\n"
        "=" * 60 + "\n"
        "WARNING: Graphviz ('dot') is required for advanced circuit schematics but was not found.\n"
        "The package will install normally, but visualization features will use a fallback layout.\n"
        "Please install Graphviz manually if needed:\n"
        "  - Windows: winget install Graphviz.Graphviz\n"
        "  - macOS: brew install graphviz\n"
        "  - Ubuntu/Debian: sudo apt-get install graphviz\n"
        "  - Fedora: sudo dnf install graphviz\n"
        "  - Arch: sudo pacman -S graphviz\n"
        "=" * 60 + "\n\n"
    )

c_source = os.path.join("..", "c", "memory.c")

# MSVC requires /O2 for optimization; GCC/Clang use -O3
compile_args = ["/O2"] if platform.system() == "Windows" else ["-O3"]

libmemory_ext = Extension(
    name="creating_intelligence.libmemory",
    sources=[c_source],
    extra_compile_args=compile_args
)

setup(
    ext_modules=[libmemory_ext]
)