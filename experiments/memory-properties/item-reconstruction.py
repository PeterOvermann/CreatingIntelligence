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

"""
Item reconstruction: reading stored autoassociations back from memory bits.

An autoassociative memory (dimension N, population P) is filled with random
items up to a given fraction of its nominal capacity

  C = ln 2 N(N-1)(N-2) / (P(P-1)(P-2)).

A memory bit belongs to an input pair {i, j} and an output k. Storing an item
A sets the bit for every pair {i, j} in A and every k in A, so a stored item
is a clique of the 3-uniform hypergraph of triples {i, j, k} whose bits are
set. At nominal capacity, half of the bits are set, and a random memory of the
same density contains essentially no P-cliques (expected number
binom(N, P) 2^-binom(P, 3)). The stored items can therefore be reconstructed
from the bits alone, without access to the item list.

Search: all P-cliques through a seed triple {a, j, k} are enumerated by
backtracking. The candidate set is the intersection of the memory sets of all
pairs in the current clique; it shrinks by about a factor 2 per pair, so
spurious branches die out after a few steps. To reconstruct every item that
contains element a, the search is seeded with the set triples {a, j, k} not yet
explained by an item found earlier ("peeling"). The result is compared with
the item list.

Reconstruction is exact when chance P-cliques are rare. Where they are not
(small N, or a memory loaded beyond nominal capacity), false items appear, and
peeling may also miss items whose triples are all covered by false cliques;
setting "peel" to False seeds from every set triple and avoids such misses.

Baseline: the same search, from randomly sampled set triples through the
same element, on a random memory with the same symmetry (each unordered triple
set with probability 1/2, all pair bits set) finds no P-cliques. Peeling is
not used here, since nothing is found that could explain a triple.

The bit table is built with numpy using the storage rule of Memory["store"],
so the search can read the bits directly; the framework has no API for that.
A consistency check compares the number of bits set with Memory["memorycount"]
on a small memory. The table needs about N^3/2 bytes: 0.5 GB for N = 1000.

Results are printed and saved to item-reconstruction.txt.
"""

import os
import math
import time
import platform
import numpy as np
from itertools import combinations
from creating_intelligence import Memory


class Report:
    """Prints lines and collects them for the matching .txt output file."""

    def __init__(self):
        self.lines = []

    def __call__(self, line=""):
        print(line, flush=True)
        self.lines.append(line)

    def save(self):
        base = os.path.splitext(os.path.abspath(__file__))[0]
        with open(base + ".txt", "w") as f:
            f.write("\n".join(self.lines) + "\n")


def nominal_capacity(n, p):
    return round(math.log(2) * n * (n - 1) * (n - 2) / (p * (p - 1) * (p - 2)))


class BitTable:
    """Memory bits as a boolean array: one row per input pair {i, j}
    (1 <= i < j <= n), one column per output element k (column k - 1)."""

    def __init__(self, n):
        self.n = n
        self.bits = np.zeros((n * (n - 1) // 2, n), dtype=bool)

    def row(self, i, j):
        """Row index of the pair {i, j}; works on scalars and arrays."""
        i, j = np.minimum(i, j), np.maximum(i, j)
        i0 = i - 1
        return i0 * self.n - i0 * (i0 + 1) // 2 + (j - i - 1)

    def memory_set(self, i, j):
        return self.bits[self.row(i, j)]

    def store(self, items, chunk=20000):
        """Autoassociative writes, as in Memory["store"]: for every pair
        {i, j} of an item, set the bits of all elements of the item."""
        p = items.shape[1]
        pairs = np.array(list(combinations(range(p), 2)))
        flat = self.bits.reshape(-1)
        for c in range(0, len(items), chunk):
            x = items[c:c + chunk]
            rows = self.row(x[:, pairs[:, 0]], x[:, pairs[:, 1]])  # (m, P(P-1)/2)
            idx = rows[:, :, None] * self.n + (x[:, None, :] - 1)  # (m, pairs, P)
            flat[idx.reshape(-1)] = True

    def count(self):
        return int(self.bits.sum())

    def fill_random_symmetric(self, density, rng):
        """Random memory with the symmetry of an autoassociative one: each
        unordered triple {i, j, k} is set with the given probability, in all
        three orientations, and all pair bits (i, j) -> i, j are set."""
        n = self.n
        self.bits[:] = False
        for a in range(1, n - 1):
            for b in range(a + 1, n):
                c = np.arange(b + 1, n + 1)
                v = rng.random(c.size) < density
                self.bits[self.row(a, b), c - 1] = v
                self.bits[self.row(a, c), b - 1] = v
                self.bits[self.row(b, c), a - 1] = v
        for a in range(1, n):
            j = np.arange(a + 1, n + 1)
            r = self.row(a, j)
            self.bits[r, a - 1] = True
            self.bits[r, j - 1] = True


def cliques_through(table, seed, p):
    """All p-cliques (as sorted tuples) that contain the seed triple."""
    a, j, k = seed
    found = []
    cand = table.memory_set(a, j) & table.memory_set(a, k) & table.memory_set(j, k)
    cand[[a - 1, j - 1, k - 1]] = False

    def extend(clique, cand, last):
        if len(clique) == p:
            found.append(tuple(sorted(clique)))
            return
        elems = np.nonzero(cand)[0] + 1
        elems = elems[elems > last]           # each clique is enumerated once
        if len(clique) + len(elems) < p:
            return
        for x in elems:
            nxt = cand.copy()
            for q in clique:
                nxt &= table.memory_set(q, x)
            nxt[x - 1] = False
            extend(clique + [int(x)], nxt, x)

    extend([a, j, k], cand, 0)
    return found


def reconstruct(table, a, p, peel=True):
    """Every p-clique containing element a. With peeling, only the set triples
    {a, j, k} that no clique found so far explains are used as seeds; without,
    every set triple through a is a seed. Peeling is much faster, but can miss
    an item whose triples are all covered by false cliques."""
    n = table.n
    explained = np.zeros((n + 1, n + 1), dtype=bool)
    found, seeds = set(), 0
    for j in range(1, n + 1):
        if j == a:
            continue
        for k in np.nonzero(table.memory_set(a, j))[0] + 1:
            if k <= j or k == a or (peel and explained[j, k]):
                continue
            seeds += 1
            for c in cliques_through(table, (a, j, int(k)), p):
                if c in found:
                    continue
                found.add(c)
                rest = [x for x in c if x != a]
                explained[np.ix_(rest, rest)] = True
    return found, seeds


def random_items(rng, n, p, count):
    """count random p-subsets of {1..n}, sorted, by rejection of duplicates."""
    out = np.empty((0, p), dtype=np.int64)
    while len(out) < count:
        x = np.sort(rng.integers(1, n + 1, (int((count - len(out)) * 1.2) + 10, p)),
                    axis=1)
        out = np.vstack([out, x[(np.diff(x, axis=1) > 0).all(axis=1)]])
    return out[:count]


def consistency_check(report, n=60, p=5, items=300, seed=1):
    rng = np.random.default_rng(seed)
    x = random_items(rng, n, p, items)
    table = BitTable(n)
    table.store(x)
    mem = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
    for item in x:
        mem["store"](item.tolist())
    ok = table.count() == int(mem["memorycount"]())
    report(f"Consistency check (N={n}, P={p}, {items} items): bit table "
           f"{table.count()} bits, Memory {int(mem['memorycount']())} bits "
           f"-> {'ok' if ok else 'MISMATCH'}")
    if not ok:
        raise SystemExit("Bit table does not match the framework's storage rule.")


def run(config):
    report = Report()
    n, p = config["N"], config["P"]
    cap = nominal_capacity(n, p)
    count = round(config["load"] * cap)
    report(f"Generated with {os.path.basename(__file__)}")
    report(f"System: {platform.platform()}, {platform.machine()}, "
           f"Python {platform.python_version()}, numpy {np.__version__}")
    report(f"Backend: {Memory.__module__}")
    report(f"Date: {time.strftime('%Y-%m-%d')}")
    report()
    consistency_check(report)
    report()

    t0 = time.time()
    rng = np.random.default_rng(config["seed"])
    items = random_items(rng, n, p, count)
    table = BitTable(n)
    table.store(items)
    off_diag = table.count() - 2 * len(table.bits)   # all pair bits are set
    density = off_diag / (len(table.bits) * (n - 2))
    report(f"N={n}, P={p}, nominal capacity C={cap:,}, stored items: {count:,} "
           f"({config['load']:g} C)")
    report(f"Density of off-diagonal bits: {density:.4f}   ({time.time() - t0:.0f} s)")
    expected = math.comb(n, p) * 2.0 ** -math.comb(p, 3)
    report(f"Expected chance {p}-cliques in a random memory of density 1/2: "
           f"{expected:.1e}")
    report()

    for a in config["elements"]:
        t0 = time.time()
        truth = {tuple(x) for x in items[(items == a).any(axis=1)].tolist()}
        found, seeds = reconstruct(table, a, p, config["peel"])
        correct = len(found & truth)
        report(f"Element {a}: stored items {len(truth)} (expected CP/N = "
               f"{count * p / n:.0f}), reconstructed {len(found)}, correct "
               f"{correct}, false {len(found) - correct}, missed "
               f"{len(truth) - correct}   ({seeds} seeds, {time.time() - t0:.0f} s)")

    if config["baseline"]:
        report()
        t0 = time.time()
        table.fill_random_symmetric(0.5, np.random.default_rng(config["seed"] + 1))
        a = config["elements"][0]
        brng = np.random.default_rng(config["seed"] + 2)
        found, seeds = set(), 0
        while seeds < config["baseline_seeds"]:
            j, k = sorted(brng.choice(np.setdiff1d(np.arange(1, n + 1), [a]), 2,
                                      replace=False).tolist())
            if table.bits[table.row(a, j), k - 1]:
                seeds += 1
                found.update(cliques_through(table, (a, j, k), p))
        report(f"Random baseline (density 1/2), element {a}: {len(found)} "
               f"{p}-cliques through {seeds} random set triples   "
               f"({time.time() - t0:.0f} s)")

    report.save()


if __name__ == "__main__":
    run({
        "N": 1000,
        "P": 10,
        "load": 1.0,            # fraction of nominal capacity
        "elements": [1],        # elements whose items are reconstructed
        "peel": True,           # seed only from triples not yet explained
        "baseline": True,       # also search a random memory of density 1/2
        "baseline_seeds": 2000, # set triples through the element to search from
        "seed": 1,
    })
