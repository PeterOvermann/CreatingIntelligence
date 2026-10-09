import os
import shutil
import sys
import platform
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.bdist_wheel import bdist_wheel

import struct

if struct.calcsize("P") * 8 != 64:
    sys.exit(
        "ERROR: creating-intelligence requires a 64-bit Python interpreter.\n"
        f"This Python is {struct.calcsize('P') * 8}-bit ({sys.executable})."
    )
    
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(current_dir)
repo_c_dir = os.path.join(repo_root, "c")
staged_c_dir = os.path.join(current_dir, "c_build")

repo_c_source = os.path.join(repo_c_dir, "memory.c")

# Stage C sources from ../c only in a genuine repo checkout. When building
# from an unpacked sdist, c_build/ is already shipped and must not be touched.
def _inside_git_checkout(start):
    """True if any parent folder of `start` contains .git (a folder or a file)."""
    d = start
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return True
        parent = os.path.dirname(d)
        if parent == d:
            return False
        d = parent

in_repo_checkout = os.path.isfile(repo_c_source) and _inside_git_checkout(current_dir)

staged_files = False

if in_repo_checkout:
    os.makedirs(staged_c_dir, exist_ok=True)
    for filename in ["memory.c", "memory.h"]:
        src_file = os.path.join(repo_c_dir, filename)
        if os.path.exists(src_file):
            shutil.copy2(src_file, os.path.join(staged_c_dir, filename))

    # Append a dummy initialization symbol to satisfy the MSVC linker on Windows
    with open(os.path.join(staged_c_dir, "memory.c"), "a") as f:
        f.write("\n\n/* Dummy Python init function to satisfy MSVC linker */\n")
        f.write("#if defined(_WIN32)\n__declspec(dllexport)\n#endif\n")
        f.write("void* PyInit_libmemory(void) { return 0; }\n")

    staged_files = True
    
if not os.path.isfile(os.path.join(staged_c_dir, "memory.c")):
    sys.exit(
        "ERROR: c_build/memory.c not found. Expected either a repo checkout "
        "with ../c/memory.c or an sdist that ships c_build/."
    )        
    
compile_args = ["/O2"] if platform.system() == "Windows" else ["-O3"]

libmemory_ext = Extension(
    name="creating_intelligence.libmemory",
    sources=[os.path.join("c_build", "memory.c")],
    depends=[os.path.join("c_build", "memory.h")],
    extra_compile_args=compile_args,
    export_symbols=[
        "Memory_new",
        "Memory_set_threshold",
        "Memory_get_threshold",
        "Memory_set_fraction",
        "Memory_get_fraction",
        "Memory_count",
        "Memory_free",
        "Memory_write",
        "Memory_read"
    ]
)

BUILD_TOOLS_WARNING = """
======================================================================

WARNING: Failed to build the C memory backend.

creating-intelligence will still work, using the slower pure-Python
backend. To get the fast C backend, install the build tools for your
operating system:

  - Ubuntu/Debian: sudo apt-get install build-essential python3-dev
  - Windows:       Install Visual Studio Build Tools (C++ workload)
  - macOS:         xcode-select --install
  - Fedora:        sudo dnf groupinstall "Development Tools" && sudo dnf install python3-devel
  - Arch Linux:    sudo pacman -S base-devel python

then reinstall without pip's cached wheel:

  pip install --force-reinstall --no-cache-dir creating-intelligence

======================================================================
"""

class OptionalBuildExt(build_ext):
    """Build the C backend if possible, but never fail the install over it."""

    def get_ext_filename(self, ext_name):
        # The library is loaded via ctypes, not imported, so give it a name that
        # does not depend on the Python version: libmemory.so / libmemory.pyd.
        # Both suffixes are in EXTENSION_SUFFIXES on every CPython version.
        suffix = ".pyd" if sys.platform == "win32" else ".so"
        return os.path.join(*ext_name.split(".")) + suffix

    def run(self):
        try:
            super().run()
        except Exception as e:
            sys.stderr.write(f"\n{e}\n{BUILD_TOOLS_WARNING}")

    def build_extension(self, ext):
        try:
            super().build_extension(ext)
        except Exception as e:
            sys.stderr.write(f"\n{e}\n{BUILD_TOOLS_WARNING}")
            
            
class PlatformWheel(bdist_wheel):
    """Tag wheels py3-none-<platform>: one wheel per OS/CPU, any Python 3."""

    def get_tag(self):
        _, _, plat = super().get_tag()
        return "py3", "none", plat


try:
    setup(
        ext_modules=[libmemory_ext],
        cmdclass={"build_ext": OptionalBuildExt, "bdist_wheel": PlatformWheel},
    )
finally:
    if staged_files and os.path.exists(staged_c_dir):
        shutil.rmtree(staged_c_dir)
        