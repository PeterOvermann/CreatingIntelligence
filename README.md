# Creating Intelligence

This research initiative aims to build a computational theory of mind based on a
new theory of hyperdimensional computing (HDC), entirely departing from
conventional neural networks, continuous weights, and matrix calculations.

In this model, the mind performs computations on sparse binary data. The
fundamental data structures are Sparse Distributed Representations (SDRs) for
perceptual information and Sparse Holographic Representations (SHRs) for symbols.

The centerpiece of this project is Topological Associative Memory &mdash; a
neural memory for sparse binary data with huge capacity and constant retrieval
time. Memory retrieval functions on the basis of exact subset matching, which we
propose to be the brain's core algorithm.

This repository includes a software framework (the system layer) for modeling and
simulating neural circuits based on the topological memory kernel.

The methods introduced here lend themselves to binary in-memory and neuromorphic
computation, opening a new route toward synthetic intelligence that does not rely
on GPU acceleration.

### General Information

* Website: https://creatingintelligence.org
* Documentation: https://creatingintelligence.org/docs
* Context for LLMs and AI agents: https://creatingintelligence.org/llms.txt
* Release information: https://pypi.org/project/creating-intelligence/
* Manuscript: https://raw.githubusercontent.com/PeterOvermann/Writings/main/CreatingIntelligence.pdf
* Preprint: https://arxiv.org/abs/2606.31819


Questions and ideas are welcome in [Discussions](https://github.com/PeterOvermann/CreatingIntelligence/discussions).
Please report bugs at the [Issue Tracker](https://github.com/PeterOvermann/CreatingIntelligence/issues).

### Python Installation

```bash
pip install creating-intelligence
```

### Getting Started


```bash
python3 experiments/hello-world/hello-world.py 
```

See also: https://creatingintelligence.org/docs/quickstart.html



### Development Setup

Building the Python package from source requires a development environment to compile the topological associative memory kernel as a C extension.

Unix, Linux, BSD, and macOS:

```bash
src/python/setup.sh
```

Windows:

```bash
src/python/setup.bat
```

To build the package on Linux without installing it, run

```bash
src/python/dev_build.sh
export PYTHONPATH="$PWD/src/python/build/local"
```


Build the standalone memory (command line interface and test program) from the zero-dependency C source:

```bash
make -C src/c/
```

### Testing

Test the circuit package (and indirectly the memory backend):

```bash
python3 experiments/circuit-tests/run.py
```

Test the memory backend (storage capacity, retrieval accuracy, and I/O performance):

```bash
python3 experiments/memory-tests/run.py
```

Test the stand-alone C memory backend:

```bash
src/c/build/memorytest
```

### Mathematica

A Mathematica implementation, functionally equivalent to the Python package, is available [here](src/mathematica).



---

### Copyright and License Information

Copyright © 2026 Peter Overmann. All rights reserved.

This repository contains two distinct categories of content, which are licensed separately:

* **The Software:** Licensed under the MIT License.

* **The Manuscript & Assets:** All Rights Reserved. These materials may not be reproduced, distributed, modified, translated, or commercialized without explicit, prior written permission from the author. 

See the full [License](License) file for details.

