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
Iterative decomposition of SHR bundles: complete decomposition and the
mechanisms that limit it, with an item memory filled to capacity.

The item memory is an autoassociative memory (dimension N, population P)
filled with random SHRs to a memory density of 0.5, its nominal capacity.
The number of items is computed in advance from the expected density after L
random autoassociative writes,

  rho(L) = 1 - (2/N) (1 - q2)^L - (1 - 2/N) (1 - q3)^L,
  q2 = P(P-1) / (N(N-1)),  q3 = P(P-1)(P-2) / (N(N-1)(N-2)).

A bundle is the union of k stored items. A query is decimated by the factor D
(a random subset of round(D |S|) elements) while the bundle holds more than P
elements; smaller bundles cannot contain a tie between intact items and are
queried as they are.

Experiment 1: complete decomposition
  Each extracted item is removed from the bundle (sampling without
  replacement), until all k items are extracted, fewer than T elements remain,
  or the budget of B queries per item is exhausted. Removing an item also
  removes the elements it shares with items still in the bundle (erosion).
  Columns:
    first      median number of queries to extract the first item
    done       fraction of bundles completely decomposed within the budget
    q/item     queries per extracted item, up to the last extraction
    lost       mean number of items never extracted
    false      extracted results that are not items of the bundle (total)

Experiment 2: self-support
  Autoassociative storage links each input pair to its own elements as
  outputs. In a memory filled to capacity, almost every pair has been written,
  so every query element is supported by nearly every pair it belongs to,
  whatever item it comes from. The same bundles and queries are evaluated
  twice: against a memory holding only the bundled items ("empty"), and
  against the memory filled to capacity ("full"). Queries are grouped by the
  number of elements retained of the favored item (m) and of the runner-up
  (r); groups with a tie (r = m) or m < T are omitted. A favored item that
  retains exactly T elements next to a runner-up at T - 1 is typically lost in
  the full memory, since the runner-up's query elements outscore the favored
  item's elements that decimation removed.

Experiment 3: shared elements
  Single decimated queries on bundles of random stored items and on bundles of
  pairwise disjoint stored items, against both memories. Columns:
    shared     mean number of elements shared by bundled items
    unique     fraction of queries with a unique favored item (no tie)
    success    fraction of queries that return a bundled item
    s|unique   success among queries with a unique favored item
  In the empty memory, disjoint bundles isolate the effect of shared elements;
  in the full memory, self-support affects disjoint bundles as well.

Results are checkpointed in iterative-decomposition.cache.json, so an
interrupted run resumes where it stopped. Every cache key contains
CACHE_VERSION; entries from earlier versions are never reused. Deleting the
cache recomputes everything.
"""

import os
import sys
import json
import math
import time
import random
import platform
from array import array
from collections import defaultdict
from creating_intelligence import Memory

CACHE_VERSION = 1


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


class Cache:
    """Checkpoints results; deleting the cache recomputes everything."""

    def __init__(self):
        self.path = os.path.splitext(os.path.abspath(__file__))[0] + ".cache.json"
        try:
            with open(self.path) as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}

    @staticmethod
    def key(**fields):
        return json.dumps({**fields, "version": CACHE_VERSION}, sort_keys=True)

    def get(self, **fields):
        return self.data.get(self.key(**fields))

    def put(self, value, **fields):
        self.data[self.key(**fields)] = value
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f)
        os.replace(tmp, self.path)

    def total_seconds(self):
        tag = f'"version": {CACHE_VERSION}'
        return sum(v.get("seconds", 0) for key, v in self.data.items() if tag in key)


def row(values, width=9):
    return "|" + "".join(f" {v:>{width}} |" for v in values)


def rule(count, width=9):
    return "|" + ("-" * (width + 2) + "|") * count


def expected_density(n, p, items):
    q2 = p * (p - 1) / (n * (n - 1))
    q3 = p * (p - 1) * (p - 2) / (n * (n - 1) * (n - 2))
    return (1 - (2 / n) * math.exp(items * math.log1p(-q2))
            - (1 - 2 / n) * math.exp(items * math.log1p(-q3)))


def prefill(n, p, density):
    """Smallest number of random items whose expected density reaches it."""
    lo, hi = 0, 1
    while expected_density(n, p, hi) < density:
        hi *= 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if expected_density(n, p, mid) < density:
            lo = mid
        else:
            hi = mid
    return hi


class Store:
    """Autoassociative item memory with its items kept in a compact array."""

    def __init__(self, n, p, count, seed):
        rng = random.Random(f"{seed}-store-{n}-{p}")
        self.n, self.p, self.count = n, p, count
        self.memory = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
        self.t = self.memory["T"]
        self.elements = array("H" if n < 65536 else "I")
        population = range(1, n + 1)
        for _ in range(count):
            x = sorted(rng.sample(population, p))
            self.elements.extend(x)
            self.memory["store"](x)

    def item(self, i):
        return tuple(self.elements[i * self.p:(i + 1) * self.p])

    def sample(self, rng, k, disjoint=False):
        """k distinct stored items; pairwise disjoint if requested."""
        while True:
            items = [self.item(i) for i in rng.sample(range(self.count), k)]
            if not disjoint or len(set().union(*items)) == k * self.p:
                return items


def empty_memory(n, p, items):
    """A memory holding only the given items."""
    mem = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
    for x in items:
        mem["store"](list(x))
    return mem


def decimate(rng, bundle, d, p):
    if len(bundle) > p:
        return sorted(rng.sample(sorted(bundle), round(d * len(bundle))))
    return sorted(bundle)


def median(values):
    values = sorted(values)
    m = len(values)
    return values[(m - 1) // 2] if m % 2 else (values[m // 2 - 1] + values[m // 2]) / 2


# ---------------------------------------------------------------------------
# Experiment 1: complete decomposition

def decompose(memory, rng, items, d, p, t, budget):
    """Sampling without replacement. Returns per-bundle statistics."""
    targets = set(items)
    state = set().union(*items)
    found, false, queries, last, first = set(), 0, 0, 0, None
    while len(state) >= t and queries < budget and len(found) < len(items):
        queries += 1
        y = memory["retrieve"](decimate(rng, state, d, p))
        if not y:
            continue
        y = tuple(y)
        if y in targets:
            if y not in found:
                found.add(y)
                last = queries
                if first is None:
                    first = queries
        else:
            false += 1
        state -= set(y)
    return {"found": len(found), "false": false, "last": last,
            "first": first if first is not None else budget + 1,
            "done": len(found) == len(items) and false == 0}


def complete_decomposition(cache, store, config, k):
    key = dict(experiment=1, N=store.n, P=store.p, D=config["D"],
               density=config["density"], bundles=config["bundles"],
               budget=config["budget"], seed=config["seed"], k=k)
    cached = cache.get(**key)
    if cached is not None:
        return cached
    started = time.time()
    rng = random.Random(f"{config['seed']}-complete-{store.n}-{store.p}-{k}")
    budget = config["budget"] * k
    runs = [decompose(store.memory, rng, store.sample(rng, k), config["D"],
                      store.p, store.t, budget)
            for _ in range(config["bundles"])]
    m = len(runs)
    found = sum(r["found"] for r in runs)
    result = {
        "first": median([r["first"] for r in runs]),
        "done": sum(r["done"] for r in runs) / m,
        "qpi": sum(r["last"] for r in runs) / found if found else None,
        "lost": k - found / m,
        "false": sum(r["false"] for r in runs),
        "seconds": time.time() - started,
    }
    cache.put(result, **key)
    print(f"  complete decomposition N={store.n} P={store.p} k={k}: "
          f"{result['seconds']:.1f} s", file=sys.stderr, flush=True)
    return result


# ---------------------------------------------------------------------------
# Experiment 2: self-support

def self_support(cache, store, config, k):
    key = dict(experiment=2, N=store.n, P=store.p, D=config["D"],
               density=config["density"], queries=config["queries"],
               seed=config["seed"], k=k)
    cached = cache.get(**key)
    if cached is not None:
        return cached
    started = time.time()
    rng = random.Random(f"{config['seed']}-selfsupport-{store.n}-{store.p}-{k}")
    groups = defaultdict(lambda: [0, 0, 0])      # (m, r) -> [count, empty, full]
    for _ in range(config["queries"]):
        items = store.sample(rng, k, disjoint=True)
        bundle = set().union(*items)
        query = decimate(rng, bundle, config["D"], store.p)
        retained = sorted((len(set(query) & set(x)) for x in items), reverse=True)
        m, r = retained[0], retained[1]
        if m < store.t or r == m:
            continue
        g = groups[(m, r)]
        g[0] += 1
        empty = empty_memory(store.n, store.p, items)
        g[1] += tuple(empty["retrieve"](query)) in items
        empty["clear"]()
        g[2] += tuple(store.memory["retrieve"](query)) in items
    result = {"groups": [[m, r, c, e, f] for (m, r), (c, e, f) in sorted(groups.items())],
              "seconds": time.time() - started}
    cache.put(result, **key)
    print(f"  self-support N={store.n} P={store.p} k={k}: {result['seconds']:.1f} s",
          file=sys.stderr, flush=True)
    return result


# ---------------------------------------------------------------------------
# Experiment 3: shared elements

def shared_elements(cache, store, config, k, disjoint):
    key = dict(experiment=3, N=store.n, P=store.p, D=config["D"],
               density=config["density"], queries=config["queries"],
               seed=config["seed"], k=k, disjoint=disjoint)
    cached = cache.get(**key)
    if cached is not None:
        return cached
    started = time.time()
    rng = random.Random(f"{config['seed']}-shared-{store.n}-{store.p}-{k}-{disjoint}")
    q = config["queries"]
    shared = unique = 0
    success = {"empty": 0, "full": 0}
    success_unique = {"empty": 0, "full": 0}
    for _ in range(q):
        items = store.sample(rng, k, disjoint)
        bundle = set().union(*items)
        shared += k * store.p - len(bundle)
        query = decimate(rng, bundle, config["D"], store.p)
        counts = sorted((len(set(query) & set(x)) for x in items), reverse=True)
        is_unique = counts[0] > counts[1]
        unique += is_unique
        empty = empty_memory(store.n, store.p, items)
        for name, memory in (("empty", empty), ("full", store.memory)):
            hit = tuple(memory["retrieve"](query)) in items
            success[name] += hit
            success_unique[name] += hit and is_unique
        empty["clear"]()
    result = {
        "shared": shared / q, "unique": unique / q,
        "success": {s: v / q for s, v in success.items()},
        "success_unique": {s: (v / unique if unique else None)
                           for s, v in success_unique.items()},
        "seconds": time.time() - started,
    }
    cache.put(result, **key)
    print(f"  shared elements N={store.n} P={store.p} k={k} disjoint={disjoint}: "
          f"{result['seconds']:.1f} s", file=sys.stderr, flush=True)
    return result


# ---------------------------------------------------------------------------

def run(config):
    report = Report()
    cache = Cache()
    report(f"Generated with {os.path.basename(__file__)}")
    report(f"System: {platform.platform()}, {platform.machine()}, "
           f"Python {platform.python_version()}")
    report(f"Backend: {Memory.__module__}")
    report(f"Date: {time.strftime('%Y-%m-%d')}")
    report()
    report("Iterative decomposition with an item memory filled to capacity")
    report()
    n, d = config["N"], config["D"]
    report(f"N = {n}, D = {d}, memory density {config['density']} (expected), "
           f"decimation only above P elements, seed {config['seed']}")
    report()

    for p in config["populations"]:
        count = prefill(n, p, config["density"])
        store = None

        def need_store():
            nonlocal store
            if store is None:
                store = Store(n, p, count, config["seed"])
            return store

        def cached_or(fn, key, *args):
            hit = cache.get(**key)
            return hit if hit is not None else fn(cache, need_store(), config, *args)

        # Experiment 1
        rows = []
        for k in config["bundle_sizes"]:
            key = dict(experiment=1, N=n, P=p, D=d, density=config["density"],
                       bundles=config["bundles"], budget=config["budget"],
                       seed=config["seed"], k=k)
            rows.append((k, cached_or(complete_decomposition, key, k)))
        t = store.t if store else Memory({"A_parameters": (n, p), "B_parameters": (n, p)})["T"]
        report(f"=== Experiment 1: complete decomposition, P = {p}, T = {t}, "
               f"{count} stored items ===")
        report()
        report(f"{config['bundles']} bundles per size, budget {config['budget']} "
               f"queries per item")
        report()
        report(row(["k", "first", "done", "q/item", "lost", "false"]))
        report(rule(6))
        for k, r in rows:
            report(row([k, r["first"], f"{r['done']:.3f}",
                        "-" if r["qpi"] is None else f"{r['qpi']:.2f}",
                        f"{r['lost']:.3f}", r["false"]]))
        report()

        if p == config["mechanisms_P"]:
            # Experiment 2
            report(f"=== Experiment 2: self-support, P = {p}, T = {t} ===")
            report()
            report(f"{config['queries']} single queries per bundle size on bundles of "
                   f"pairwise disjoint items; success in a memory holding only the "
                   f"bundled items (empty) and in the memory filled to capacity (full)")
            report()
            report(row(["k", "m", "r", "queries", "empty", "full"]))
            report(rule(6))
            for k in config["mechanism_sizes"]:
                key = dict(experiment=2, N=n, P=p, D=d, density=config["density"],
                           queries=config["queries"], seed=config["seed"], k=k)
                res = cached_or(self_support, key, k)
                for m, r, c, e, f in res["groups"]:
                    if c >= config["min_group"]:
                        report(row([k, m, r, c, f"{e / c:.3f}", f"{f / c:.3f}"]))
            report()
            report(f"m, r: elements retained of the favored item and of the runner-up; "
                   f"groups with fewer than {config['min_group']} queries are omitted.")
            report()

            # Experiment 3
            report(f"=== Experiment 3: shared elements, P = {p}, T = {t} ===")
            report()
            report(f"{config['queries']} single queries per row")
            report()
            report(row(["k", "items", "shared", "unique", "empty", "full",
                        "empty|u", "full|u"]))
            report(rule(8))
            for k in config["mechanism_sizes"]:
                for disjoint in (False, True):
                    key = dict(experiment=3, N=n, P=p, D=d, density=config["density"],
                               queries=config["queries"], seed=config["seed"], k=k,
                               disjoint=disjoint)
                    res = cached_or(shared_elements, key, k, disjoint)
                    su = res["success_unique"]
                    report(row([k, "disjoint" if disjoint else "random",
                                f"{res['shared']:.2f}", f"{res['unique']:.3f}",
                                f"{res['success']['empty']:.3f}",
                                f"{res['success']['full']:.3f}",
                                "-" if su["empty"] is None else f"{su['empty']:.3f}",
                                "-" if su["full"] is None else f"{su['full']:.3f}"]))
            report()
            report("empty|u, full|u: success among queries with a unique favored item.")
            report()

        if store is not None:
            store.memory["clear"]()
            store = None

    report(f"Total compute time: {cache.total_seconds():.0f} s (single thread, "
           f"cache version {CACHE_VERSION}, excluding filling the item memories)")
    report.save()


if __name__ == "__main__":
    run({
        "N": 2000,
        "populations": [10, 12, 16],
        "mechanisms_P": 10,           # population for experiments 2 and 3
        "D": 0.7,
        "density": 0.5,               # item memory filled to nominal capacity
        "bundle_sizes": [1, 2, 3, 4, 5, 6, 7, 8, 10, 12],
        "bundles": 500,               # experiment 1
        "budget": 10,                 # queries per item, experiment 1
        "mechanism_sizes": [2, 3, 4, 5, 6, 8],
        "queries": 2000,              # experiments 2 and 3
        "min_group": 30,
        "seed": 1,
    })
