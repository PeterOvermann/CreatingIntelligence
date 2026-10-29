# Usable bundle size

`usable-bundle-size.py` determines how many items a bundle of sparse
holographic representations (SHRs) can hold, measured by how quickly the first
item can be extracted from it.

| File | Content |
|---|---|
| `usable-bundle-size.py` | Experiment script |
| `usable-bundle-size-0.0188365.txt`, `.csv` | Run 1: moderately loaded memory |
| `usable-bundle-size-0.5.txt`, `.csv` | Run 2: memory filled to capacity |

## Method

1. An autoassociative item memory with dimension $N$ and population $P$ is
   filled with random SHRs up to a fixed memory density, the fraction of
   memory bits set.
2. A bundle is the union of $k$ randomly chosen stored items.
3. The bundle is queried repeatedly. Each query is decimated by the factor $D$:
   a random subset of $\operatorname{round}(D \cdot |S|)$ elements of the
   bundle $S$. Bundles of no more than $P$ elements are not decimated, since
   they cannot contain a tie between intact items.
4. The latency is the number of queries until memory retrieval returns one of
   the bundled items. A result that is not a bundled item counts as a false
   extraction.

Bundles without an extraction within $Q$ queries are *censored*: their
latency is only known to exceed $Q$. Since some large bundles almost never
yield an item, the mean latency is not well defined; the experiment reports
the median and the fraction of censored bundles.

**Usable bundle size:** the largest $k$ such that the median latency is at
most two queries, for every bundle size up to $k$.

## Memory density

The number of items needed for a given density is computed in advance from
the expected density after $L$ random autoassociative writes:

$$\rho(L) = 1 - \tfrac{2}{N}(1 - q_2)^L - \left(1 - \tfrac{2}{N}\right)(1 - q_3)^L,
\quad q_2 = \tfrac{P(P-1)}{N(N-1)}, \quad q_3 = \tfrac{P(P-1)(P-2)}{N(N-1)(N-2)}.$$

A memory bit belongs to an input pair $\{i, j\}$ and an output $o$. A random
item sets it if it contains $i$, $j$ and $o$; for the fraction $2/N$ of bits
with $o \in \{i, j\}$, it only needs to contain the pair. The formula
reproduces measured densities to four significant digits, and at density 0.5
it agrees with the nominal capacity for autoassociations,
$\ln 2 \, N(N-1)(N-2) / (P(P-1)(P-2))$ items, to within 0.4 percent. The
density is not measured during a run, because counting memory bits is
expensive.

At a density of 0.5, nearly every input pair of the memory is in use, so the
memory needs about $N^3/16$ bytes: 0.5 GB for $N = 2000$, 4 GB for
$N = 4000$.

## Configuration

| Parameter | Run 1 | Run 2 |
|---|---|---|
| Memory density | 0.0188365 (200,000 items at $N = 2000$, $P = 10$) | 0.5 (capacity) |
| Dimensions $N$ | 1000, 1500, 2000, 3000, 4000 | 1000, 2000, 4000 |
| Populations $P$ | 9 to 16 | 10, 12, 14, 16 |
| Stored items | 5,222 to 2,349,482 | 205,081 to 61,522,459 |

Both runs use:

| Parameter | Value |
|---|---|
| Decimation factor $D$ | 0.7 |
| Bundles per size | 1000 |
| Bundle sizes | 1 to 40 |
| Cap $Q$ | 8 queries |
| Early stop | a series ends at the first bundle size whose median exceeds 4 |
| Seed | 1 |

$D = 0.7$ was chosen from preliminary tests at $N = 2000$, $P = 10$:
stronger decimation fails already for small bundles in a loaded memory, and
$D = 0.9$ rarely breaks ties in larger bundles.

The early stop and the small cap keep the runs short: the usable bundle size
only depends on bundle sizes up to the first median above two, and a median
above four is detected once more than half of the bundles fail within four
queries.

## Running

```
python3 usable-bundle-size.py
```

The configuration at the end of the script is that of run 2. To reproduce
run 1, set `dimensions`, `populations` and `density` to the values in the
table above.

Most of the run time is spent filling the item memories for $N = 4000$; the
latency measurements are short because of the early stop. The memory for
$N = 4000$ needs about 4 GB, plus up to 1.2 GB for the list of stored items.

Results are checkpointed in `usable-bundle-size.cache.json`, so an interrupted
run resumes where it stopped. Every cache key contains a version number;
entries from earlier versions of the script are never reused, and deleting the
cache recomputes all results. The cache file is not part of the repository.

## Output

Output files are named after the density, so runs do not overwrite each
other.

- The report (`.txt`) lists, per item memory, the median latency and the
  censored fraction for every bundle size, the number of false extractions,
  and summary tables of the usable bundle size.
- The CSV file has one row per configuration and bundle size, with columns
  `N, P, T, D, k, items, median, censored, false` and the latency distribution
  `P(L<=1)`, `P(L<=2)`, `P(L<=4)`, `P(L<=8)`. Rows after the early stop are
  omitted.

## Results

### Run 2: memory filled to capacity

| $N$ | $P=10$ ($T=7$) | $P=12$ ($T=7$) | $P=14$ ($T=8$) | $P=16$ ($T=8$) |
|---|---|---|---|---|
| 1000 | 5 | 6 | 7 | 8 |
| 2000 | 5 | 7 | 8 | 9 |
| 4000 | 4 | 7 | 8 | 10 |

### Run 1: density 0.0188365

The pattern matching threshold $T$ is given in parentheses.

| $N$ | $P=9$ | $P=10$ | $P=11$ | $P=12$ | $P=13$ | $P=14$ | $P=15$ | $P=16$ |
|---|---|---|---|---|---|---|---|---|
| 1000 | 6 (7) | 7 (7) | 8 (7) | 8 (7) | 7 (8) | 8 (8) | 8 (8) | 9 (8) |
| 1500 | 6 (7) | 8 (7) | 8 (7) | 9 (7) | 8 (8) | 9 (8) | 9 (8) | 10 (8) |
| 2000 | 6 (7) | 8 (7) | 9 (7) | 10 (7) | 9 (8) | 9 (8) | 10 (8) | 11 (8) |
| 3000 | 7 (7) | 8 (7) | 9 (7) | 11 (7) | 11 (7) | 10 (8) | 11 (8) | 12 (8) |
| 4000 | 7 (7) | 8 (7) | 10 (7) | 11 (7) | 12 (7) | 11 (8) | 11 (8) | 12 (8) |

### Interpretation

- **The usable bundle size is small and nearly independent of the
  dimension.** At a given memory density and threshold, it changes by one to
  three items between $N = 1000$ and $N = 4000$.
- **It is governed by the retained margin $DP - T$,** the expected number of
  elements a decimated query retains of an intact item beyond the threshold.
  Where $T$ steps from 7 to 8, a larger population can do worse: in run 1,
  $P = 13$ with $T = 8$ falls below $P = 12$ with $T = 7$, while $P = 13$ with
  $T = 7$ (at $N \ge 3000$) matches or exceeds it.
- **Memory load reduces the usable bundle size moderately.** From run 1 to
  run 2, $P = 10$ drops from 7 to 8 items to 4 to 5, and $P = 16$ from 9 to 12
  items to 8 to 10. A larger margin makes extraction more robust against load.
- **False extractions are rare:** 18 in run 1 and 297 in run 2. Populations
  with a large margin are least affected: in run 2, $P = 14$ and $P = 16$ at
  $N \ge 2000$ had at most 4. False extractions occur when a decimated query
  happens to contain enough elements of an unrelated stored item.

## Notes

- **Memory load.** In a loaded memory, query elements receive support not
  only from the pairs of their own item, but also from pairs written by other
  stored items, including pairs that link them to other query elements. This
  support grows with the size of the query and reaches the query elements of
  all bundled items alike, but not the elements of the favored item that
  decimation removed. Competing items therefore interfere more strongly in
  larger bundles. This is a property of autoassociative retrieval in a loaded
  memory.
- **Fixed decimation factor.** $D$ is kept constant for all queries. This is
  an algorithmic choice, not necessarily the best strategy.
- **Time budget.** The usable bundle size is defined for a budget of two
  queries. With a larger budget, larger bundles can be decomposed, at the cost
  of time.
