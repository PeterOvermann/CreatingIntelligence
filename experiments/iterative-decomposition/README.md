# Iterative decomposition

Experiments on decomposing a bundle of sparse holographic representations
(SHRs) against an item memory: how completely a bundle can be decomposed, and
which mechanisms limit decomposition.

| File | Content |
|---|---|
| `iterative-decomposition.py` | Complete decomposition, retrieval in an empty and a full memory, and shared elements |
| `iterative-decomposition.txt` | Output of `iterative-decomposition.py` |
| `iterative-decomposition-sparse.py`, `.txt` | Earlier experiments with a lightly loaded memory (archive) |
| `IterativeDecomposition.nb`, `.json`, `.pdf` | Mathematica example of the decomposition circuit |

## Setup

**Item memory.** An autoassociative memory with dimension $N$ and population
$P$, filled with random SHRs up to a given memory density, the fraction of
memory bits set. The script uses $N = 2000$, $P = 10$, 12 and 16, and a
density of 0.5. The pattern matching threshold $T$ follows from $N$ and $P$:
$T = 7$ for $P = 10$ and 12, $T = 8$ for $P = 16$.

**Memory density.** The number of items needed for a density is computed in
advance from the expected density after $L$ random autoassociative writes:

$$\rho(L) = 1 - \tfrac{2}{N}(1 - q_2)^L - \left(1 - \tfrac{2}{N}\right)(1 - q_3)^L,
\quad q_2 = \tfrac{P(P-1)}{N(N-1)}, \quad q_3 = \tfrac{P(P-1)(P-2)}{N(N-1)(N-2)}.$$

A memory bit belongs to an input pair $\{i, j\}$ and an output $o$. A random
item sets it if it contains $i$, $j$ and $o$; for the fraction $2/N$ of bits
with $o \in \{i, j\}$, it only needs to contain the pair. The formula
reproduces measured densities to four significant digits. A density of 0.5
corresponds to the nominal capacity for autoassociations,
$\ln 2 \, N(N-1)(N-2) / (P(P-1)(P-2))$ items, for example 7,678,987 items at
$N = 2000$, $P = 10$. The density is never measured during a run, because
counting memory bits is expensive. At density 0.5, the memory needs about
$N^3/16$ bytes, 0.5 GB for $N = 2000$.

**Bundles and queries.** A bundle is the union of $k$ randomly chosen stored
items. A query is decimated by the factor $D$, a random subset of
$\operatorname{round}(D \cdot |S|)$ elements of the bundle $S$, while the
bundle holds more than $P$ elements. Smaller bundles cannot contain a tie
between intact items and are queried as they are. The script uses $D = 0.7$:
stronger decimation fails already for small bundles in a loaded memory, and
$D = 0.9$ rarely breaks ties in larger bundles.

## Running

```
python3 iterative-decomposition.py
```

The script fills three item memories with 7.7, 4.2 and 1.6 million items
($P = 10$, 12 and 16), which takes most of the run time; the experiments
themselves take a few minutes. The reported compute time excludes filling.

The script uses fixed seeds and writes a checkpoint file,
`iterative-decomposition.cache.json`, so an interrupted run resumes where it
stopped. Every cache key contains a version number; entries from earlier
versions of the script are never reused, and deleting the cache recomputes
all results. The cache file is not part of the repository.

## Complete decomposition and its limits

`iterative-decomposition.py` uses an item memory with $N = 2000$, filled to
capacity, and runs three experiments.

### Experiment 1: complete decomposition

Each extracted item is removed from the bundle (sampling without replacement)
until all $k$ items are extracted, fewer than $T$ elements remain, or a budget
of 10 queries per item is exhausted. Removing an item also removes the
elements it shares with items still in the bundle (erosion). 500 bundles per
size.

| $k$ | first ($P=10$) | done ($P=10$) | q/item ($P=10$) | first ($P=12$) | done ($P=12$) | first ($P=16$) | done ($P=16$) |
|---|---|---|---|---|---|---|---|
| 2 | 1 | 1.000 | 1.27 | 1 | 1.000 | 1 | 1.000 |
| 4 | 2 | 0.996 | 1.73 | 1 | 0.998 | 1 | 1.000 |
| 6 | 3 | 0.988 | 2.61 | 2 | 0.994 | 1 | 1.000 |
| 8 | 6 | 0.930 | 4.22 | 3 | 0.980 | 2 | 1.000 |
| 10 | 13 | 0.710 | 7.56 | 6 | 0.956 | 3 | 1.000 |
| 12 | 24 | 0.312 | 13.41 | 12 | 0.880 | 5 | 0.998 |

*first*: median number of queries to extract the first item; *done*: fraction
of bundles completely decomposed within the budget; *q/item*: queries per
extracted item.

- **The first extraction is the bottleneck.** Its median latency stays at one
  or two queries up to 5 items for $P = 10$, up to 7 items for $P = 12$ and up
  to 8 items for $P = 16$, and then rises steeply. Once items have been
  removed, the remaining bundle is smaller and easier to query.
- **Given enough queries, larger bundles can still be decomposed.** With
  $P = 10$, 93 percent of 8-item bundles are completely decomposed, at 4.2
  queries per item, although the first extraction takes a median of 6
  queries. The budget of 10 queries per item is generous; with a tight time
  budget, the latency of the first extraction is the relevant limit.
- **Erosion is a minor effect.** Up to 8 items, fewer than 0.15 items per
  bundle are lost. Since bundles of at most $P$ elements are not decimated, an
  eroded item is lost only if fewer than $T$ of its elements remain.
- **A larger retained margin helps strongly at capacity.** $P = 16$ decomposes
  all bundles of up to 10 items, at fewer than 2 queries per item, without
  false extractions. $P = 10$ produces 198 false extractions at 12 items.

### Experiment 2: empty and full memory

The experiment evaluates the same bundles and queries against a memory
holding only the bundled items ("empty") and against the memory filled to
capacity ("full"), grouped by the number of elements retained of the favored
item ($m$) and of the runner-up ($r$). Bundles consist of pairwise disjoint
items; 2000 queries per bundle size.

Selected rows ($P = 10$, $T = 7$):

| $k$ | $m$ | $r$ | empty | full |
|---|---|---|---|---|
| 3 | 8 | 7 | 1.000 | 0.471 |
| 3 | 9 | 7 | 1.000 | 0.917 |
| 4 | 9 | 7 | 1.000 | 0.633 |
| 5 | 9 | 7 | 1.000 | 0.332 |
| 6 | 9 | 7 | 1.000 | 0.209 |
| 8 | 9 | 7 | 1.000 | 0.103 |
| 6 | 10 | 8 | 1.000 | 0.446 |

- **Without load, a unique favored item is always retrieved.** In the empty
  memory, every group succeeds in all queries.
- **With load, success depends on the query size and on the gap between
  favored item and runner-up.** For the same retained counts (9 and 7),
  success falls from 92 percent at $k = 3$ to 10 percent at $k = 8$. A
  narrower gap ($m = 8$, $r = 7$) fails more often than a wider one.
- **Mechanism.** In a loaded memory, query elements receive support not only
  from the pairs of their own item, but also from pairs written by other
  stored items, including pairs that link them to other query elements. This
  support grows with the size of the query. It reaches the query elements of
  all bundled items alike, but not the elements of the favored item that
  decimation removed. With a narrow gap, the runner-up therefore competes more
  strongly with the favored item, and retrieval more often returns an empty
  result. This is a property of autoassociative retrieval in a loaded
  memory.
- At $D = 0.7$ and $P = 10$, a query retains on average exactly $DP = 7 = T$
  elements per item. A unique favored item therefore always retains at least
  8 elements, so no group with $m = 7$ occurs.

### Experiment 3: shared elements

Single queries on bundles of random stored items and of pairwise disjoint
stored items, evaluated against both memories; 2000 queries per row.

| $k$ | items | shared elements | success given unique, empty | success given unique, full |
|---|---|---|---|---|
| 4 | random | 0.29 | 0.938 | 0.453 |
| 4 | disjoint | 0 | 1.000 | 0.441 |
| 8 | random | 1.41 | 0.866 | 0.137 |
| 8 | disjoint | 0 | 1.000 | 0.128 |

- **In an empty memory, shared elements are the only source of interference.**
  Disjoint bundles succeed whenever the favored item is unique; random bundles
  lose up to 13 percent of these queries, because an element shared by two
  items collects support from the pairs of both.
- **In a memory filled to capacity, support from the stored items
  dominates.** Disjoint and random bundles fail equally often, so the few
  shared elements no longer matter.
- **Ties alone would allow larger bundles.** A unique favored item exists in
  57 to 77 percent of all queries, nearly independent of the bundle size.

## Archive: lightly loaded memory

`iterative-decomposition-sparse.py` and its output
`iterative-decomposition-sparse.txt` document earlier experiments with a
lightly loaded item store (typically 10,000 items, density about 0.01
percent), mostly with $D = 0.8$. They cover complete decomposition with
different decimation rules and query strategies, the erosion model, sampling
with and without replacement, first-extraction latency for $N$ up to 8000, and
the shared-element control. In a nearly empty memory, there is little support
from other stored items, so considerably larger bundles can be decomposed than
at capacity, and the decomposable bundle size grows with the dimension. These
results describe a different regime and are kept for reference; the latency
CSV file the script writes when rerun is not included.

## Mathematica example

`IterativeDecomposition.nb` (with `.json` and `.pdf` exports) demonstrates the
decomposition circuit: a bundle is decimated, matched against the item store,
and the extracted item is removed by inhibitory feedback.

## Notes

- **Fixed decimation factor.** $D$ is kept constant throughout an extraction.
  This is an algorithmic choice, not necessarily the best strategy, and not a
  model of biological reality, where the strength of subsampling may vary
  from query to query.
- **Time budget.** The budget of 10 queries per item allows complete
  decomposition well beyond the bundle size at which the first extraction
  slows down. A computer can extend the budget at the cost of time.
