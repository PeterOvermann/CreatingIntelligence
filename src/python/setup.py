import os
import shutil
import sys
import platform
from setuptools import setup, Extension

if not os.environ.get("_CI_GRAPHVIZ_WARN_SHOWN"):
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
    os.environ["_CI_GRAPHVIZ_WARN_SHOWN"] = "1"

current_dir = os.path.dirname(os.path.abspath(__file__))
repo_c_dir = os.path.abspath(os.path.join(current_dir, "..", "c"))
staged_c_dir = os.path.join(current_dir, "c_build")

repo_c_source = os.path.join(repo_c_dir, "memory.c")
staged_files = False

if os.path.exists(repo_c_source):
    os.makedirs(staged_c_dir, exist_ok=True)
    for filename in ["memory.c", "memory.h"]:
        src_file = os.path.join(repo_c_dir, filename)
        if os.path.exists(src_file):
            shutil.copy2(src_file, os.path.join(staged_c_dir, filename))
    staged_files = True

compile_args = ["/O2"] if platform.system() == "Windows" else ["-O3"]

libmemory_ext = Extension(
    name="creating_intelligence.libmemory",
    sources=[os.path.join("c_build", "memory.c")],
    depends=[os.path.join("c_build", "memory.h")],
    extra_compile_args=compile_args
)

try:
    setup(
        ext_modules=[libmemory_ext]
    )
finally:
    if staged_files and os.path.exists(staged_c_dir):
        shutil.rmtree(staged_c_dir)