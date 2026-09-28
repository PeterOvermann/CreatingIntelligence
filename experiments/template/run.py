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


# This template processes tabular data through the specified circuits.
# Result: Inputs and the corresponding outputs formatted side-by-side.

# Usage: python3 run.py [jsonfile] [datafile]


import sys
import os
import json
import tablib
from creating_intelligence import Circuit

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 run.py [jsonfile] [datafile]")
        sys.exit(1)

    jsonfile = sys.argv[1]
    datafile = sys.argv[2]

    with open(jsonfile, "r") as f:
        config = json.load(f)

    circuit_instance = Circuit(config)
    run = circuit_instance["function"]

    fmt = os.path.splitext(datafile)[1].lstrip('.')
    
    with open(datafile, "r") as f:
        dataset = tablib.Dataset().load(f.read(), format=fmt)
    
    if not dataset.headers and len(dataset) > 0:
        dataset.headers = dataset[0]
        del dataset[0]

    isPredictive = True

    results = []
    for row in dataset:
        output = run(*row)
        results.append((row, output))

    if not results:
        return

    num_inputs = len(results[0][0])
    num_outputs = len(results[0][1])

    if isPredictive:
        inputs = [r[0] for r in results]
        outputs = [r[1] for r in results]
        
        outputs = [tuple([None] * num_outputs)] + outputs[:-1]
        results = list(zip(inputs, outputs))

    headers = ["in"] * num_inputs + ["out"] * num_outputs
    print("| " + " | ".join(headers) + " |")
    print("|" + "|".join(["---"] * len(headers)) + "|")

    for row, output in results:
        combined = [str(item) for item in row] + [str(item) for item in output]
        print("| " + " | ".join(combined) + " |")

if __name__ == "__main__":
    main()