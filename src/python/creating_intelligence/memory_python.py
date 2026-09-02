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

import math
import numpy as np
from itertools import combinations

def Memory(config: dict) -> dict:
    # Extract hyperparameters
    NA, PA = config["A_parameters"]
    NB, PB = config["B_parameters"]
    
    # Memory capacity, needed for default threshold calculation
    if NA == NB and PA == PB:
        capacity = round((math.log(2.0) * NA * (NA - 1) * (NA - 2)) / 
                         (PA * (PA - 1) * (PA - 2)))
    else:
        capacity = round((math.log(2.0) * NA * (NA - 1) * NB) / 
                         (PA * (PA - 1) * PB))
        
    # Default pattern matching threshold
    T = 1
    while (T < PA and 
           (capacity**2 * math.comb(PA, T) * 
            math.comb(NA - PA, PA - T) / 
            math.comb(NA, PA)) >= 1):
        T += 1
        
    # User-defined (scaled) threshold via get()
    if config.get("threshold") is not None:
        T = round(config["threshold"] * PA)
    
    T = max(2, T)

    # Initialize enclosed memory dictionary and zero array
    mem = {}
    zero = np.zeros(NB + 1, dtype=np.int8)

    def store(A, B=None):
        if B is None:
            B = A
            
        v = zero.copy()
        v[B] = 1 
        
        for pair in combinations(A, 2):
            key = tuple(sorted(pair))
            
            if key not in mem:
                mem[key] = v.copy() 
            else:
                mem[key] = np.bitwise_or(mem[key], v)

    def retrieve(A):
        X = list(A)  

        while True:
            P = len(X)
            if P < T:
                return []

            Ri = np.zeros((P, NB + 1), dtype=np.int32)

            for i, j in combinations(range(P), 2):
                key = tuple(sorted([X[i], X[j]]))
                v = mem.get(key, zero)
                Ri[i] += v
                Ri[j] += v

            R = np.sum(Ri, axis=0) // 2

            R_valid = R[1:] 
            sorted_R = np.sort(R_valid)
            
            t_val = sorted_R[-PB] if PB <= len(sorted_R) else sorted_R[0]
            t = max(1, t_val)

            if t < (T * (T - 1)) / 2:
                return []
            
            Y = [i for i in range(1, NB + 1) if R[i] >= t]
            w = np.sum(Ri[:, Y], axis=1)

            ws = np.sort(w)
            h = P
            
            while h > 0 and ws[-h] < len(Y) * (h - 1):
                h -= 1

            if h < T:
                return []

            cutoff = ws[-h]
            new_X = [X[i] for i in range(P) if w[i] >= cutoff]

            if h == T and h < len(new_X):
                return []

            if len(new_X) == P:
                return Y

            X = new_X

    def memorycount():
        return sum(np.sum(v) for v in mem.values())

    def clear():
        mem.clear()
        
    return  {
        "A_parameters": (NA, PA),
        "B_parameters": (NB, PB),
        "T": T,
        "store": store,
        "retrieve": retrieve,
        "clear": clear,
        "memorycount": memorycount,
        "backend": "python"
    }
    