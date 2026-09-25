# Creating Intelligence

This project aims to build a computational theory of mind based on a new theory of
hyperdimensional computing (HDC), entirely departing from neural-network-based connectionist models which rely on matrix calculations and continuous weights.

In this model, the mind performs computations on sparse binary data. The fundamental
data structures are Sparse Distributed Representations (SDRs) for perceptual information 
and Sparse Holographic Representations (SHRs) for symbols. 

The centerpiece of this project is Topological Associative Memory &mdash; a 
newly discovered associative memory for sparse data, serving as the computational
kernel that models the brain's core algorithm. A software frontend
for modeling and simulating neural circuits and pathways complements the memory backend.

The methods introduced here lend themselves to binary in-memory and neuromorphic computating, opening a new route toward synthetic intelligence that does not rely on GPU acceleration.


### General Information

* Website: https://creatingintelligence.org
* Documentation: https://creatingintelligence.org/docs
* E-Book PDF: https://creatingintelligence.org/CreatingIntelligence.pdf
* Preprint: https://arxiv.org/abs/2606.31819
* Discussions: https://github.com/PeterOvermann/CreatingIntelligence/discussions
* Issue Tracker: https://github.com/PeterOvermann/CreatingIntelligence/issues

### Python Installation

```python
pip install creating-intelligence
```


### Development Setup

Building the package from source requires a C development environment to compile
the topological associative memory kernel as a Python extension.

On Unix, Linux, BSD, and macOS, run

```bash
src/python/setup.sh
```

On Windows, run

```bash
src/python/setup.bat
```

Build the standalone memory CLI and test programs from the zero-dependency Standard C source:

```bash
make -C src/c/
```

### Getting Started


```bash
python3 experiments/hello-world/hello-world.py 
```

See also: https://creatingintelligence.org/docs/quickstart.html

### Testing

Test the circuit package (and indirectly the memory backend):

```bash
python3 experiments/circuit-tests/run.py
```

Test the topological associative memory backend (storage capacity, retrieval accuracy, and I/O performance) with

```bash
python3 experiments/memory-tests/run.py
```

or as a stand-alone C binary with

```bash
src/c/build/memorytest
```

### Mathematica

A Mathematica version, functionally equivalent to the Python package, is available [here](src/mathematica).



---

### Copyright and License Information

Copyright © 2026 Peter Overmann. All rights reserved.

This repository contains two distinct categories of content, which are licensed separately:

* **The Software:** Licensed under the MIT License.

* **The Manuscript & Assets:** All Rights Reserved. These materials may not be reproduced, distributed, modified, translated, or commercialized without explicit, prior written permission from the author. 

See the full [LICENSE](LICENSE) file for details.

