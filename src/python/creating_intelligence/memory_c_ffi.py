"""
Copyright (c) 2026 Peter Overmann
 
SPDX-License-Identifier: MIT
 
This file is part of the "Creating Intelligence" project. It is licensed 
under the MIT License. You may obtain a copy of the License in the LICENSE 
file in the root directory of this repository.
 
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
"""

import ctypes
import os
import sys
import importlib.machinery
from pathlib import Path

def _candidate_paths():
    """Yield possible locations of the compiled C library, most preferred first."""
    # 1. Explicit override, e.g. MEMORY_LIB_PATH=/path/to/libmemory.so
    override = os.environ.get("MEMORY_LIB_PATH")
    if override:
        yield Path(override)

    # 2. Extension built by pip/setuptools, under any suffix this interpreter
    #    accepts (.cpython-312-x86_64-linux-gnu.so, .abi3.so, .cp312-win_amd64.pyd, ...)
    pkg_dir = Path(__file__).resolve().parent
    for suffix in importlib.machinery.EXTENSION_SUFFIXES:
        yield pkg_dir / f"libmemory{suffix}"

    # 3. Local development build from the C Makefile (<repo>/c/lib/)
    if sys.platform == "darwin":
        lib_name = "libmemory.dylib"
    elif sys.platform == "win32":
        lib_name = "libmemory.dll"
    else:
        lib_name = "libmemory.so"
    yield pkg_dir.parent.parent / "c" / "lib" / lib_name


def _load_library():
    tried = []
    for path in _candidate_paths():
        if not path.is_file():
            tried.append(f"  {path} (not found)")
            continue
        try:
            return ctypes.CDLL(str(path))
        except OSError as e:
            tried.append(f"  {path} ({e})")
    raise OSError("Could not load the C memory library. Tried:\n" + "\n".join(tried))


lib = _load_library()        
        
# Define the C 'Set' struct in Python.
class CSet(ctypes.Structure):
    _fields_ = [
        ("a", ctypes.POINTER(ctypes.c_int)),
        ("n", ctypes.c_int),
        ("p", ctypes.c_int)
    ]

# Define FFI signatures mapped from the C implementations.
lib.Memory_new.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
lib.Memory_new.restype = ctypes.c_void_p

lib.Memory_set_threshold.argtypes = [ctypes.c_void_p, ctypes.c_int]
lib.Memory_set_threshold.restype = None

lib.Memory_get_threshold.argtypes = [ctypes.c_void_p]
lib.Memory_get_threshold.restype = ctypes.c_int

lib.Memory_set_fraction.argtypes = [ctypes.c_void_p, ctypes.c_double]
lib.Memory_set_fraction.restype = None

lib.Memory_get_fraction.argtypes = [ctypes.c_void_p]
lib.Memory_get_fraction.restype = ctypes.c_double

lib.Memory_count.argtypes = [ctypes.c_void_p]
lib.Memory_count.restype = ctypes.c_int64

lib.Memory_free.argtypes = [ctypes.c_void_p]
lib.Memory_free.restype = None

lib.Memory_write.argtypes = [ctypes.c_void_p, ctypes.POINTER(CSet), ctypes.POINTER(CSet)]
lib.Memory_write.restype = None

lib.Memory_read.argtypes = [ctypes.c_void_p, ctypes.POINTER(CSet), ctypes.POINTER(CSet)]
lib.Memory_read.restype = ctypes.POINTER(CSet)

def Memory(config: dict) -> dict:
    NA, PA = config["A_parameters"] 
    NB, PB = config["B_parameters"] 
    
    # Construct the underlying C memory object.
    M = lib.Memory_new(NA, PA, NB, PB)
    
    # Push user-defined threshold scaling if provided.
    if config.get("threshold") is not None:
        scaled_threshold = round(config.get("threshold") * PA)
        lib.Memory_set_threshold(M, scaled_threshold) 
        
    # Push optional relative threshold (fraction of the query population).
    if config.get("fraction") is not None:
        lib.Memory_set_fraction(M, float(config.get("fraction")))

    # Retrieve final absolute threshold from C backend.
    T = lib.Memory_get_threshold(M) 

    # Retrieve fraction parameter from C backend
    fraction = lib.Memory_get_fraction(M) 

    def _make_cset(data_list, dimension):
        """Creates a CSet and holds the underlying array reference to prevent garbage collection."""
        length = len(data_list)
        shifted_data = [x - 1 for x in data_list]
        arr = (ctypes.c_int * length)(*shifted_data)
        cset = CSet(a=ctypes.cast(arr, ctypes.POINTER(ctypes.c_int)), n=dimension, p=length)
        return cset, arr
             
    def store(A, B=None):
        # Store auto-association A -> A in memory if B is omitted.
        if B is None:
            B = A 
            
        if len(A) > 0 and len(B) > 0: 
            cset_A, _ref_A = _make_cset(A, NA)
            cset_B, _ref_B = _make_cset(B, NB)
            lib.Memory_write(M, ctypes.byref(cset_A), ctypes.byref(cset_B)) 

    def retrieve(A):
        if len(A) == 0: 
            return []
            
        cset_A, _ref_A = _make_cset(A, NA)
        
        # Allocate space for retrieved values up to max dimension NB.
        Y_arr = (ctypes.c_int * NB)() 
        cset_Y = CSet(a=ctypes.cast(Y_arr, ctypes.POINTER(ctypes.c_int)), n=NB, p=0)
        
        # Memory_read returns a pointer to the populated result Set.
        res_ptr = lib.Memory_read(M, ctypes.byref(cset_A), ctypes.byref(cset_Y)) 
        
        if not res_ptr:
            return []
            
        res_set = res_ptr.contents
        return [res_set.a[i] + 1 for i in range(res_set.p)]
        
    def memorycount():
        return lib.Memory_count(M)

    def clear():
        lib.Memory_free(M) 

    return  {
        "A_parameters": (NA, PA),
        "B_parameters": (NB, PB),
        "T": T,
        "fraction": fraction,
        "store": store,
        "retrieve": retrieve,
        "clear": clear,
        "memorycount": memorycount,
        "backend": "c_ffi"
    }
