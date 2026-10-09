
SOURCE CODE

# Python



## circuits.py

See also: https://creatingintelligence.org/index.html#circuits

*insert python/creating_intelligence/circuits.py*


## memory_python.py 

This reference implementation of the Topological Associative Memory algorithm illustrates the mechanics of the memory core and its programming interface, serving as a baseline for experimental and derived algorithms.

See also: https://creatingintelligence.org/index.html#the-core-algorithm

*insert python/creating_intelligence/memory_python.py*


## memory_c_ffi.py 

By default, the package uses this C extension as the memory backend, which is an order of magnitude faster than
the reference implementation.


*insert python/creating_intelligence/memory_c_ffi.py*

## __init__.py 


*insert python/creating_intelligence/__init__.py*

## Local build without pip

To assemble a working package from [this documentation](../llms-docs.txt) alone (for instance in a sandbox without network access), save each code block under its section header, ignoring trailing whitespace in the headers:

    creating_intelligence/__init__.py
    creating_intelligence/circuits.py
    creating_intelligence/memory_python.py
    creating_intelligence/memory_c_ffi.py
    c_build/memory.h          (from the C section)
    c_build/memory.c          (from the C section)

Then compile the C backend into the package directory:

```bash
gcc -O3 -shared -fPIC c_build/memory.c -o creating_intelligence/libmemory.so -lm
```

Run scripts from the directory containing `creating_intelligence/`. If compilation is not possible, the package falls back to the pure-Python backend automatically; set `MEMORY_BACKEND=python` to select it explicitly. 

Requirements: 64-bit Python ≥ 3.9 with numpy, scipy, networkx and matplotlib.

