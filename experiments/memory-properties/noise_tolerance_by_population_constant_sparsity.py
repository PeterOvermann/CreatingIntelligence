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
Noise tolerance of auto-associative memory retrieval as a function of the
population P. The sparsity P/N is held constant, which keeps the nominal capacity
nearly unchanged while the memory size grows with N^3.

For each configuration, random auto-associations are stored until the
measured memory density reaches the target. Stored patterns are then
retrieved from queries with exactly `noise` additional distinct elements
drawn from outside the pattern. The summary reports the noise levels at which
90 and 50 percent of queries are answered correctly (linear interpolation),
and the independent-bit SNR estimate at the 90 percent point.
"""

import os
import sys
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


def density(mem, n):
    return mem["memorycount"]() / (n * n * (n - 1) / 2)


def fill_to_density(mem, rng, n, p, target, stored):
    """Store random auto-associations until the measured density reaches target.
    Batches shrink near the target, so the overshoot stays below 0.001."""
    gain = None
    while (current := density(mem, n)) < target:
        if gain is None:
            batch = 1000
        else:
            batch = max(10, min(20000, int(0.5 * (target - current) / gain)))
        before = current
        for _ in range(batch):
            x = random_set(rng, n, p)
            mem["store"](x)
            stored.append(x)
        gain = max((density(mem, n) - before) / batch, 1e-12)


def snr_estimate(p, noise, rho):
    """Signal-to-noise ratio of the first output estimate (independent-bit model)."""
    pairs = noise * (2 * p + noise - 1) / 2
    return math.comb(p, 2) / math.sqrt(pairs * rho * (1 - rho))


def noise_trial(mem, rng, stored, n, noise, queries):
    """Retrieve stored patterns with added noise; count outcomes."""
    correct = empty = false = 0
    for _ in range(queries):
        target = stored[rng.randrange(len(stored))]
        out = mem["retrieve"](add_exact_noise(rng, target, n, noise))
        if not out:
            empty += 1
        elif out == target:
            correct += 1
        else:
            false += 1
    return correct, empty, false


def crossover(points, fraction):
    """Noise level at which the correct fraction falls below `fraction` (linear interpolation)."""
    for (z0, a0), (z1, a1) in zip(points, points[1:]):
        if a0 >= fraction > a1:
            return z0 + (z1 - z0) * (a0 - fraction) / (a0 - a1)
    return None


def row(values, width=11):
    return "|" + "".join(f" {v:>{width}} |" for v in values)


def rule(count, width=11):
    return "|" + ("-" * (width + 2) + "|") * count


def capacity(n, p):
    return math.log(2) * n * (n - 1) * (n - 2) / (p * (p - 1) * (p - 2))


def test(config):
    report = Report()
    queries = config["queries"]
    rng = random.Random(config["seed"])
    header(report, f"Auto-associative memory, {config['label']}, target density "
                   f"{config['density']}, exact additive noise, {queries} queries per row")

    summary = []
    for n, p, grid in config["configurations"]:
        mem = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
        stored = []
        fill_to_density(mem, rng, n, p, config["density"], stored)
        rho = density(mem, n)
        report(f"N = {n}, P = {p}, T = {mem['T']}, nominal capacity "
               f"{capacity(n, p):.0f}, {len(stored)} stored patterns, density {rho:.3f}")
        report()
        report(row(["noise", "SNR", "correct", "empty", "false"]))
        report(rule(5))
        points = []
        for noise in grid:
            c, e, f = noise_trial(mem, rng, stored, n, noise, queries)
            points.append((noise, c / queries))
            report(row([noise, f"{snr_estimate(p, noise, rho):.2f}", c, e, f]))
        report()
        z90, z50 = crossover(points, 0.9), crossover(points, 0.5)
        snr90 = snr_estimate(p, z90, rho) if z90 is not None else None
        summary.append((n, p, z90, z50, snr90))
        mem["clear"]()

    fmt = lambda v, spec: format(v, spec) if v is not None else "n/a"
    report("Summary")
    report()
    report(row(["N", "P", "noise @90%", "noise @50%", "SNR @90%"]))
    report(rule(5))
    for n, p, z90, z50, snr90 in summary:
        report(row([n, p, fmt(z90, ".1f"), fmt(z50, ".1f"), fmt(snr90, ".2f")]))
    report()
    n0, p0, z0, _, _ = summary[0]
    if z0 is not None:
        for n, p, z, _, _ in summary[1:]:
            if z is not None:
                exponent = math.log(z / z0) / math.log(p / p0)
                report(f"Scaling exponent of noise @90% from P = {p0} to P = {p}: {exponent:.2f}")
    report.save()


if __name__ == "__main__":
    testconfig = {
        "label": "constant sparsity P/N = 0.01",
        "density": 0.3,
        "configurations": [
            (1000, 10, [20, 30, 40, 50, 60, 70]),
            (1500, 15, [50, 70, 90, 110, 130, 150]),
            (2000, 20, [80, 110, 140, 170, 200, 240]),
        ],
        "queries": 500,
        "seed": 1,
    }

    test(testconfig)
