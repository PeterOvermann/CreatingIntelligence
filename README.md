# About the *Creating Intelligence* Project

Our goal is to build a Computational Theory of Mind, based on a 
new approach to Hyperdimensional Computing. It proposes an alternative to classical
computationalist models and to neural-network-based connectionist models of the mind.

In this theory, the mind performs computations on sparse binary data. The fundamental
data structures are Sparse Distributed Representations (SDRs) for perceptual information 
and Sparse Holographic Representations (SHRs) for symbols. 

The centerpiece of this project is the Topological Associative Memory &mdash; a 
newly discovered associative memory for sparse data, serving as the computational
kernel that models the brain's core algorithm. A software frontend
for modeling and simulating neural circuits and pathways complements the memory backend.

The methods introduced here lend themselves to binary in-memory computation, opening a
new route toward synthetic intelligence that does not rely on GPU acceleration.


### General Information

* Website: https://creatingintelligence.org
* Download PDF: https://creatingintelligence.org/CreatingIntelligence.pdf
* Preprint: https://arxiv.org/abs/2606.31819
* Discussions: https://github.com/PeterOvermann/CreatingIntelligence/discussions
* Issue Tracker: https://github.com/PeterOvermann/CreatingIntelligence/issues


### Build Instructions

On Unix, Linux, BSD, and macOS, run

```
src/python/setup.sh
```

This will create a Python virtual environment `~/.ci` in your home directory and build the *creating_intelligence* package.
It includes a high-performance memory backend written in Standard C, and an alternative native Python version.

To build stand-alone zero-dependency versions of the Standard C memory kernel (a command line interface and test program), run

```
make -C src/c/
```

### Getting Started

Learn how to set up neural architectures via the JSON dataflow description language: [GettingStarted.pdf](experiments/getting-started/GettingStarted.pdf) 

Run a first example:

```
python3 experiments/hello-world/hello-world.py 
```



### Testing

To test the circuit package (and indirectly the memory backend), run

```
python3 experiments/circuit-tests/run.py
```

Test the stand-alone memory kernel (storage capacity, retrieval accuracy, and I/O performance) with

```
python3 experiments/memory-tests/run.py
```

or as a stand-alone C binary with

```
bin/memorytest
```




---

### Copyright and License Information

Copyright © 2026 Peter Overmann. All rights reserved.

This repository contains two distinct categories of content, which are licensed separately:

* **The Software:** Licensed under the MIT License.

* **The Manuscript & Assets:** All Rights Reserved. These materials may not be reproduced, distributed, modified, translated, or commercialized without explicit, prior written permission from the author. 

See the full [LICENSE](LICENSE) file for details.

