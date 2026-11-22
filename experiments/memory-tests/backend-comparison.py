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
Side-by-side comparison of the two memory backends: pure Python
(memory_python) and C via ctypes (memory_c_ffi).

Both memories receive the same random auto-associations until the measured
density reaches the target, then the same queries. The script checks that

  - both compute the same matching threshold T (here and on a small grid),
  - memorycount() is identical after filling,
  - retrieval gives the same results for exact inputs, additive noise,
    subtractive noise and random (unknown) inputs.

Each retrieval test reports outcome counts per backend and the number of
queries on which both backends returned exactly the same output.
Results are printed and written to backend-comparison.txt next to this file.

How both backends are active at the same time
---------------------------------------------
The MEMORY_BACKEND environment variable is only read once, by the package's
__init__.py, to decide which backend is exported as
creating_intelligence.Memory. The backends themselves are ordinary
submodules, each with its own Memory() factory, and importing one never
blocks the other. So instead of using creating_intelligence.Memory, this
script imports both submodules directly:

    from creating_intelligence import memory_python, memory_c_ffi
    mem_py = memory_python.Memory(config)
    mem_c  = memory_c_ffi.Memory(config)

MEMORY_BACKEND has no effect here. If the C library cannot be loaded, the
import of memory_c_ffi fails with an error instead of silently falling back
to Python, which is what a comparison test should do.
"""

import os
import time
import random
import platform
from creating_intelligence import memory_python, memory_c_ffi


BACKENDS = {"python": memory_python.Memory, "c_ffi": memory_c_ffi.Memory}


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
    report(f"Backends: {memory_python.__name__}, {memory_c_ffi.__name__}")
    report(f"Date: {time.strftime('%Y-%m-%d')}")
    report()
    report(title)
    report()


def check(ok):
    return "ok" if ok else "MISMATCH"


def random_set(rng, n, p):
    return sorted(rng.sample(range(1, n + 1), p))


def add_exact_noise(rng, pattern, n, size):
    """Union of the pattern with exactly `size` distinct elements outside it."""
    inside = set(pattern)
    noise = set()
    while len(noise) < size:
        x = rng.randint(1, n)
        if x not in inside:
            noise.add(x)
    return sorted(inside | noise)


def remove_elements(rng, pattern, size):
    """The pattern with `size` randomly chosen elements removed."""
    return sorted(rng.sample(pattern, len(pattern) - size))


def density(mem, n):
    return int(mem["memorycount"]()) / (n * n * (n - 1) / 2)


def fill_to_density(mems, rng, n, p, target):
    """Store the same random auto-associations in every memory until the
    density of the first one reaches target. Batches shrink near the target,
    so the overshoot stays small. Returns the stored patterns."""
    stored = []
    gain = None
    while (current := density(mems[0], n)) < target:
        if gain is None:
            batch = 1000
        else:
            batch = max(10, min(20000, int(0.5 * (target - current) / gain)))
        for _ in range(batch):
            x = random_set(rng, n, p)
            for mem in mems:
                mem["store"](x)
            stored.append(x)
        gain = max((density(mems[0], n) - current) / batch, 1e-12)
    return stored


def classify(out, expected):
    if not out:
        return "empty"
    return "correct" if out == expected else "false"


def compare_retrieval(mems, queries, examples):
    """Run (query, expected) pairs on all memories. expected=None means the
    correct answer is an empty result (unknown input). The first `examples`
    queries are returned with their outputs for display."""
    counts = {name: {"correct": 0, "empty": 0, "false": 0} for name in mems}
    same = 0
    shown = []
    for query, expected in queries:
        outs = {name: sorted(mem["retrieve"](query)) for name, mem in mems.items()}
        if len(shown) < examples:
            shown.append((query, expected, outs))
        for name, out in outs.items():
            if expected is None:
                counts[name]["correct" if not out else "false"] += 1
            else:
                counts[name][classify(out, expected)] += 1
        same += len({tuple(o) for o in outs.values()}) == 1
    return counts, same, shown


def show_examples(report, label, shown):
    """Literal queries and outputs, one line each, backends side by side."""
    report(f"{label}:")
    for query, expected, outs in shown:
        report(f"  query   {fmt(query)}")
        if expected is not None and expected != query:
            report(f"  stored  {fmt(expected)}")
        for name, out in outs.items():
            report(f"  {name:7s} {fmt(out)}")
        report()


def fmt(elements):
    return " ".join(f"{x:>3}" for x in elements) if elements else "(empty)"


def row(values, width=12):
    return "|" + "".join(f" {v:>{width}} |" for v in values)


def rule(count, width=12):
    return "|" + ("-" * (width + 2) + "|") * count


def threshold_grid(report, grid):
    """Compare T for a few (NA, PA, NB, PB) configurations."""
    report("Threshold T on a grid of configurations")
    report()
    report(row(["NA/PA", "NB/PB", "T python", "T c_ffi", "check"]))
    report(rule(5))
    all_ok = True
    for na, pa, nb, pb in grid:
        config = {"A_parameters": (na, pa), "B_parameters": (nb, pb)}
        ts = {}
        for name, factory in BACKENDS.items():
            mem = factory(config)
            ts[name] = mem["T"]
            mem["clear"]()      # the C backend frees its memory here
        ok = ts["python"] == ts["c_ffi"]
        all_ok &= ok
        report(row([f"{na}/{pa}", f"{nb}/{pb}", ts["python"], ts["c_ffi"], check(ok)]))
    report()
    return all_ok


def test(config):
    report = Report()
    n, p, q = config["N"], config["P"], config["queries"]
    rng = random.Random(config["seed"])
    mem_config = {"A_parameters": (n, p), "B_parameters": (n, p)}
    mems = {name: factory(mem_config) for name, factory in BACKENDS.items()}
    py, c = mems["python"], mems["c_ffi"]

    header(report, f"Python vs C backend, auto-associative memory at {n}/{p}, "
                   f"target density {config['density']}, {q} queries per test")
    results = []

    # 1. Threshold T
    ok = py["T"] == c["T"]
    results.append(ok)
    report(f"Threshold T: python {py['T']}, c_ffi {c['T']}  {check(ok)}")
    report()

    # 2. Fill both memories with the same patterns, compare memorycount
    t0 = time.perf_counter()
    stored = fill_to_density([c, py], rng, n, p, config["density"])
    fill_time = time.perf_counter() - t0
    count_py, count_c = int(py["memorycount"]()), int(c["memorycount"]())
    ok = count_py == count_c
    results.append(ok)
    report(f"Filled with {len(stored)} patterns in {fill_time:.0f} s, "
           f"density {density(c, n):.4f}")
    report(f"memorycount: python {count_py}, c_ffi {count_c}  {check(ok)}")
    report()

    # 3. Retrieval tests: same queries for both backends
    def known(make_query):
        targets = [stored[rng.randrange(len(stored))] for _ in range(q)]
        return [(make_query(x), x) for x in targets]

    tests = [
        ("exact", known(lambda x: x)),
        (f"+{p} noise", known(lambda x: add_exact_noise(rng, x, n, p))),
        ("-2 noise", known(lambda x: remove_elements(rng, x, 2))),
        (f"random {p}-{2 * p}",
         [(random_set(rng, n, rng.randint(p, 2 * p)), None) for _ in range(q)]),
    ]

    report("Retrieval (random inputs: correct = empty result)")
    report()
    report(row(["test", "backend", "correct", "empty", "false", "same out"]))
    report(rule(6))
    examples = []
    for label, queries in tests:
        counts, same, shown = compare_retrieval(mems, queries, config["examples"])
        examples.append((label, shown))
        ok = same == len(queries)
        results.append(ok)
        for i, name in enumerate(mems):
            k = counts[name]
            last = f"{same}/{len(queries)}" if i == 0 else check(ok)
            report(row([label if i == 0 else "", name,
                        k["correct"], k["empty"], k["false"], last]))
    report()

    report(f"Example retrievals (first {config['examples']} queries of each test)")
    report()
    for label, shown in examples:
        show_examples(report, label, shown)

    # 4. Threshold on a small grid, including hetero-associative configurations
    results.append(threshold_grid(report, config["grid"]))

    report(f"Overall: {'all checks passed' if all(results) else 'MISMATCHES FOUND'}")
    report.save()

    for mem in mems.values():
        mem["clear"]()


if __name__ == "__main__":
    testconfig = {
        "N": 1000,
        "P": 10,
        "density": 0.1,
        "queries": 1000,
        "examples": 2,          # literal outputs shown per retrieval test
        "seed": 1,
        # (NA, PA, NB, PB) for the threshold comparison
        "grid": [
            (1000, 10, 1000, 10),
            (1000, 20, 1000, 20),
            (500, 10, 500, 10),
            (2000, 10, 2000, 10),
            (1000, 10, 1001, 10),
            (1000, 10, 500, 20),
        ],
    }

    test(testconfig)
