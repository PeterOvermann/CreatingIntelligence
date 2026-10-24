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
Noise tolerance of auto-associative memory retrieval as a function of memory
density.

Random auto-associations are stored until the measured memory density reaches
each target. Stored patterns are then retrieved from queries with exactly
`noise` additional distinct elements drawn from outside the pattern. Each
query counts as correct (the pattern itself), empty, or false (any other
result). The SNR column is the independent-bit estimate of the first output
estimate's signal-to-noise ratio.
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


def test(config):
    report = Report()
    n, p, queries = config["N"], config["P"], config["queries"]
    rng = random.Random(config["seed"])
    mem = Memory({"A_parameters": (n, p), "B_parameters": (n, p)})
    header(report, f"Auto-associative memory at {n}/{p}, matching threshold "
                   f"T = {mem['T']}, exact additive noise, {queries} queries per row")

    stored = []
    for target in config["densities"]:
        fill_to_density(mem, rng, n, p, target, stored)
        rho = density(mem, n)
        report(f"Density {rho:.3f} ({len(stored)} stored patterns)")
        report()
        report(row(["noise", "SNR", "correct", "empty", "false"]))
        report(rule(5))
        points = []
        for noise in config["noise"]:
            c, e, f = noise_trial(mem, rng, stored, n, noise, queries)
            points.append((noise, c / queries))
            report(row([noise, f"{snr_estimate(p, noise, rho):.2f}", c, e, f]))
        report()
        for fraction in (0.9, 0.5):
            z = crossover(points, fraction)
            text = f"{z:.1f}" if z is not None else "outside tested range"
            report(f"Noise at {int(fraction * 100)}% correct: {text}")
        report()
    report.save()


if __name__ == "__main__":
    testconfig = {
        "N": 1000,
        "P": 10,
        "densities": [0.2, 0.3, 0.4, 0.45],
        "noise": [10, 20, 30, 40, 50, 60],
        "queries": 500,
        "seed": 1,
    }

    test(testconfig)
