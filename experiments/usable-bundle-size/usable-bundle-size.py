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
Usable bundle size: latency of extracting the first item from a bundle.

An autoassociative item memory is prefilled with random SHRs (population P,
dimension N) up to a fixed memory density, the fraction of memory bits set.
The number of items needed for this density is computed in advance from the
expected density after L random autoassociative writes,

  rho(L) = 1 - (2/N) (1 - q2)^L - (1 - 2/N) (1 - q3)^L,
  q2 = P(P-1) / (N(N-1)),  q3 = P(P-1)(P-2) / (N(N-1)(N-2)).

A memory bit belongs to an input pair {i, j} and an output o. A random item
sets it if it contains i, j and o; for the fraction 2/N of bits with o in
{i, j}, it only needs to contain the pair. A density of 0.5 corresponds to
the nominal capacity for autoassociations, ln 2 N(N-1)(N-2) / (P(P-1)(P-2));
a density of 0.0188365 is that of 200,000 items at N = 2000 and P = 10. The
density is never measured during the run, since counting memory bits is
expensive. A bundle is the union of k distinct stored items.
The bundle is queried repeatedly; each query is decimated by the factor D
(a random subset of round(D |S|) elements), except when the bundle holds no
more than P elements, since such a bundle cannot contain a tie between intact
items. The latency is the number of queries until memory retrieval returns one
of the bundled items. Results that are not bundled items are counted as false.
Bundles without an extraction within Q queries are censored: their latency is
only known to exceed Q.

Usable bundle size: the largest k such that the median latency is at most two
queries, for every bundle size up to k. It depends on D; the best decimation
factor is the one that maximizes it. Values equal to the largest tested bundle
size are lower bounds. A best decimation factor at the edge of the tested range
means the optimum may lie outside it.

At this density, nearly every input pair of the memory is in use, so the
memory needs about N^3 / 16 bytes: 0.5 GB for N = 2000, 4 GB for N = 4000.

Tables per item store (N, P):
  median     median latency per bundle size and decimation factor;
             ">Q" if more than half of the bundles are censored
  censored   fraction of bundles without an extraction within Q queries
A decimation series stops at the first bundle size whose median exceeds
`stop` queries (default 4); omitted rows are marked "-". The usable bundle size
only depends on the bundle sizes up to the first median above two, so larger
bundles are not needed. For the same reason, the cap Q can be small: a median
above `stop` is detected once more than half of the bundles fail within
`stop` queries.

Output files are named after the density, for example usable-bundle-size-0.5.txt
and usable-bundle-size-0.5.csv, so runs with different densities do not
overwrite each other. The latency distributions in the CSV file have the columns
N, P, T, D, k, items, median, censored, false, P(L<=l) for each budget l.

Results are checkpointed in usable-bundle-size.cache.json, so an interrupted run
resumes where it stopped. Every cache key contains CACHE_VERSION; entries from
earlier versions are never reused. Deleting the cache recomputes everything.
"""

import os
import sys
import json
import math
import time
import random
import platform
from array import array
from creating_intelligence import Memory

CACHE_VERSION = 1
BUDGETS = (1, 2, 4, 8)                  # time budgets l for P(L <= l)


class Report:
    """Prints lines and collects them for the matching .txt output file."""

    def __init__(self):
        self.lines = []

    def __call__(self, line=""):
        print(line, flush=True)
        self.lines.append(line)

    def save(self, suffix=""):
        base = os.path.splitext(os.path.abspath(__file__))[0] + suffix
        with open(base + ".txt", "w") as f:
            f.write("\n".join(self.lines) + "\n")


class Cache:
    """Checkpoints results per item store, decimation factor and bundle size.
    The cache is only a checkpoint: deleting it recomputes every result."""

    def __init__(self):
        self.path = os.path.splitext(os.path.abspath(__file__))[0] + ".cache.json"
        try:
            with open(self.path) as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}

    @staticmethod
    def key(config, n, p, d, k):
        fields = {f: config[f] for f in ("density", "bundles", "cap", "seed")}
        fields.update({"N": n, "P": p, "D": d, "k": k, "version": CACHE_VERSION})
        return json.dumps(fields, sort_keys=True)

    def get(self, *args):
        return self.data.get(self.key(*args))

    def put(self, value, *args):
        self.data[self.key(*args)] = value
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f)
        os.replace(tmp, self.path)

    def total_seconds(self):
        tag = f'"version": {CACHE_VERSION}'
        return sum(v["seconds"] for key, v in self.data.items() if tag in key)


def row(values, width=8):
    return "|" + "".join(f" {v:>{width}} |" for v in values)


def rule(count, width=8):
    return "|" + ("-" * (width + 2) + "|") * count


def expected_density(n, p, items):
    """Expected fraction of memory bits set after `items` random
    autoassociative writes."""
    q2 = p * (p - 1) / (n * (n - 1))
    q3 = p * (p - 1) * (p - 2) / (n * (n - 1) * (n - 2))
    return (1 - (2 / n) * math.exp(items * math.log1p(-q2))
            - (1 - 2 / n) * math.exp(items * math.log1p(-q3)))


def prefill(n, p, density):
    """Smallest number of random items whose expected density reaches
    `density`."""
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
        self.p, self.count = p, count
        self.memory = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
        self.elements = array("H" if n < 65536 else "I")
        population = range(1, n + 1)
        for _ in range(count):
            x = sorted(rng.sample(population, p))
            self.elements.extend(x)
            self.memory["store"](x)

    def item(self, i):
        return tuple(self.elements[i * self.p:(i + 1) * self.p])

    def sample(self, rng, k):
        return [self.item(i) for i in rng.sample(range(self.count), k)]


def latency(mem, rng, bundle_items, d, p, cap):
    """Queries until a bundled item is extracted (None if censored), and the
    number of false results."""
    targets = set(bundle_items)
    bundle = sorted(set().union(*bundle_items))
    false = 0
    for q in range(1, cap + 1):
        if len(bundle) > p:
            query = sorted(rng.sample(bundle, round(d * len(bundle))))
        else:
            query = bundle
        y = mem["retrieve"](query)
        if not y:
            continue
        if tuple(y) in targets:
            return q, false
        false += 1
    return None, false


def median(latencies, cap):
    """Median latency; None if more than half of the bundles are censored."""
    values = sorted(cap + 1 if x is None else x for x in latencies)
    m = len(values)
    mid = values[(m - 1) // 2] if m % 2 else (values[m // 2 - 1] + values[m // 2]) / 2
    return None if mid > cap else mid


def measure(cache, config, store, n, p, d, k):
    """Latency statistics for one bundle size, from the cache if available."""
    cached = cache.get(config, n, p, d, k)
    if cached is not None:
        return cached
    cap = config["cap"]
    started = time.time()
    rng = random.Random(f"{config['seed']}-{n}-{p}-{d}-{k}")
    runs = [latency(store.memory, rng, store.sample(rng, k), d, p, cap)
            for _ in range(config["bundles"])]
    lat = [r[0] for r in runs]
    m = len(lat)
    result = {
        "median": median(lat, cap),
        "censored": lat.count(None) / m,
        "false": sum(r[1] for r in runs),
        "cdf": [sum(x is not None and x <= b for x in lat) / m for b in BUDGETS],
        "seconds": time.time() - started,
    }
    cache.put(result, config, n, p, d, k)
    print(f"  N={n} P={p} D={d} k={k}: median {result['median']}, "
          f"{result['seconds']:.1f} s", file=sys.stderr, flush=True)
    return result


def usable(results):
    """Largest k with median <= 2 for every bundle size up to k."""
    best = 0
    for k, r in results:
        if r is None or r["median"] is None or r["median"] > 2:
            break
        best = k
    return best


def fmt(value):
    return str(int(value)) if value == int(value) else f"{value:.1f}"


def run(config):
    report = Report()
    cache = Cache()
    report(f"Generated with {os.path.basename(__file__)}")
    report(f"System: {platform.platform()}, {platform.machine()}, "
           f"Python {platform.python_version()}")
    report(f"Backend: {Memory.__module__}")
    report(f"Date: {time.strftime('%Y-%m-%d')}")
    report()
    report("Latency of extracting the first item from a bundle, "
           "with a prefilled item memory")
    report()
    report(f"Item memory filled with random autoassociations to density "
           f"{config['density']} (expected); {config['bundles']} bundles per size; "
           f"cap Q = {config['cap']} queries; a decimation series stops once the "
           f"median exceeds {config['stop']}; decimation only above P elements; "
           f"seed {config['seed']}")
    report()

    sizes = list(range(1, config["max_bundle"] + 1))
    cap = config["cap"]
    summary = {}
    csv = []
    for n in config["dimensions"]:
        for p in config["populations"]:
            count = prefill(n, p, config["density"])
            store, t = None, None
            table = {}
            for d in config["decimation"]:
                results, stopped = [], False
                for k in sizes:
                    if stopped:
                        results.append((k, None))
                        continue
                    if store is None and cache.get(config, n, p, d, k) is None:
                        store = Store(n, p, count, config["seed"])
                    r = measure(cache, config, store, n, p, d, k)
                    results.append((k, r))
                    stopped = r["median"] is None or r["median"] > config["stop"]
                table[d] = results
            if store is None:          # everything cached: T from a small memory
                t = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})["T"]
            else:
                t = store.memory["T"]
                store.memory["clear"]()
                store = None

            report(f"=== N = {n}, P = {p}, T = {t}, {count} stored items ===")
            report()
            labels = [f"D={d}" for d in config["decimation"]]
            for name, cell in (
                    ("median latency (queries)",
                     lambda r: "-" if r is None else
                     (f">{cap}" if r["median"] is None else fmt(r["median"]))),
                    ("censored: no extraction within Q queries",
                     lambda r: "-" if r is None else f"{r['censored']:.3f}")):
                report(name)
                report()
                report(row(["k"] + labels))
                report(rule(len(labels) + 1))
                for i, k in enumerate(sizes):
                    report(row([k] + [cell(table[d][i][1]) for d in config["decimation"]]))
                report()
            falses = [sum(r["false"] for _, r in table[d] if r) for d in config["decimation"]]
            report("false extractions (total): " + ", ".join(
                f"D={d}: {f}" for d, f in zip(config["decimation"], falses)))
            report()

            summary[(n, p)] = (t, count, {d: usable(table[d]) for d in config["decimation"]})
            for d in config["decimation"]:
                for k, r in table[d]:
                    if r is None:
                        continue
                    csv.append(f"{n},{p},{t},{d},{k},{count},"
                               f"{'' if r['median'] is None else r['median']},"
                               f"{r['censored']:.4f},{r['false']},"
                               + ",".join(f"{c:.4f}" for c in r["cdf"]))

    report("=== Usable bundle size (median latency <= 2 queries) ===")
    report()
    labels = [f"D={d}" for d in config["decimation"]]
    report(row(["N", "P", "items"] + labels + ["best", "best D"], width=9))
    report(rule(len(labels) + 5, width=9))
    top = config["max_bundle"]
    for (n, p), (t, count, sizes_by_d) in summary.items():
        best = max(sizes_by_d.values())
        best_d = [d for d, v in sizes_by_d.items() if v == best]
        edge = (" *" if len(config["decimation"]) > 1 and best < top
                and (config["decimation"][0] in best_d
                     or config["decimation"][-1] in best_d) else "")
        cells = [f">={v}" if v == top else v for v in sizes_by_d.values()]
        report(row([n, p, count] + cells
                   + [f">={best}" if best == top else best,
                      "/".join(str(d) for d in best_d) + edge], width=9))
    report()
    report(f">= {top}: no limit within the tested bundle sizes. * best decimation "
           f"factor at the edge of the tested range; the optimum may lie outside it.")
    report()

    for d in config["decimation"]:
        report(f"Usable bundle size by dimension and population, D = {d} "
               f"(T in parentheses)")
        report()
        populations = [p for p in config["populations"]
                       if any((n, p) in summary for n in config["dimensions"])]
        report(row(["N"] + [f"P={p}" for p in populations], width=9))
        report(rule(1 + len(populations), width=9))
        for n in config["dimensions"]:
            cells = []
            for p in populations:
                if (n, p) not in summary:
                    cells.append("-")
                    continue
                t, _, sizes_by_d = summary[(n, p)]
                v = sizes_by_d[d]
                cells.append(f"{'>=' if v == top else ''}{v} ({t})")
            report(row([n] + cells, width=9))
        report()

    suffix = f"-{config['density']}"
    path = os.path.splitext(os.path.abspath(__file__))[0] + suffix + ".csv"
    with open(path, "w") as f:
        f.write("N,P,T,D,k,items,median,censored,false,"
                + ",".join(f"P(L<={b})" for b in BUDGETS) + "\n")
        f.write("\n".join(csv) + "\n")

    report(f"Total compute time: {cache.total_seconds():.0f} s (single thread, "
           f"cache version {CACHE_VERSION})")
    report.save(suffix)


if __name__ == "__main__":
    run({
        "dimensions": [1000, 2000, 4000],
        "populations": [10, 12, 14, 16],
        "decimation": [0.7],
        "density": 0.5,         # memory filled to nominal capacity
        "bundles": 1000,
        "cap": 8,
        "stop": 4,
        "max_bundle": 40,
        "seed": 1,
    })
