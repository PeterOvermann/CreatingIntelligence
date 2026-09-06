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

import time
import random
from creating_intelligence import Memory

def random_set(n, p):
    return sorted(random.sample(range(1, n + 1), p))

def random_association(config):
    return (
        random_set(*config["A_parameters"]),
        random_set(*config["B_parameters"])
    )

def add_noise(A, config_A, noise):
    n, p = config_A
    if noise == 0:
        return A
    elif noise > 0:
        random_ints = [random.randint(1, n) for _ in range(noise)]
        return sorted(list(set(A).union(random_ints)))
    else:
        return sorted(random.sample(A, len(A) + noise))

def overlap(A, B):
    return len(set(A).intersection(B))

def distance(A, B):
    return len(set(A).symmetric_difference(B))

def test(config):
    # Initialize memory via the configuration dictionary
    mem = Memory(config)
    
    NA, PA = mem["A_parameters"]
    NB, PB = mem["B_parameters"]
    
    memsize = (NB * NA * (NA - 1)) / 2
    size = config["batchsize"]
    
    print(f"Configuration: {config}")
    print(f"Memory: {mem}\n")
    
    cols = ["items", "writes/s", "density", "reads/s", "distance", "overlap"]
    print("|" + "".join([f"{col} ".rjust(12) + "|" for col in cols]))
    print("|" + "------------|" * len(cols))
    
    for iter_num in range(1, config["iterations"] + 1):
        data = [random_association(config) for _ in range(size)]
        
        t0 = time.perf_counter()
        for A, B in data:
            mem["store"](A, B)
        storetime = time.perf_counter() - t0
        
        inputs = [add_noise(A, config["A_parameters"], config["noise"]) for A, B in data]
        
        t1 = time.perf_counter()
        out = [mem["retrieve"](inp) for inp in inputs]
        retrievetime = time.perf_counter() - t1
        
        dist_total = sum(distance(out[i], data[i][1]) for i in range(size))
        overlap_total = sum(overlap(out[i], data[i][1]) for i in range(size))
        
        items = iter_num * size
        writes_s = round(size / storetime) if storetime > 0 else float('inf')
        density = mem["memorycount"]() / memsize
        reads_s = round(size / retrievetime) if retrievetime > 0 else float('inf')
        avg_dist = dist_total / size
        avg_overlap = overlap_total / size
        
        print(f"| {items:10d} | {writes_s:10.0f} | {density:10.6f} | {reads_s:10.0f} | {avg_dist:10.6f} | {avg_overlap:10.6f} |")

if __name__ == "__main__":
    # Unified configuration dictionary
    testconfig = {
        "A_parameters": (1000, 10),
        "B_parameters": (1001, 10),
        "batchsize": 50000,
        "iterations": 40,
        "noise": 0
    }
    
    test(testconfig)