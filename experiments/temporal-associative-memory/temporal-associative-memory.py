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


# Temporal Associative Memory: online sequence learning.
#
# The "temporal" associative memory component learns higher-order sequences
# and next-token prediction on the fly. This script feeds a random string of
# the characters A to Z through the circuit in TemporalAssociativeMemory.json
# for several iterations and reports the next-token prediction score of each
# iteration. Python port of TemporalAssociativeMemory.nb.
#
# Usage: python3 temporal-associative-memory.py [--length 2000] [--iterations 5]


import os
import json
import random
import string
import argparse
from creating_intelligence import Circuit


def prediction_score(dataset, predictions):
    # The prediction made at step t-1 is compared with the input at step t.
    # Like RotateRight in the notebook, the comparison wraps around: the last
    # prediction is compared with the first input. Only exact matches count,
    # so a superposition of several characters is scored as wrong.
    n = len(dataset)
    hits = sum(dataset[t] == predictions[t - 1] for t in range(n))
    return hits / n


def main():
    parser = argparse.ArgumentParser(
        description="Online sequence learning with temporal associative memory.")
    parser.add_argument("--length", type=int, default=2000,
                        help="length of the random string (default 2000)")
    parser.add_argument("--iterations", type=int, default=5,
                        help="number of passes through the string (default 5)")
    parser.add_argument("--seed", type=int, default=None,
                        help="seed for the random string (circuit not seeded)")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "TemporalAssociativeMemory.json")

    with open(json_path, "r") as f:
        config = json.load(f)

    circuit_instance = Circuit(config)
    run = circuit_instance["function"]

    # Dataset: a random string of characters A to Z
    chars = list(string.ascii_uppercase)
    dataset = random.Random(args.seed).choices(chars, k=args.length)

    print("".join(dataset))
    print()

    # Prediction score. The circuit learns continuously, so every iteration
    # is both a training pass and a test of what was learned before.
    for i in range(1, args.iterations + 1):
        predictions = [run(token)[0] for token in dataset]
        score = prediction_score(dataset, predictions)
        print(f"iteration = {i}, prediction score = {score:.3f}")


if __name__ == "__main__":
    main()
