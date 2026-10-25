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
Separating known from unknown: retrieval from known and unknown queries as a
function of memory density, for auto-associations (A -> A) and
hetero-associations (A -> B) stored in the same memory configuration.

Random associations are stored until the measured memory density reaches each
target. Two query classes then receive identical perturbations: a known query
is a stored pattern A, an unknown query is a fresh random set of the same
population. A negative noise value drops that many random elements, a positive
value adds exactly that many distinct elements from outside the pattern.

Known queries count as correct (the stored output), empty, or false (any other
result). Unknown queries count as rejected (empty result), justified, or
hallucinated. A non-empty result is justified if the query actually contains
at least T elements of a stored input and the result is that input's stored
output: the memory then follows its own matching criterion, which large random
queries satisfy by chance. Any other non-empty result is a hallucination.

The "chance" column is the analytical number of chance matches among the
unknown queries of a row: the number of stored inputs times the hypergeometric
probability that a random query of the given size shares at least T elements
with a stored input. It counts the queries that could be answered with a
justified result, not a prediction of how many are: a query sharing only T
elements with a stored input but carrying many other elements is usually
rejected. "95% bound" is the one-sided 95% upper confidence bound
on the hallucination rate (Clopper-Pearson).
"""

import os
import math
import time
import random
import platform
import numpy as np
from scipy.stats import beta
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


def random_set(rng, n, p):
    return sorted(rng.sample(range(1, n + 1), p))


def perturb(rng, pattern, n, noise):
    """Drop -noise random elements (noise < 0) or add exactly noise distinct
    elements from outside the pattern (noise > 0)."""
    if noise < 0:
        return sorted(rng.sample(pattern, len(pattern) + noise))
    inside = set(pattern)
    extra = set()
    while len(extra) < noise:
        x = rng.randint(1, n)
        if x not in inside:
            extra.add(x)
    return sorted(inside | extra)


def density(mem, n):
    return mem["memorycount"]() / (n * n * (n - 1) / 2)


def fill_to_density(mem, rng, n, p, target, inputs, outputs, auto):
    """Store random associations until the measured density reaches target.
    Batches shrink near the target, so the overshoot stays below 0.001."""
    gain = None
    while (current := density(mem, n)) < target:
        if gain is None:
            batch = 1000
        else:
            batch = max(10, min(20000, int(0.5 * (target - current) / gain)))
        before = current
        for _ in range(batch):
            a = random_set(rng, n, p)
            b = a if auto else random_set(rng, n, p)
            mem["store"](a, b)
            inputs.append(a)
            outputs.append(b)
        gain = max((density(mem, n) - before) / batch, 1e-12)


def expected_justified(n, p, t, size, count):
    """Expected number of stored random inputs sharing >= t elements with a
    random query of the given size."""
    hits = sum(math.comb(size, k) * math.comb(n - size, p - k)
               for k in range(t, min(size, p) + 1))
    return count * hits / math.comb(n, p)


def is_justified(query, result, n, t, input_array, outputs):
    """True if the query shares >= t elements with a stored input whose
    stored output equals the result."""
    mask = np.zeros(n + 1, dtype=bool)
    mask[query] = True
    overlap = mask[input_array].sum(axis=1)
    return any(outputs[i] == result for i in np.flatnonzero(overlap >= t))


def upper_bound(k, total, confidence=0.95):
    """One-sided Clopper-Pearson upper bound for k events in total trials."""
    return 1.0 if k >= total else float(beta.ppf(confidence, k + 1, total - k))


def known_trial(mem, rng, inputs, outputs, n, noise, queries):
    correct = empty = false = 0
    for _ in range(queries):
        i = rng.randrange(len(inputs))
        out = mem["retrieve"](perturb(rng, inputs[i], n, noise))
        if not out:
            empty += 1
        elif out == outputs[i]:
            correct += 1
        else:
            false += 1
    return correct, empty, false


def unknown_trial(mem, rng, input_array, outputs, n, p, noise, queries):
    rejected = justified = hallucinated = 0
    for _ in range(queries):
        query = perturb(rng, random_set(rng, n, p), n, noise)
        out = mem["retrieve"](query)
        if not out:
            rejected += 1
        elif is_justified(query, out, n, mem["T"], input_array, outputs):
            justified += 1
        else:
            hallucinated += 1
    return rejected, justified, hallucinated


COLUMNS = [("noise", 6), ("correct", 8), ("empty", 6), ("false", 6),
           ("rejected", 9), ("justified", 9), ("chance", 9),
           ("halluc.", 8), ("95% bound", 9)]


def row(values):
    return "|" + "".join(f" {v:>{w}} |" for v, (_, w) in zip(values, COLUMNS))


def rule():
    return "|" + "".join("-" * (w + 2) + "|" for _, w in COLUMNS)


def test(config):
    report = Report()
    n, p = config["N"], config["P"]
    kq, uq = config["known_queries"], config["unknown_queries"]
    mem = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
    header(report, f"Memory at {n}/{p}, matching threshold T = {mem['T']}, "
                   f"{kq} known and {uq} unknown queries per row")
    mem["clear"]()
    report("Columns correct/empty/false: known queries. Columns rejected/"
           "justified/halluc.: unknown queries.")
    report("chance: analytical number of unknown queries sharing >= T elements "
           "with a stored input.")
    report()

    for mode in config["modes"]:
        auto = mode == "auto"
        rng = random.Random(config["seed"])
        mem = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
        t = mem["T"]
        report(f"=== {'Auto-associations A -> A' if auto else 'Hetero-associations A -> B'} ===")
        report()
        inputs, outputs = [], []
        for target in config["densities"]:
            fill_to_density(mem, rng, n, p, target, inputs, outputs, auto)
            rho = density(mem, n)
            input_array = np.array(inputs)
            report(f"Density {rho:.3f} ({len(inputs)} stored patterns)")
            report()
            report(row([c for c, _ in COLUMNS]))
            report(rule())
            for noise in config["noise"]:
                c, e, f = known_trial(mem, rng, inputs, outputs, n, noise, kq)
                r, j, h = unknown_trial(mem, rng, input_array, outputs, n, p,
                                        noise, uq)
                exp = uq * expected_justified(n, p, t, p + noise, len(inputs))
                label = "clean" if noise == 0 else f"{noise:+d}"
                report(row([label, c, e, f, r, j, f"{exp:.2f}", h,
                            f"{upper_bound(h, uq):.1e}"]))
            report()
        mem["clear"]()
    report.save()


if __name__ == "__main__":
    testconfig = {
        "N": 1000,
        "P": 10,
        "modes": ["auto", "hetero"],
        "densities": [0.25, 0.375, 0.5],
        "noise": [0, -1, -2, -3, 5, 10, 20, 30],
        "known_queries": 1000,
        "unknown_queries": 20000,
        "seed": 1,
    }

    test(testconfig)
