import os
import shutil
import sys
import platform
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext

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
            
    # Append a dummy initialization symbol to satisfy the MSVC linker on Windows
    with open(os.path.join(staged_c_dir, "memory.c"), "a") as f:
        f.write("\n\n/* Dummy Python init function to satisfy MSVC linker */\n")
        f.write("#if defined(_WIN32)\n__declspec(dllexport)\n#endif\n")
        f.write("void* PyInit_libmemory(void) { return 0; }\n")
        
    staged_files = True
    
    
compile_args = ["/O2"] if platform.system() == "Windows" else ["-O3"]

libmemory_ext = Extension(
    name="creating_intelligence.libmemory",
    sources=[os.path.join("c_build", "memory.c")],
    depends=[os.path.join("c_build", "memory.h")],
    extra_compile_args=compile_args
)

BUILD_TOOLS_ERROR = """
======================================================================

ERROR: Failed to build the memory backend.

This package requires a C/C++ compiler.

Please install the standard build tools for your operating system,
then retry the installation:

  - Ubuntu/Debian: sudo apt-get install build-essential python3-dev
  - Windows:       Install Visual Studio Build Tools (C++ workload)
  - macOS:         xcode-select --install
  - Fedora:        sudo dnf groupinstall "Development Tools" && sudo dnf install python3-devel
  - Arch Linux:    sudo pacman -S base-devel python
  
======================================================================
"""

class StrictBuildExt(build_ext):
    def run(self):
        try:
            super().run()
        except Exception as e:
            sys.stderr.write(f"\n{e}\n{BUILD_TOOLS_ERROR}")
            sys.exit(1)

    def build_extension(self, ext):
        try:
            super().build_extension(ext)
        except Exception as e:
            sys.stderr.write(f"\n{e}\n{BUILD_TOOLS_ERROR}")
            sys.exit(1)

try:
    setup(
        ext_modules=[libmemory_ext],
        cmdclass={"build_ext": StrictBuildExt},
    )
finally:
    if staged_files and os.path.exists(staged_c_dir):
        shutil.rmtree(staged_c_dir)
    