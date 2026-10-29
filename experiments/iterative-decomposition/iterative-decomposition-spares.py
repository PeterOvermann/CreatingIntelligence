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
Iterative decomposition: usable bundle size for unbundling superposed SHRs
against an item store.

A lexicon of random SHRs (population P, dimension N) is stored as
auto-associations in an item memory. A bundle is the union of k distinct
lexicon items. Decomposition mirrors the circuit in IterativeDecomposition.json:
at every cycle the remaining bundle S is decimated by the factor D (a random
subset of round(D |S|) elements) and used as a query. A non-empty result Y is
recorded as an extracted item and removed from the state (inhibitory feedback,
S <- S \\ Y). An empty result is a failed cycle (pattern matching tie or no
match). Decomposition ends when all k items have been extracted, when fewer
than T elements remain, or when the budget of B cycles per bundled item is
exhausted.

Sampling modes:
  without    sampling without replacement (default): each extracted item is
             removed from the bundle, which forms dynamically and shrinks
  with       sampling with replacement: the bundle is stored (for instance as
             a hyperassociation) and every query decimates the intact bundle.
             Extracted items are recorded but not removed, so items can be
             recalled repeatedly and erosion cannot occur.

Query strategies (sampling without replacement):
  always     decimate every query, as in the circuit (default)
  on-empty   query the undecimated state first; after an empty result,
             decimate the next query. Isolates the cost of decimation itself.
  fallback   decimate every query; after `patience` consecutive empty
             results, query the undecimated state once. Recovers items that
             erosion has pushed out of reach of decimated queries.

Decimation rule: a query is decimated only while the remaining bundle holds
more than P elements. A smaller remainder cannot contain a tie between intact
items, so it is queried as it is (config "decimate_above_P", default True).

Removing an extracted item also removes elements it shares by chance with
items still in the bundle (erosion). An eroded item wins decimated queries
less often while other items remain. With the decimation rule above, it is
lost only if it drops below T elements; if every query is decimated
("decimate_above_P": False), it is also lost once it is the last item and
D n < T (for P = 10, T = 7, D = 0.8: n = 8 yields 6 query elements).

Columns of the detailed table:
  |S|        mean bundle population (union of k items; spurious overlaps merge)
  sparsity   mean |S| / N
  p(1st)     probability that the first query on the full bundle returns one
             of its items. Exact ties make this lowest for k = 2: decimation
             removes elements evenly from both items with high probability.
  false      extracted results that are not items of the bundle (intruders
             or sets that are not lexicon items), total over all trials
  lost       mean number of bundle items never extracted
  pred       erosion model for lost: an item is trapped if it loses more than
             e elements: e = P - T with the decimation rule above, otherwise
             the largest e with round(D (P - e)) >= T. Elements
             are lost to items extracted earlier; their number is modeled as
             Poisson with mean (k - 1) P^2 / (2N). Ties are not modeled.
  cyc/item   cycles up to the last successful extraction, per extracted item
             (trailing cycles of stalled runs are excluded; "-" if no item
             was extracted)
  stalled    fraction of bundles that exhausted the budget with items missing
  eroded     fraction of bundles that ended with fewer than T elements left
             and items missing
  done@2k    fraction of bundles fully decomposed, without false results,
             within 2 cycles per item
  done@Bk    the same within the full budget of B cycles per item

The section on sampling with and without replacement reports, per bundle
size k:
  p(query)   fraction of queries that return a bundled item (new or repeated)
  done@Bk    fraction of bundles fully recalled within the budget
  q/item     median number of queries per item until a bundle is fully
             recalled (complete bundles only)
  coupon     H_k / p(query), the expected queries per item for sampling with
             replacement (coupon collector), H_k = 1 + 1/2 + ... + 1/k
  r@1k ...   mean fraction of items recalled after k, 2k, 4k and 8k queries.
             With replacement, the expected value is about 1 - exp(-p q / k).
  lost       mean number of items never recalled within the budget

The section on first-extraction latency measures how many queries it takes
to extract the first item from a full bundle of k items, the time constraint
that matters if a bundle decays while it is being decomposed. Until the first
item is extracted the bundle is unchanged, so the latency of one bundle is
geometric with its own success probability. Some large bundles almost never
yield an item, so the mean latency over bundles is undefined; queries stop
after Q attempts and such bundles are censored rather than assigned a value.
Columns:
  P(L<=l)    fraction of bundles whose first item is extracted within l queries
             (exact up to Q, since every bundle has the same cap)
  median     median latency; "-" if more than half of the bundles are censored
  censored   fraction of bundles without an extraction within Q queries
  1/rate     successes per query, pooled over all queries until the first
             success or the cap, inverted (latency at a constant success rate)
  false      queries that returned an item not in the bundle (total)
The span for a time budget of l queries and reliability r is the largest k
such that a fraction r of bundles yields its first item within l queries, for
every bundle size up to k (r = 0.5: median latency at most l). The summary
relates the span to the retained margin D P - T, the expected number of
elements of an intact item that a decimated query retains above the threshold.

The section on shared elements isolates the effect of shared elements on a single
decimated query. The item store holds only the k bundled items, which are
either independent random SHRs or pairwise disjoint SHRs. Columns:
  shared     mean number of elements shared by bundled items (P k - |S|)
  unique     fraction of queries in which one bundled item has strictly more
             elements in the query than any other (no tie)
  success    fraction of queries that return a bundled item
  s|unique   success among queries with a unique best item

Usable bundle size, per configuration (largest k such that the criterion
holds for every bundle size up to k):
  k(95%)     done@Bk >= 0.95: reliable complete decomposition
  k(cyc<=2)  cyc/item <= 2: on average at most one failed query per item
  A value equal to the largest tested k is a lower bound. If a sweep starts
  above k = 1 and its first bundle size already fails the criterion, the
  result is reported as "<k" (below the tested range).

The section on the economic SHR population summarizes the measured usable
bundle sizes k(95%) per dimension and population. The economic population is
the smallest P whose k(95%) reaches at least 90 percent of the value for the
largest tested population (the interference limit). The section also reports
sparsity and the nominal capacity for autoassociations,
ln 2 N(N-1)(N-2) / (P(P-1)(P-2)).
"""

import os
import sys
import json
import math
import time
import random
import platform
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


def header(report, title):
    report(f"Generated with {os.path.basename(__file__)}")
    report(f"System: {platform.platform()}, {platform.machine()}, "
           f"Python {platform.python_version()}")
    report(f"Backend: {Memory.__module__}")
    report(f"Date: {time.strftime('%Y-%m-%d')}")
    report()
    report(title)
    report()


def cpi_text(value):
    return "-" if value is None else f"{value:.2f}"


def row(values, width=9):
    return "|" + "".join(f" {v:>{width}} |" for v in values)


def rule(count, width=9):
    return "|" + ("-" * (width + 2) + "|") * count


def random_set(rng, n, p):
    return sorted(rng.sample(range(1, n + 1), p))


def build_item_store(rng, n, p, lexicon_size):
    """Item memory holding `lexicon_size` distinct random SHRs as auto-associations."""
    mem = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
    lexicon, index = [], {}
    while len(lexicon) < lexicon_size:
        x = random_set(rng, n, p)
        if tuple(x) not in index:
            index[tuple(x)] = len(lexicon)
            lexicon.append(x)
            mem["store"](x)
    return mem, lexicon, index


def erosion_tolerance(p, t, d, above_p=True):
    """Largest number of elements an item can lose and still be extracted as
    the last item in the bundle, or -1 if even the intact item fails. With
    the decimation rule (decimate only above P elements), the last item is
    queried undecimated and only needs T elements."""
    if above_p:
        return p - t
    return max((e for e in range(p) if round(d * (p - e)) >= t), default=-1)


def predicted_lost(n, p, t, d, k, above_p=True):
    """Erosion model: expected number of items trapped below reach."""
    e = erosion_tolerance(p, t, d, above_p)
    if e < 0:
        return float(k)
    lam = (k - 1) * p * p / (2 * n)
    stay = sum(math.exp(-lam) * lam ** j / math.factorial(j) for j in range(e + 1))
    return k * (1 - stay)


def density(mem, n):
    return mem["memorycount"]() / (n * n * (n - 1) / 2)


def decompose(mem, rng, lexicon, index, items, d, t, max_cycles, strategy,
              patience=2, replacement=False, p=None):
    """Decompose the bundle of `items`. Returns per-trial statistics.
    With replacement, every query decimates the intact bundle and extracted
    items are not removed."""
    targets = set(items)
    state = set().union(*(lexicon[i] for i in items))
    size = len(state)
    found, false, cycles, last, done_at, first_ok = set(), 0, 0, 0, None, None
    hits, new_at = 0, []
    decimate = strategy != "on-empty"
    empties = 0
    while len(state) >= t and cycles < max_cycles and len(found) < len(items):
        cycles += 1
        elements = sorted(state)
        if decimate and (p is None or len(elements) > p):
            query = rng.sample(elements, round(d * len(elements)))
        else:
            query = elements
        y = mem["retrieve"](sorted(query))
        item = index.get(tuple(y)) if y else None
        if first_ok is None:
            first_ok = item is not None and item in targets
        if strategy == "on-empty":
            decimate = not y
        elif strategy == "fallback":
            empties = empties + 1 if not y else 0
            decimate = empties < patience
            if not decimate:
                empties = 0
        if not y:
            continue
        if item is not None and item in targets:
            hits += 1
            if item not in found:
                found.add(item)
                new_at.append(cycles)
                last = cycles
                if len(found) == len(items):
                    done_at = cycles
        else:
            false += 1
        if not replacement:
            state -= set(y)
    missing = len(found) < len(items)
    return {"size": size, "first": bool(first_ok), "found": len(found),
            "false": false, "last": last, "cycles": cycles, "hits": hits,
            "new_at": new_at,
            "stalled": missing and len(state) >= t and cycles >= max_cycles,
            "eroded": missing and len(state) < t,
            "done_at": done_at if false == 0 else None}


class Cache:
    """Checkpoints results per configuration and bundle size, so an interrupted
    run resumes where it stopped. The cache is only a checkpoint: deleting it
    makes the script recompute every result from scratch. Each bundle size is seeded independently,
    therefore resumed and uninterrupted runs give identical results."""

    def __init__(self):
        self.path = os.path.splitext(os.path.abspath(__file__))[0] + ".cache.json"
        try:
            with open(self.path) as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}

    @staticmethod
    def key(config, k):
        fields = ("N", "P", "D", "lexicon", "strategy", "budget", "trials", "seed")
        key = {f: config[f] for f in fields}
        key["version"] = CACHE_VERSION
        if config["strategy"] == "fallback":
            key["patience"] = config["patience"]
        if config.get("sampling", "without") == "with":
            key["sampling"] = "with"
        elif config.get("decimate_above_P", True):
            key["rule"] = "decimate above P"
        return json.dumps(key, sort_keys=True) + f"|k={k}"

    def get(self, config, k):
        return self.data.get(self.key(config, k))

    def put(self, config, k, value):
        self.data[self.key(config, k)] = value
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.data, f)
        os.replace(tmp, self.path)

    def total_seconds(self):
        """Compute time of all results of the current cache version."""
        tag = f'"version": {CACHE_VERSION}'
        return sum(v["seconds"] for key, v in self.data.items() if tag in key)


CACHE = None
CACHE_VERSION = 3     # part of every cache key: entries from earlier script
                      # versions are never reused. Increase on any change that
                      # affects results.
CURVE = (1, 2, 4, 8)        # recall-curve checkpoints, in multiples of k queries


def median(values):
    if not values:
        return None
    values = sorted(values)
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def sweep(config):
    """Run all bundle sizes for one configuration. Returns the per-k results."""
    n, p, d = config["N"], config["P"], config["D"]
    mem = None
    info = None
    results = []
    for k in config["bundle_sizes"]:
        cached = CACHE.get(config, k)
        if cached is None:
            if mem is None:
                mem, lexicon, index = build_item_store(
                    random.Random(config["seed"]), n, p, config["lexicon"])
                t = mem["T"]
                info = {"T": t, "density": density(mem, n)}
            started = time.time()
            rng = random.Random(f"{config['seed']}-{k}")
            budget = config["budget"] * k
            trials = [decompose(mem, rng, lexicon, index,
                                rng.sample(range(len(lexicon)), k), d, t, budget,
                                config["strategy"], config.get("patience", 2),
                                config.get("sampling", "without") == "with",
                                p if config.get("decimate_above_P", True) else None)
                      for _ in range(config["trials"])]
            m = len(trials)
            found = sum(r["found"] for r in trials)
            cached = {
                "k": k, "info": info,
                "size": sum(r["size"] for r in trials) / m,
                "first": sum(r["first"] for r in trials) / m,
                "false": sum(r["false"] for r in trials),
                "lost": k - found / m,
                "cpi": sum(r["last"] for r in trials) / found if found else None,
                "stalled": sum(r["stalled"] for r in trials) / m,
                "eroded": sum(r["eroded"] for r in trials) / m,
                "tight": sum(r["done_at"] is not None and r["done_at"] <= 2 * k
                             for r in trials) / m,
                "full": sum(r["done_at"] is not None for r in trials) / m,
                "p_query": sum(r["hits"] for r in trials)
                           / max(1, sum(r["cycles"] for r in trials)),
                "median_q": median([r["done_at"] / k for r in trials
                                    if r["done_at"] is not None]),
                "curve": [sum(sum(c <= f * k for c in r["new_at"]) for r in trials)
                          / (m * k) for f in CURVE],
                "seconds": time.time() - started,
            }
            CACHE.put(config, k, cached)
            print(f"  [{config['N']}/{config['P']} D={d} {config['strategy']} "
                  f"{config.get('sampling', 'without')} replacement "
                  f"L={config['lexicon']}] k={k} done in {cached['seconds']:.1f} s",
                  file=sys.stderr, flush=True)
        info = cached["info"]
        if cached["cpi"] is not None and cached["cpi"] >= 1e8:    # older cache entries
            cached = {**cached, "cpi": None}
        results.append(cached)
    if mem is not None:
        mem["clear"]()
    return info, results


def usable(results, key, level):
    """Largest k such that results[key] >= level for every bundle size up to k."""
    best = 0
    for r in results:
        if r[key] < level:
            break
        best = r["k"]
    return best


def usable_text(results, value):
    """Usable size as text, marking results below a sweep's tested range."""
    if value == 0 and results and results[0]["k"] > 1:
        return f"<{results[0]['k']}"
    return value


def usable_max(results, key, level):
    """Largest k such that results[key] <= level for every bundle size up to k."""
    best = 0
    for r in results:
        if r[key] is None or r[key] > level:
            break
        best = r["k"]
    return best


def detailed(report, config):
    info, results = sweep(config)
    n, p = config["N"], config["P"]
    report(f"N = {n}, P = {p}, T = {info['T']}, D = {config['D']}, "
           f"strategy {config['strategy']}, "
           f"lexicon {config['lexicon']} items (item store density "
           f"{info['density']:.4f}), {config['trials']} bundles per row, "
           f"budget {config['budget']} cycles per item")
    report()
    b = config["budget"]
    report(row(["k", "|S|", "sparsity", "p(1st)", "false", "lost", "pred",
                "cyc/item", "stalled", "eroded", "done@2k", f"done@{b}k"]))
    report(rule(12))
    for r in results:
        pred = predicted_lost(n, p, info["T"], config["D"], r["k"],
                              config.get("decimate_above_P", True))
        report(row([r["k"], f"{r['size']:.1f}", f"{100 * r['size'] / n:.2f}%",
                    f"{r['first']:.3f}", r["false"], f"{r['lost']:.3f}",
                    f"{pred:.3f}", cpi_text(r["cpi"]), f"{r['stalled']:.3f}",
                    f"{r['eroded']:.3f}", f"{r['tight']:.3f}", f"{r['full']:.3f}"]))
    report()
    report(f"Usable bundle size: k(95%) = {usable(results, 'full', 0.95)}, "
           f"k(cyc<=2) = {usable_max(results, 'cpi', 2.0)}")
    report()


def compact(report, title, variants, base):
    """Compare variants of the base configuration per bundle size k."""
    report(title)
    report()
    runs = []
    for label, change in variants:
        config = {**base, **change}
        info, results = sweep(config)
        runs.append((label, config, info, results))
    for label, config, info, _ in runs:
        report(f"  {label}: N = {config['N']}, P = {config['P']}, T = {info['T']}, "
               f"D = {config['D']}, strategy {config['strategy']}"
               + (f" (patience {config['patience']})"
                  if config["strategy"] == "fallback" else "")
               + f", lexicon {config['lexicon']}, "
               f"item store density {info['density']:.4f}, "
               f"{config['trials']} bundles per row")
    report()
    labels = [label for label, *_ in runs]
    b = base["budget"]
    for key, name in (
            ("full", f"done@{b}k: complete decomposition within {b} cycles per item"),
            ("cpi", "cyc/item: cycles per extracted item"),
            ("lost", "lost: mean number of items never extracted")):
        report(name)
        report()
        report(row(["k"] + labels))
        report(rule(len(labels) + 1))
        for i, k in enumerate(base["bundle_sizes"]):
            cells = [cpi_text(results[i][key]) if key == "cpi"
                     else f"{results[i][key]:.3f}" for *_, results in runs]
            report(row([k] + cells))
        report()
    report(row(["usable"] + labels))
    report(rule(len(labels) + 1))
    report(row(["k(95%)"] + [usable_text(r, usable(r, "full", 0.95))
                             for *_, r in runs]))
    report(row(["k(cyc<=2)"] + [usable_text(r, usable_max(r, "cpi", 2.0))
                                for *_, r in runs]))
    report(row(["false"] + [sum(x["false"] for x in r) for *_, r in runs]))
    report()
    report("Values equal to the largest tested k are lower bounds; "
           "\"<k\" means below the tested range.")
    report()


LATENCY = (1, 2, 4, 8, 16, 32)     # time budgets for P(L <= l)


def first_latency(mem, rng, lexicon, index, items, d, p, max_queries, above_p):
    """Queries until the first bundled item is extracted from the full bundle,
    or None if none is extracted within max_queries. Returns (latency, false)."""
    targets = set(items)
    bundle = sorted(set().union(*(lexicon[i] for i in items)))
    false = 0
    for q in range(1, max_queries + 1):
        if not above_p or len(bundle) > p:
            query = rng.sample(bundle, round(d * len(bundle)))
        else:
            query = bundle
        y = mem["retrieve"](sorted(query))
        if not y:
            continue
        if index.get(tuple(y)) in targets:
            return q, false
        false += 1
    return None, false


def latency_sweep(config):
    """First-extraction latency for all bundle sizes of one configuration."""
    n, p, d, cap = config["N"], config["P"], config["D"], config["budget"]
    key_config = {**config, "strategy": "first-latency"}
    mem = None
    info = None
    results = []
    for k in config["bundle_sizes"]:
        cached = CACHE.get(key_config, k)
        if cached is None:
            if mem is None:
                mem, lexicon, index = build_item_store(
                    random.Random(config["seed"]), n, p, config["lexicon"])
                info = {"T": mem["T"], "density": density(mem, n)}
            started = time.time()
            rng = random.Random(f"latency-{config['seed']}-{k}")
            runs = [first_latency(mem, rng, lexicon, index,
                                  rng.sample(range(len(lexicon)), k), d, p, cap,
                                  config.get("decimate_above_P", True))
                    for _ in range(config["trials"])]
            m = len(runs)
            lat = [r[0] for r in runs]
            done = sorted(x for x in lat if x is not None)
            queries = sum(cap if x is None else x for x in lat)
            cached = {
                "k": k, "info": info,
                "cdf": [sum(x is not None and x <= l for x in lat) / m for l in LATENCY],
                "median": done[(m - 1) // 2] if len(done) > (m - 1) // 2 else None,
                "censored": lat.count(None) / m,
                "rate": len(done) / queries,
                "false": sum(r[1] for r in runs),
                "seconds": time.time() - started,
            }
            CACHE.put(key_config, k, cached)
            print(f"  [latency {n}/{p} D={d}] k={k} done in {cached['seconds']:.1f} s",
                  file=sys.stderr, flush=True)
        info = cached["info"]
        results.append(cached)
    if mem is not None:
        mem["clear"]()
    return info, results


def span(results, budget, level=0.5):
    """Largest k such that a fraction `level` of bundles yield their first item
    within `budget` queries, for every bundle size up to k. With level 0.5,
    this is the largest k whose median latency is at most `budget`."""
    j = LATENCY.index(budget)
    best = 0
    for r in results:
        if r["cdf"][j] < level:
            break
        best = r["k"]
    return best


SPANS = ((2, 0.5), (4, 0.5), (4, 0.9), (8, 0.9))   # (time budget, reliability)


def latency_report(report, base, config):
    """First-extraction latency per dimension, population and decimation."""
    summary = []
    for n in config["dimensions"]:
        for p in config["populations"]:
            runs = []
            for d in config["decimation"]:
                cfg = {**base, **config["overrides"], "N": n, "P": p, "D": d}
                info, results = latency_sweep(cfg)
                runs.append((d, cfg, info, results))
            cfg, t = runs[0][1], runs[0][2]["T"]
            report(f"N = {n}, P = {p}, T = {t}, lexicon {cfg['lexicon']}, "
                   f"{cfg['trials']} bundles per row, cap Q = {cfg['budget']} "
                   f"queries, decimation only above P elements")
            report()
            labels = [f"D={d}" for d, *_ in runs]
            for name, cell in (
                    ("median latency (queries)",
                     lambda r: "-" if r["median"] is None else r["median"]),
                    ("P(L<=4): first item within 4 queries",
                     lambda r: f"{r['cdf'][LATENCY.index(4)]:.3f}"),
                    ("censored: no item within Q queries",
                     lambda r: f"{r['censored']:.3f}")):
                report(name)
                report()
                report(row(["k"] + labels))
                report(rule(len(labels) + 1))
                for i, k in enumerate(cfg["bundle_sizes"]):
                    report(row([k] + [cell(res[i]) for *_, res in runs]))
                report()
            for d, cfg, info, results in runs:
                summary.append((n, p, info["T"], d, results))

    report("Span: largest k such that a fraction r of bundles yields its first "
           "item within l queries, for all bundle sizes up to k. Retained "
           "margin: D P - T, the expected number of elements of an intact item "
           "that a decimated query retains above the threshold.")
    report()
    report(row(["N", "P", "T", "D", "D P - T"]
               + [f"l={l},r={r}" for l, r in SPANS]))
    report(rule(5 + len(SPANS)))
    for n, p, t, d, results in summary:
        report(row([n, p, t, d, f"{d * p - t:.1f}"]
                   + [span(results, l, r) for l, r in SPANS]))
    report()

    l, r = config["pivot"]
    report(f"Span (l = {l} queries, r = {r}) by dimension and population, "
           f"one table per decimation factor")
    report()
    for d in config["decimation"]:
        report(f"D = {d}")
        report()
        report(row(["N"] + [f"P={p}" for p in config["populations"]]))
        report(rule(1 + len(config["populations"])))
        for n in config["dimensions"]:
            cells = [span(res, l, r) for nn, pp, t, dd, res in summary
                     if nn == n and dd == d]
            report(row([n] + cells))
        report()
    report("Best decimation factor: largest span (l = 2, r = 0.5) per dimension "
           "and population; ties list all best factors")
    report()
    report(row(["N"] + [f"P={p}" for p in config["populations"]], width=17))
    report(rule(1 + len(config["populations"]), width=17))
    for n in config["dimensions"]:
        cells = []
        for p in config["populations"]:
            spans = [(span(res, 2, 0.5), dd) for nn, pp, t, dd, res in summary
                     if nn == n and pp == p]
            best = max(v for v, _ in spans)
            ds = "/".join(f"{dd}" for v, dd in spans if v == best)
            cells.append(f"{best} ({ds})")
        report(row([n] + cells, width=17))
    report()
    report("Values equal to the largest tested k are lower bounds.")
    report()


def sampling_report(report, variants, base):
    """Sampling with and without replacement: cost and recall curve per k."""
    for label, change in variants:
        config = {**base, **change}
        info, results = sweep(config)
        mode = config.get("sampling", "without")
        report(f"{label}: N = {config['N']}, P = {config['P']}, T = {info['T']}, "
               f"D = {config['D']}, sampling {mode} replacement, lexicon "
               f"{config['lexicon']}, {config['trials']} bundles per row, "
               f"budget {config['budget']} queries per item")
        report()
        b = config["budget"]
        report(row(["k", "p(query)", f"done@{b}k", "q/item", "coupon"]
                   + [f"r@{f}k" for f in CURVE] + ["lost"]))
        report(rule(6 + len(CURVE)))
        for r in results:
            k = r["k"]
            h = sum(1 / i for i in range(1, k + 1))
            coupon = (f"{h / r['p_query']:.2f}"
                      if mode == "with" and r.get("p_query") else "-")
            q = "-" if r.get("median_q") is None else f"{r['median_q']:.2f}"
            curve = r.get("curve") or [None] * len(CURVE)
            report(row([k, f"{r.get('p_query', 0):.3f}", f"{r['full']:.3f}", q, coupon]
                       + ["-" if c is None else f"{c:.3f}" for c in curve]
                       + [f"{r['lost']:.3f}"]))
        report()


def shared_elements(report, config):
    """Single decimated queries against a store holding only the bundled items."""
    n, d, trials = config["N"], config["D"], config["trials"]
    report(f"N = {n}, D = {d}, {trials} queries per row, item store holds "
           f"only the bundled items")
    report()
    report(row(["P", "k", "items", "shared", "unique", "success", "s|unique"]))
    report(rule(7))
    for p, sizes in config["cases"]:
        for k in sizes:
            for disjoint in (False, True):
                rng = random.Random(f"shared-{p}-{k}-{disjoint}")
                shared = unique = success = success_unique = 0
                for _ in range(trials):
                    if disjoint:
                        pool = rng.sample(range(1, n + 1), p * k)
                        items = [sorted(pool[i * p:(i + 1) * p]) for i in range(k)]
                    else:
                        items = [random_set(rng, n, p) for _ in range(k)]
                    mem = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
                    for x in items:
                        mem["store"](x)
                    bundle = sorted(set().union(*items))
                    shared += p * k - len(bundle)
                    query = set(rng.sample(bundle, round(d * len(bundle))))
                    counts = sorted(len(query & set(x)) for x in items)
                    is_unique = k == 1 or counts[-1] > counts[-2]
                    hit = mem["retrieve"](sorted(query)) in items
                    unique += is_unique
                    success += hit
                    success_unique += hit and is_unique
                    mem["clear"]()      # frees the memory (C backend)
                report(row([p, k, "disjoint" if disjoint else "random",
                            f"{shared / trials:.2f}", f"{unique / trials:.3f}",
                            f"{success / trials:.3f}",
                            f"{success_unique / unique:.3f}" if unique else "-"]))
    report()


def economic_population(report, base, config):
    """Measured usable bundle sizes per dimension and population, and the
    smallest population that reaches the interference limit."""
    rows = {}
    for n, populations, overrides in config["cases"]:
        results = {}
        for p in populations:
            info, res = sweep({**base, **overrides, "N": n, "P": p})
            results[p] = (info, res, usable(res, "full", 0.95))
        reference = results[populations[-1]][2]
        economic = next(p for p in populations
                        if results[p][2] >= config["level"] * reference)
        cells = [usable_text(results[p][1], results[p][2]) for p in populations]
        capacity = (math.log(2) * n * (n - 1) * (n - 2)
                    / (economic * (economic - 1) * (economic - 2)))
        rows[n] = (cells, economic, results[economic][0]["T"], capacity)
    header_done = False
    for n, populations, overrides in config["cases"]:
        if not header_done:
            report(f"k(95%) per population; economic P = smallest P with k(95%) >= "
                   f"{config['level']:.0%} of the largest tested population")
            report()
            report(row(["N"] + [f"P={p}" for p in populations]
                       + ["econ. P", "T", "sparsity", "capacity"]))
            report(rule(len(populations) + 5))
            header_done = True
        cells, economic, t, capacity = rows[n]
        report(row([n] + cells + [economic, t, f"{100 * economic / n:.3f}%",
                                  f"{capacity:.3g}"]))
    report()
    report("Values equal to the largest tested k are lower bounds; "
           "\"<k\" means below the tested range.")
    report()


def test(config):
    report = Report()
    header(report, "Iterative decomposition of SHR bundles against an item store")
    base = config["base"]
    global CACHE
    CACHE = Cache()

    report("=== Bundle size, base configuration ===")
    report()
    detailed(report, {**base, "trials": config["detailed_trials"],
                      "bundle_sizes": config["detailed_sizes"]})

    for sweep_spec in config["sweeps"]:
        title, variants = sweep_spec[:2]
        overrides = sweep_spec[2] if len(sweep_spec) > 2 else {}
        compact(report, f"=== {title} ===", variants, {**base, **overrides})

    if "latency" in config:
        report("=== First-extraction latency ===")
        report()
        latency_report(report, base, config["latency"])

    if "sampling" in config:
        title, variants, overrides = config["sampling"]
        report(f"=== {title} ===")
        report()
        sampling_report(report, variants, {**base, **overrides})

    if "shared" in config:
        report("=== Shared elements: random vs disjoint items, single query ===")
        report()
        shared_elements(report, config["shared"])

    if "economic" in config:
        report("=== Economic SHR population (measured) ===")
        report()
        economic_population(report, base, config["economic"])

    report(f"Total compute time: {CACHE.total_seconds():.0f} s (single thread, "
           f"cache version {CACHE_VERSION})")
    report.save()


if __name__ == "__main__":
    sizes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20]
    large = sizes + [22, 24, 26, 28]
    large_dims = {"bundle_sizes": [16, 20, 24, 28, 32, 36, 40], "trials": 100}
    testconfig = {
        "base": {
            "N": 4000, "P": 10, "D": 0.8, "lexicon": 10000, "strategy": "always",
            "patience": 2, "decimate_above_P": True,
            "budget": 10, "trials": 200, "bundle_sizes": sizes, "seed": 1,
        },
        "detailed_trials": 500,
        "detailed_sizes": list(range(1, 21)),
        "sweeps": [
            ("Decimation factor D (N = 4000, P = 10)",
             [(f"D={d}", {"D": d}) for d in (1.0, 0.9, 0.8, 0.7, 0.6)]),
            ("Query strategy (N = 4000, P = 10, D = 0.8)",
             [(s, {"strategy": s}) for s in ("always", "on-empty", "fallback")]),
            ("Decimation factor D (N = 16000, P = 10)",
             [(f"D={d}", {"D": d}) for d in (0.9, 0.8, 0.7, 0.6)],
             {"N": 16000, "bundle_sizes": [8, 12, 16, 20, 24, 28, 32],
              "trials": 100}),
            ("Population P: margin P - T (N = 4000)",
             [(f"P={p}", {"P": p}) for p in (8, 9, 10, 11, 12, 15, 20)],
             {"bundle_sizes": large}),
            ("Dimension N, margin P - T = 3 (P = 10)",
             [(f"N={n}", {"N": n}) for n in (2000, 4000, 8000, 12000, 16000)],
             {"bundle_sizes": sizes + [24, 28, 32]}),
            ("Lexicon size (N = 4000, P = 10)",
             [(f"L={x}", {"lexicon": x}) for x in (1000, 10000, 30000)]),
            ("Margin at large dimensions",
             [(f"{n // 1000}k,P={p}", {"N": n, "P": p})
              for n in (8000, 12000, 16000) for p in (9, 10, 11, 12, 15)],
             large_dims),
        ],
        "latency": {
            "dimensions": [1000, 2000, 4000, 8000],
            "populations": [8, 9, 10, 11, 12, 15],
            "decimation": [0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            "pivot": (2, 0.5),
            "overrides": {"trials": 500, "budget": 32,
                          "bundle_sizes": list(range(1, 21))},
        },
        "sampling": (
            "Sampling with and without replacement",
            [("N=4000, P=10, without", {"N": 4000, "P": 10}),
             ("N=4000, P=10, with", {"N": 4000, "P": 10, "sampling": "with"}),
             ("N=16000, P=10, without", {"N": 16000, "P": 10}),
             ("N=16000, P=9, with", {"N": 16000, "P": 9, "sampling": "with"}),
             ("N=16000, P=10, with", {"N": 16000, "P": 10, "sampling": "with"}),
             ("N=16000, P=12, with", {"N": 16000, "P": 12, "sampling": "with"})],
            {"bundle_sizes": [4, 8, 12, 16, 20, 24], "trials": 100, "budget": 50},
        ),
        "economic": {
            "level": 0.9,
            "cases": [(4000, (9, 10, 11, 12, 15), {"bundle_sizes": large})]
                     + [(n, (9, 10, 11, 12, 15), large_dims)
                        for n in (8000, 12000, 16000)],
        },
        "shared": {
            "N": 4000, "D": 0.8, "trials": 300,
            "cases": [(10, (4, 8, 12, 16, 20)), (20, (8, 16, 20, 24, 28))],
        },
    }

    test(testconfig)
