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

This package employs a standardized plugin mechanism for circuit components,
encoders (preprocessing), decoders (postprocessing), circuit embedding mechanisms,
and auto-associative update rules.

Plugins are defined via factory functions that take a dictionary as input
and dispatch a dictionary, using closures encapsulate stateful evaluation functions.

The function names match the corresponding value strings in the JSON dataflow description,
for example {"component": "auto", "plugin": "replacement", ...}

Users can patch custom plugins into the circuits namespace via:

import creating_intelligence
from myplugins import mycomponent
circuits.mycomponent = mycomponent 


"""

## -----------------------------------------------------------------------------
## Dependencies
## -----------------------------------------------------------------------------

import itertools
import math
import sys
import os
import json

from collections import Counter

import numpy as np
import scipy.sparse as sp

import networkx as nx
import matplotlib.pyplot as plt


from creating_intelligence import Memory

   
    
## -----------------------------------------------------------------------------
## Global RNG for the circuits module
## -----------------------------------------------------------------------------

rng = np.random.default_rng()


## -----------------------------------------------------------------------------
## Set / Multiset Utilities
## -----------------------------------------------------------------------------


def multiset(u):
    """
    Summates excitatory and inhibitory signals.
    Outputs a net multiset. No element will exist as both positive and negative.
    """
    if not isinstance(u, list):
        u = [u]
        
    # Flatten nested structures if necessary
    flat_u = []
    def _flatten(items):
        for item in items:
            if isinstance(item, list):
                _flatten(item)
            else:
                flat_u.append(item)
    _flatten(u)
            
    tally = Counter()
    pos = [x for x in flat_u if x > 0]
    neg = [-x for x in flat_u if x < 0]
    
    tally.update(pos)
    tally.subtract(neg)
    
    result = []
    for k, v in tally.items():
        if v > 0:
            result.extend([k] * v)
        elif v < 0:
            result.extend([-k] * abs(v))
            
    return sorted(result)


def resolve_normal(x):
    """Applies graded inhibition, drops negatives, squashes excitatory survivors."""
    ae = [i for i in x if i > 0]
    ai = [-i for i in x if i < 0]
    
    if not ai: # Fast path for pure boolean
        return sorted(list(set(ae)))
        
    counts_e = Counter(ae)
    counts_i = Counter(ai)
    
    survivors = [k for k, v in counts_e.items() if v > counts_i.get(k, 0)]
    return sorted(survivors)




def resolve_graded(x):
    """Applies graded inhibition, drops negatives, keeps excitatory survivors."""
    ae = [i for i in x if i > 0]
    ai = [-i for i in x if i < 0]
    
    if not ai: # Fast path for pure multisets
        return sorted(ae)
        
    counts_e = Counter(ae)
    counts_i = Counter(ai)
    
    result = []
    for k, v in counts_e.items():
        surviving_count = max(0, v - counts_i.get(k, 0))
        result.extend([k] * surviving_count)
        
    return sorted(result)




def multiset_block_join(blocks, dims):
    """Transparently joins multisets. Preserves duplicates and negative signs."""
    offsets = list(itertools.accumulate([0] + dims[:-1]))
    
    result = []
    for sublist, offset in zip(blocks, offsets):
        for val in sublist:
            sign = 1 if val > 0 else -1 if val < 0 else 0
            shifted = sign * (abs(val) + offset)
            result.append(shifted)
            
    return sorted(result)




def multiset_block_split(A, dims):
    """Transparently splits a joined multiset back into its original blocks."""
    limits = list(itertools.accumulate([0] + dims))
    bounds = list(zip(limits[:-1], limits[1:]))
    
    split_blocks = []
    for b_start, b_end in bounds:
        chunk = []
        for val in A:
            if b_start < abs(val) <= b_end:
                sign = 1 if val > 0 else -1 if val < 0 else 0
                restored = sign * (abs(val) - b_start)
                chunk.append(restored)
        split_blocks.append(chunk)
        
    return split_blocks




def multiset_block_join_normal(blocks, dims):
    """
    Join blocks with dimensions into a single list. 
    Applies graded inhibition and drops inhibitory elements. Preserves multisets.
    """
    offsets = list(itertools.accumulate([0] + dims[:-1]))
    
    ae = []
    ai = []
    for sublist, offset in zip(blocks, offsets):
        for val in sublist:
            shifted_abs = abs(val) + offset
            if val > 0:
                ae.append(shifted_abs)
            elif val < 0:
                ai.append(shifted_abs)
                
    counts_e = Counter(ae)
    counts_i = Counter(ai)
    
    net_excitatory = []
    for k, v in counts_e.items():
        surviving_count = max(0, v - counts_i.get(k, 0))
        net_excitatory.extend([k] * surviving_count)
        
    return sorted(net_excitatory)






def resolve_block_join_normal(blocks, dims):
    """
    Applies graded subtraction, drops negatives, and squashes the survivors. 
    Outputs a flat, Boolean excitatory set.
    """
    offsets = list(itertools.accumulate([0] + dims[:-1]))
    
    ae = []
    ai = []
    for sublist, offset in zip(blocks, offsets):
        for val in sublist:
            shifted_abs = abs(val) + offset
            if val > 0:
                ae.append(shifted_abs)
            elif val < 0:
                ai.append(shifted_abs)
                
    counts_e = Counter(ae)
    counts_i = Counter(ai)
    
    survivors = [k for k, v in counts_e.items() if v > counts_i.get(k, 0)]
    return sorted(survivors)





## -----------------------------------------------------------------------------
## Memory Properties 
## -----------------------------------------------------------------------------




def memory_capacity(A_params, B_params):
    NA, PA = A_params
    NB, PB = B_params
    if NA == NB and PA == PB:
        return round((math.log(2.0) * NB * (NA - 1) * (NA - 2)) / (PB * (PA - 1) * (PA - 2)))
    else:
        return round((math.log(2.0) * NB * NA * (NA - 1)) / (PB * PA * (PA - 1)))




def matching_threshold(A_params, B_params):
    NA, PA = A_params
    NB, PB = B_params
    
    if PA <= 2 or PB <= 2:
        return 0
        
    cap = memory_capacity(A_params, B_params)
    T = 1
    
    while T < PA and (cap**2 * math.comb(PA, T) * math.comb(NA - PA, PA - T) / math.comb(NA, PA)) >= 1:
        T += 1
        
    return T


    
    
## -----------------------------------------------------------------------------
## Encoders and decoders    
## -----------------------------------------------------------------------------
    
    
# Shared state structure keyed by (N, P) tuple
# By design, circuits with identical hyperparameters (N, P) share encoder/decoder instances.

circuit_codec_lexicon = {}

def codec(config):
    """General-purpose SHR encoder/decoder for symbolic expressions."""
    
    # Extract hyperparameters from config
    hyperparameters = config.get("hyperparameters", [0, 0])
    n, p = hyperparameters[0], hyperparameters[1]
    lex_key = (n, p)
    
    # Initialize global hash table if missing for these dimensions
    if lex_key not in circuit_codec_lexicon:
        circuit_codec_lexicon[lex_key] = {None: []}
        
    lex = circuit_codec_lexicon[lex_key]
    
    # Use auto-associative pattern matching threshold
    T = matching_threshold((n, p), (n, p))
    
    def f(expr):
        # Encoding logic
        if config.get("component") == "input":
            if isinstance(expr, list):
                # Bundle multiple tokens
                bundled = []
                for e in expr:
                    res = f(e)
                    if res:
                        bundled.extend(res)
                return sorted(list(set(bundled)))
            
            if expr not in lex:
                # 1-based indexing for native arrays
                sampled = rng.choice(range(1, n + 1), size=p, replace=False)
                lex[expr] = sorted(sampled.tolist())
                
            return lex[expr]
            
        # Decoding logic
        if not expr:
            return None
            
        overlaps = {k: len(set(v).intersection(expr)) 
                    for k, v in lex.items() if k is not None}
                    
        result = [k for k, overlap in overlaps.items() if overlap >= T]
        
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            return sorted(result)

    def clear():
        lex.clear()
        lex[None] = []
        
    return {
        "label": "SYM",
        "function": f,
        "clear": clear
    }
        
## -----------------------------------------------------------------------------
        

# Shared state structures keyed by (n, p) tuple
circuit_category_lexicon = {}

def category(config):
    hyperparameters = config.get("hyperparameters", [0, 0])
    n, p = hyperparameters[0], hyperparameters[1]
    lex_key = (n, p)
    
    K = config.get("categories", n // p if p > 0 else 0)
    if K * p > n:
        raise ValueError(f"Category encoder requires dimension {K * p} or greater.")
        
    partitionsize = n // K if K > 0 else 0
    
    if lex_key not in circuit_category_lexicon:
        circuit_category_lexicon[lex_key] = {None: []}
        
    lex = circuit_category_lexicon[lex_key]
    T = matching_threshold((n, p), (n, p))
    
    def f(expr):
        if config.get("component") == "input":
            if not isinstance(expr, int) or expr < 0 or expr >= K:
                return []
            
            if expr not in lex:
                # 1-based indexing for native arrays
                start = partitionsize * expr + 1
                end = start + partitionsize
                lex[expr] = list(range(start, end))
                
            pool = lex[expr]
            sample_size = min(p, len(pool))
            return sorted(rng.choice(pool, size=sample_size, replace=False).tolist())
            
        if not expr:
            return None
            
        overlaps = {k: len(set(v).intersection(expr)) 
                    for k, v in lex.items() if k is not None}
                    
        result = [k for k, overlap in overlaps.items() if overlap >= T]
        
        if len(result) == 0:
            return None
        elif len(result) == 1:
            return result[0]
        else:
            return sorted(result)
            
    def clear():
        lex.clear()
        lex[None] = []
        
    return {
        "label": "CAT",
        "function": f,
        "clear": clear
    }


## -----------------------------------------------------------------------------


circuit_binning_lexicon = {}

def binning(config):
    hyperparameters = config.get("hyperparameters", [0, 0])
    n, p = hyperparameters[0], hyperparameters[1]
    lex_key = (n, p)
    
    if lex_key not in circuit_binning_lexicon:
        circuit_binning_lexicon[lex_key] = {None: []}
        
    lex = circuit_binning_lexicon[lex_key]
    T = matching_threshold((n, p), (n, p))
    
    if config.get("component") == "input":
        raise ValueError("binning cannot be used as an encoder.")
        
    def f(expr):
        if not expr:
            return 0
            
        overlaps = {k: len(set(v).intersection(expr)) 
                    for k, v in lex.items() if k is not None}
                    
        bins = [k for k, overlap in overlaps.items() if overlap >= T]
        
        if len(bins) == 0:
            new_bin = len(lex)
            lex[new_bin] = expr
            return new_bin
        elif len(bins) == 1:
            return bins[0]
        else:
            return sorted(bins)
            
    def clear():
        lex.clear()
        lex[None] = []
        
    return {
        "label": "BIN",
        "function": f,
        "clear": clear
    }


## -----------------------------------------------------------------------------


circuit_vectorencoder_matrices = {}

def vectorencoder(config):
    hyperparameters = config.get("hyperparameters", [0, 0])
    n, p = hyperparameters[0], hyperparameters[1]
    key = (n, p)
    
    if key not in circuit_vectorencoder_matrices:
        circuit_vectorencoder_matrices[key] = {}
        
    R = circuit_vectorencoder_matrices[key]
    
    if config.get("component") == "output":
        raise ValueError("vectorencoder cannot be used as a decoder.")
        
    def f(lst):
        if not isinstance(lst, list):
            lst = list(lst)
        d = len(lst)
        if p <= 0 or d == 0:
            return []
            
        sparsity = config.get("sparsity", float(1.0 / math.sqrt(d)))
        
        if d not in R:
            num_ones = round(n * d * sparsity)
            flat_indices = rng.choice(n * d, size=num_ones, replace=False)
            rows = flat_indices // d
            cols = flat_indices % d
            vals = np.ones(num_ones)
            
            R[d] = sp.csr_matrix((vals, (rows, cols)), shape=(n, d))
            
        matrix = R[d]
        vec = matrix.dot(np.array(lst))
        
        min_val, max_val = np.min(vec), np.max(vec)
        span = max_val - min_val
        scale = max(abs(min_val), abs(max_val))
        tolerance = 1e-10
        
        if scale == 0 or span <= tolerance * scale:
            return []
            
        k = min(p, len(vec))
        top_k_indices = np.argsort(vec)[-k:]
        return sorted((top_k_indices + 1).tolist())
        
    def clear():
        R.clear()
        
    return {
        "label": "VEC",
        "function": f,
        "clear": clear
    }


## -----------------------------------------------------------------------------


circuit_flyhash_matrices = {}
circuit_flyhash_resting = {}

def flyhash(config):
    hyperparameters = config.get("hyperparameters", [0, 0])
    n, p = hyperparameters[0], hyperparameters[1]
    key = (n, p)
    
    if key not in circuit_flyhash_matrices:
        circuit_flyhash_matrices[key] = {}
        circuit_flyhash_resting[key] = {}
        
    R = circuit_flyhash_matrices[key]
    restingpotential = circuit_flyhash_resting[key]
    
    sparsity = config.get("sparsity", 0.1)
    
    if config.get("component") == "output":
        raise ValueError("flyhash cannot be used as a decoder.")
        
    def f(lst):
        if not isinstance(lst, list):
            lst = list(lst)
        d = len(lst)
        if p <= 0 or d == 0:
            return []
            
        arr = np.array(lst)
        centeredlist = arr - np.mean(arr)
        tolerance = 1e-10
        
        if d not in R:
            c = max(1, round(d * sparsity))
            
            rows = np.repeat(np.arange(n), c)
            cols = np.concatenate([rng.choice(d, size=c, replace=False) for _ in range(n)])
            vals = np.ones(n * c)
            
            R[d] = sp.csr_matrix((vals, (rows, cols)), shape=(n, d))
            restingpotential[d] = rng.uniform(0, tolerance * 0.01, size=n)
            
        vec = R[d].dot(centeredlist) + restingpotential[d]
        
        min_val, max_val = np.min(vec), np.max(vec)
        span = max_val - min_val
        scale = max(abs(min_val), abs(max_val))
        
        if scale == 0 or span <= tolerance * scale:
            return []
            
        k = min(p, len(vec))
        top_k_indices = np.argsort(vec)[-k:]
        return sorted((top_k_indices + 1).tolist())
        
    def clear():
        R.clear()
        restingpotential.clear()
        
    return {
        "label": "FLY",
        "function": f,
        "clear": clear
    }        
        
                
        
## -----------------------------------------------------------------------------
## Circuit Components
## -----------------------------------------------------------------------------



def input(config):
    """
    At the beginning of each cycle, external input is pushed 
    into the input's send slots. Input nodes have no "receive" slots.
    The callback function serves as an optional encoder/preprocessing plugin.
    """
    pluginconfig = config.copy()
    if "send_blocks" in config and config["send_blocks"]:
        pluginconfig["hyperparameters"] = config["send_blocks"][0]

    plugin_factory = config.get("plugin")
    
    if callable(plugin_factory):
        plugin = plugin_factory(pluginconfig)
    else:
        # Default Identity function
        plugin = {"function": lambda x: x}

    # Strict dictionary union: plugin properties are overridden by component hard requirements
    return plugin | {"size": 10, "checks": ["input", "oneout"]}




## -----------------------------------------------------------------------------





def output(config):
    """
    At the end of each cycle, the output's input edges are read out.
    Output nodes have no "send" slots.
    The callback function serves as an optional decoder/postprocessing plugin.
    """
    pluginconfig = config.copy()
    if "receive_blocks" in config and config["receive_blocks"]:
        pluginconfig["hyperparameters"] = config["receive_blocks"][0]

    plugin_factory = config.get("plugin")
    
    if callable(plugin_factory):
        plugin = plugin_factory(pluginconfig)
    else:
        # Default Identity function
        plugin = {"function": lambda x: x}

    return plugin | {"size": 10, "checks": ["output", "oneinp"]}



## -----------------------------------------------------------------------------

"""
The delay node encapsulates multiple functionalities:

- signal delay
- block coding and re-coding
- proportional decimation (default: none)
- rate limiting  (default: none)
- temporal integration via internal capacity (default: none),
    using the plugin mechanism for update rules .

Multisets and inhibitory signals are handled transparently . 
"""

def delay(config):
    plugin_factory = config.get("plugin", augmentation)
    
    if isinstance(plugin_factory, str):
        import sys
        plugin_factory = getattr(sys.modules[__name__], plugin_factory, augmentation)
        
    plugin = plugin_factory(config)
    
    # Remove label if plugin and capacity were implicitly defaulted
    if "plugin" not in config and "capacity" not in config:
        plugin.pop("label", None)

    dims1 = [b[0] for b in config.get("receive_blocks", [])]
    dims2 = [b[0] for b in config.get("send_blocks", [])]
    pop = sum(b[1] for b in config.get("receive_blocks", []))
    
    rate_limit_factor = config.get("rate_limit", float('inf'))
    absratelimit = round(rate_limit_factor * pop) if rate_limit_factor != float('inf') else float('inf')
    
    decay = config.get("decay", 0.0)
    capacity_factor = config.get("capacity", 0.0)
    abscapacity = round(capacity_factor * pop)
    decimation = config.get("decimate", 1.0)

    Xstate = []

    def f(*blocks):
        nonlocal Xstate
        X = multiset_block_join(list(blocks), dims1)
        
        if len(X) > absratelimit:
            X = sorted(rng.choice(X, size=absratelimit, replace=False).tolist())
            
        if decay > 0.0:
            keep_size = math.floor((1.0 - decay) * len(Xstate))
            Xstate = sorted(rng.choice(Xstate, size=keep_size, replace=False).tolist())
            
        if len(Xstate) > abscapacity:
            Xstate = sorted(rng.choice(Xstate, size=abscapacity, replace=False).tolist())
            
        Xstate = plugin["updaterule"](X, Xstate)
        
        # Proportional multiset subsampling applied to output
        Xdec = Xstate
        if decimation < 1.0:
            sample_size = math.floor(decimation * len(Xdec))
            Xdec = sorted(rng.choice(Xdec, size=sample_size, replace=False).tolist())
            
        return tuple(multiset_block_split(Xdec, dims2))
        
        
    result = dict(plugin)
    
    result.update({
        "function": f,
        "checks": ["arginp", "argout", "totaldim"],
        "fill": 13
    })
    return result
    
        

## -----------------------------------------------------------------------------




def latch(config):
    """
    A sample-and-hold latch with threshold and expiration.
    Latches onto a signal if its population meets threshold T.
    Holds and broadcasts the state for the specified number of additional cycles.
    """
    dims1 = [b[0] for b in config.get("receive_blocks", [])]
    dims2 = [b[0] for b in config.get("send_blocks", [])]
    pop = sum(b[1] for b in config.get("receive_blocks", []))

    # Hyperparameters
    threshold = config.get("threshold", 1.0)
    cycles = config.get("cycles", float('inf'))

    # Internal state and age tracker
    state = [[] for _ in dims2]
    timer = cycles + 1  # Start in an expired state

    def f(*blocks):
        nonlocal state, timer
        
        X = multiset_block_join(list(blocks), dims1)
        
        # Event-driven latch: Update state if threshold is met.
        if len(X) >= threshold * pop:
            state = multiset_block_split(X, dims2)
            timer = 0
        else:
            # Sub-threshold input: tick the timer only if within bounds.
            if timer <= cycles:
                timer += 1
            
            # Check expiration.
            if timer >= cycles:
                state = [[] for _ in dims2]

        return tuple(state)

    return {
        "function": f,
        "checks": ["arginp", "argout", "totaldim"],
        "fill": 13,
        "label": "■",
        "size": 17
    }


    

## -----------------------------------------------------------------------------

## Update rules for auto-associative memory components ("auto")
## and temporal integration ("delay").

def replacement(config):
    return {"updaterule": lambda y, x: y, "label": "▼", "size": 18}

def residual(config):
    return {"updaterule": lambda y, x: resolve_graded(multiset([x, [-i for i in y]])), "label": "▲", "size": 18}

def complement(config):
    return {"updaterule": lambda y, x: resolve_graded(multiset([y, [-i for i in x]])), "label": "▽", "size": 20}

def difference(config):
    return {"updaterule": lambda y, x: sorted([abs(i) for i in multiset([y, [-i for i in x]])]), "label": "△", "size": 20}

def augmentation(config):
    return {"updaterule": lambda y, x: multiset([y, x]), "label": "∪", "size": 14}

def coincidence(config):
    def multiset_intersection(y, x):
        counts_y = Counter(y)
        counts_x = Counter(x)
        res = []
        for k, v in counts_y.items():
            res.extend([k] * min(v, counts_x.get(k, 0)))
        return sorted(res)
    return {"updaterule": multiset_intersection, "label": "∩", "size": 14}

def permutation(config):
    dims = sum(b[0] for b in config.get("receive_blocks", []))
    dim = dims if dims else 0
    perm = rng.choice(range(1, dim + 1), size=dim, replace=False).tolist() if dim > 0 else []
    
    def updaterule(y, x):
        mapped_x = sorted([(1 if i > 0 else -1 if i < 0 else 0) * perm[abs(i) - 1] for i in x if i != 0])
        return multiset([y, mapped_x])
        
    return {"updaterule": updaterule, "label": "π", "size": 16}


## -----------------------------------------------------------------------------

"""
Auto-associative memory component . 

Note: There is a wide range of possible learning, subsampling, retrieval 
and update rules for auto-associative memory . This prototype captures the 
geneneric cases . Modify as needed .
"""

def auto(config):
    plugin_factory = config.get("plugin", replacement)
    
    if isinstance(plugin_factory, str):
        # Resolve string name to function dynamically
        import sys
        plugin_factory = getattr(sys.modules[__name__], plugin_factory, replacement)
        
    plugin = plugin_factory(config)

    receive_blocks = config.get("receive_blocks", [])
    dims = [b[0] for b in receive_blocks]
    
    # params = Plus @@ config["receive_blocks"] (Sums Ns and Ps respectively)
    params = [sum(b[0] for b in receive_blocks), sum(b[1] for b in receive_blocks)]
    pop = params[1] if len(params) > 1 else 0

    rate_limit_factor = config.get("rate_limit", float('inf'))
    absratelimit = round(rate_limit_factor * pop) if rate_limit_factor != float('inf') else float('inf')
    
    decimation = config.get("decimate", 1.0)

    # Learning thresholds
    min_val = pop
    max_val = pop
    learn_val = config.get("learn", False)
    
    if isinstance(learn_val, (int, float)) and not isinstance(learn_val, bool):
        min_val = max_val = round(learn_val * pop)
    elif isinstance(learn_val, (list, tuple)) and len(learn_val) == 2:
        min_val = round(learn_val[0] * pop)
        max_val = round(learn_val[1] * pop)

    # Memory with identical input and output parameters
    m_config = dict(config)
    m_config.update({
        "A_parameters": params,
        "B_parameters": params
    })
    
    # Depends on Memory imported from creating_intelligence
    M = Memory(m_config)

    def f(*blocks):
        # Join partitions and apply inhibition
        A = resolve_block_join_normal(list(blocks), dims)
        X = A
        
        # Limit the rate of incoming positives
        if len(X) > absratelimit:
            X = sorted(rng.choice(X, size=absratelimit, replace=False).tolist())
            
        # Proportional decimation
        if decimation < 1.0:
            sample_size = math.floor(decimation * len(X))
            Xdec = sorted(rng.choice(X, size=sample_size, replace=False).tolist())
        else:
            Xdec = X
            
        # Always learn if "learn" is strictly True
        if learn_val is True:
            M["store"](A)
            
        # Memory retrieval with decimated and rate-limited input state
        Y = M["retrieve"](Xdec)
        
        # Learn input A if retrieval fails and it falls within thresholds
        if not Y and min_val <= len(A) <= max_val:
            if learn_val is not True:
                M["store"](A)
            Y = A
            
        X_out = plugin["updaterule"](Y, X)
        X_out = sorted(list(set(X_out))) 
              
        return tuple(multiset_block_split(X_out, dims))

    # Merge plugin attributes, component defaults, and Memory closures (e.g., "clear")
    result = dict(plugin)
    result.update({
        "function": f,
        "checks": ["arginp", "argout", "ident"],
        "shape": "Square",
        "fill": 8
    })
    result.update(M)
    
    return result
  

## -----------------------------------------------------------------------------

"""
Temporal-associative memory component . 
Learns higher-order sequences on the fly and predicts the next token .
A hybrid between auto-associative and hetero-associative architectures .
Uses the same temporal integration parametrization as "delay" .
"""

def temporal(config):
    plugin_factory = config.get("plugin", permutation)
    
    if isinstance(plugin_factory, str):
        import sys
        plugin_factory = getattr(sys.modules[__name__], plugin_factory, permutation)
        
    plugin = plugin_factory(config)
    
    if "plugin" not in config and "capacity" not in config:
        plugin.pop("label", None)

    receive_blocks = config.get("receive_blocks", [])
    dims = [b[0] for b in receive_blocks]
    
    params = [sum(b[0] for b in receive_blocks), sum(b[1] for b in receive_blocks)]
    pop = params[1] if len(params) > 1 else 0
    
    rate_limit_factor = config.get("rate_limit", float('inf'))
    absratelimit = round(rate_limit_factor * pop) if rate_limit_factor != float('inf') else float('inf')
    
    decay = config.get("decay", 0.0)
    capacity_factor = config.get("capacity", 0.0)
    abscapacity = round(capacity_factor * pop)
    decimation = config.get("decimate", 1.0)

    # Memory with identical input and output parameters
    m_config = dict(config)
    m_config.update({
        "A_parameters": params,
        "B_parameters": params
    })
    
    M = Memory(m_config)
    Xstate = []

    def f(*blocks):
        nonlocal Xstate
        X = multiset_block_join(list(blocks), dims)
        
        # Rate limiting equally applies to positive and negative elements
        if len(X) > absratelimit:
            X = sorted(rng.choice(X, size=absratelimit, replace=False).tolist())
            
        # Pre-integration stochastic decay
        if decay > 0.0:
            keep_size = math.floor((1.0 - decay) * len(Xstate))
            Xstate = sorted(rng.choice(Xstate, size=keep_size, replace=False).tolist())
            
        # Always learn state -> current input
        M["store"](resolve_normal(Xstate), resolve_normal(X))
        
        # Multiset subsampling applied to previous state
        if len(Xstate) > abscapacity:
            Xstate = sorted(rng.choice(Xstate, size=abscapacity, replace=False).tolist())
            
        # Temporal integration via update rules
        Xstate = plugin["updaterule"](X, Xstate)
        
        # Proportional multiset subsampling applied to the integrated state
        Xdec = Xstate
        if decimation < 1.0:
            sample_size = math.floor(decimation * len(Xdec))
            Xdec = sorted(rng.choice(Xdec, size=sample_size, replace=False).tolist())
            
        # Predict next token
        prediction = M["retrieve"](resolve_normal(Xdec))
        
        return tuple(multiset_block_split(prediction, dims))

    result = dict(plugin)
    result.update({
        "function": f,
        "checks": ["arginp", "argout", "ident"],
        "shape": "Square",
        "fill": 14
    })
    result.update(M)
    
    return result

  
## -----------------------------------------------------------------------------
    



def associator(config):
    """
    Vanilla hetero-associative node for supervised learning A -> B.
    B is the first input argument. A is given by the rest of the input arguments. 
    Can be block-coded. Always learns if B != [].
    """
    receive_blocks = config.get("receive_blocks", [])
    Adims = [b[0] for b in receive_blocks[1:]] 
    
    decimation = config.get("decimate", 1.0)
    oversampling = config.get("oversampling", 1.0)
    
    params_A = [sum(b[0] for b in receive_blocks[1:]), sum(b[1] for b in receive_blocks[1:])]
    params_B = receive_blocks[0]
    
    m_config = dict(config)
    m_config.update({
        "A_parameters": params_A,
        "B_parameters": params_B
    })
    
    M = Memory(m_config)
    
    def f(B, *blocks):
        X = resolve_block_join_normal(list(blocks), Adims)
        Y = resolve_normal(B)
        
        if not Y:
            return (M["retrieve"](X),)
            
        if decimation < 1.0:
            sample_size = math.floor(decimation * len(X))
            X = sorted(rng.choice(X, size=sample_size, replace=False).tolist())
            
        if oversampling > 1.0:
            extra_size = round((oversampling - 1.0) * len(X))
            pool = [i for i in range(1, params_A[0] + 1) if i not in X]
            extra = rng.choice(pool, size=min(extra_size, len(pool)), replace=False).tolist()
            X = sorted(X + extra)
            
        M["store"](X, Y)
        return ([],)

    result = {
        "function": f,
        "checks": ["dimfirst", "oneout"],
        "shape": "Square",
        "fill": 11,
        "size": 18,
        "label": "▶●"
    }
    result.update(M)
    return result




## -----------------------------------------------------------------------------





def heteroencoder(config):
    """
    Heteroencoder A -> B. A may be partitioned. Has no input for B.
    """
    receive_blocks = config.get("receive_blocks", [])
    dims = [b[0] for b in receive_blocks]
    
    params_A = [sum(b[0] for b in receive_blocks), sum(b[1] for b in receive_blocks)]
    params_B = config.get("send_blocks", [[0, 0]])[0]
    
    m_config = dict(config)
    m_config.update({
        "A_parameters": params_A,
        "B_parameters": params_B
    })
    
    M = Memory(m_config)
    
    def f(*blocks):
        X = resolve_block_join_normal(list(blocks), dims)
        Y = M["retrieve"](X)
        
        if not Y:
            n, p = params_B
            Y = sorted(rng.choice(range(1, n + 1), size=p, replace=False).tolist())
            
        M["store"](X, Y)
        return (Y,)

    result = {
        "function": f,
        "checks": ["arginp", "oneout"],
        "shape": "Square",
        "fill": 11,
        "size": 18,
        "label": "◀▶"
    }
    result.update(M)
    return result




## -----------------------------------------------------------------------------



def predictor(config):
    """
    Generates a prediction based on the current input (slot #1) and context (slots #2,...).
    Automatically learns the correct prediction in the following cycle.
    """
    receive_blocks = config.get("receive_blocks", [])
    itemconfig = receive_blocks[0]
    contextconfig = receive_blocks[1:]
    
    # Extract decimation parameter, defaulting to 1.0
    decimation = config.get("decimate", 1.0)
    
    params_A = [sum(b[0] for b in contextconfig), sum(b[1] for b in contextconfig)]
    params_B = itemconfig
    
    m_config = dict(config)
    m_config.update({
        "A_parameters": params_A,
        "B_parameters": params_B
    })
    
    M = Memory(m_config)
    X = []
    
    def f(item, *blocks):
        nonlocal X
        Y = resolve_normal(item)
        
        M["store"](X, Y)
        
        X = resolve_block_join_normal(list(blocks), [b[0] for b in contextconfig])
        
        # Apply stochastic subsampling to X before retrieval
        if decimation < 1.0:
            sample_size = math.floor(decimation * len(X))
            Xdec = sorted(rng.choice(X, size=sample_size, replace=False).tolist())
        else:
            Xdec = X
            
        prediction = M["retrieve"](Xdec)
        
        return (prediction,)

    result = {
        "function": f,
        "checks": ["dimfirst", "oneout"],
        "shape": "Square",
        "fill": 11,
        "size": 18,
        "label": "▶▶"
    }
    result.update(M)
    return result
    


## -----------------------------------------------------------------------------





def noise(config):
    """Random noise generator."""
    n, p = config.get("send_blocks", [[0, 0]])[0]
    
    def f(*blocks):
        return (sorted(rng.choice(range(1, n + 1), size=p, replace=False).tolist()),)
        
    return {
        "function": f,
        "checks": ["input", "oneout"],
        "label": "~",
        "fill": 13,
        "size": 18
    }



## -----------------------------------------------------------------------------



def file(config):
    file_path = config.get("name")
    if not file_path:
        raise CircuitError(f"Missing 'name' property in {config}")
        
    if not file_path.endswith(".json"):
        file_path += ".json"

    # Search current working directory first, then sys.path
    search_paths = [""] + sys.path 
    
    full_path = None
    for base in search_paths:
        target = os.path.join(base, file_path) if base else file_path
        if os.path.exists(target):
            full_path = target
            break
            
    if not full_path:
        raise CircuitError(f"File '{file_path}' not found in current directory or sys.path.")
        
    with open(full_path, "r") as f:
        circ_expr = json.load(f)
    
    # Rescale hyperparameters of embedded circuit
    scale = config.get("scale")
    default_hp = circ_expr.get("hyperparameters", {}).get("default")
    
    if (isinstance(scale, (list, tuple)) and len(scale) == 2 and 
        isinstance(default_hp, (list, tuple)) and len(default_hp) == 2):
                        
        # Calculate separate scaling factors
        rescale_factor_n = scale[0] / default_hp[0]
        rescale_factor_p = scale[1] / default_hp[1]
        
        # Apply scaling to all hyperparameters in the embedded circuit
        for k, v in circ_expr["hyperparameters"].items():
            if isinstance(v, (list, tuple)) and len(v) == 2:
                circ_expr["hyperparameters"][k] = [
                    round(v[0] * rescale_factor_n), 
                    round(v[1] * rescale_factor_p)
                ]                
                
                
    # Compile the imported circuit
    sub = Circuit(circ_expr)
    
    # Extract up to 5 characters from the filename for the label
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    sub["label"] = base_name[:5]
    
    return sub    


# Registry for compiled embedded circuits
circuit_registry = {}

def shared(config):
    """Plug-in for embedding a precompiled circuit."""
    name = config.get("name")
    if not name:
        raise ValueError(f"Missing 'name' property in shared circuit: {config}")
        
    sub = circuit_registry.get(name)
    if not sub:
        raise ValueError(f"Unknown circuit '{name}'.")
        
    result = dict(sub)
    result["label"] = name
    result.pop("clear", None) 
    
    return result


def circuit(config):
    """
    Embedded circuit component.
    Multiple circuit components can reference the same embedded instance.
    """
    plugin_factory = config.get("plugin", shared)
    
    if isinstance(plugin_factory, str):
        import sys
        plugin_factory = getattr(sys.modules[__name__], plugin_factory, shared)
        
    plugin = plugin_factory(config)
    if not plugin:
        return {}
        
    params = [plugin.get("receive_blocks", []), plugin.get("send_blocks", [])]
    
    if [config.get("receive_blocks", []), config.get("send_blocks", [])] != params:
        raise ValueError(f"Hyperparameters of embedded circuit do not match: {params}")
        
    def f(*blocks):
        return plugin["function"](*blocks)
        
    result = dict(plugin)
    result.update({
        "function": f,
        "checks": ["arginp", "argout"],
        "shape": "Square",
        "size": 9
    })
    
    return result
    
    
  
## -----------------------------------------------------------------------------
    
## Circuit Error Handling

class CircuitError(Exception):
    """Custom exception for Circuit-related errors."""
    pass

circuit_messages = {
    "ident": "{0}: Inputs must match outputs.",
    "identdim": "{0}: Input and output dimensions must be identical.",
    "totaldim": "{0}: Total input and output dimensions must match.",
    "dimfirst": "{0}: Output must match first input slot.",
    "input": "No input slots allowed in {0}.",
    "oneinp": "Expecting one input slot in {0}.",
    "arginp": "{0}: Missing input.",
    "output": "No output slots allowed in {0}.",
    "oneout": "{0}: Expecting one output slot.",
    "argout": "{0}: Missing output."
}

circuit_checks = {
    "ident": lambda r, s: [b[0] for b in r] == [b[0] for b in s],
    "identdim": lambda r, s: sorted(list(set(b[0] for b in r))) == sorted(list(set(b[0] for b in s))),
    "totaldim": lambda r, s: sum(b[0] for b in r) == sum(b[0] for b in s),
    "dimfirst": lambda r, s: len(r) > 0 and len(s) > 0 and r[0] == s[0],
    "input": lambda r, s: len(r) == 0,
    "oneinp": lambda r, s: len(r) == 1,
    "arginp": lambda r, s: len(r) > 0,
    "output": lambda r, s: len(s) == 0,
    "oneout": lambda r, s: len(s) == 1,
    "argout": lambda r, s: len(s) > 0
}
    


## -----------------------------------------------------------------------------
## Circuit Visualization
## -----------------------------------------------------------------------------


# 16-color Nord hex palette as defined in the Mathematica source
NORD_PALETTE = [
    "#2E3440", "#3B4252", "#434C5E", "#4C566A",
    "#D8DEE9", "#E5E9F0", "#ECEFF4", "#8FBCBB",
    "#88C0D0", "#81A1C1", "#5E81AC", "#BF616A",
    "#D08770", "#EBCB8B", "#A3BE8C", "#B48EAD"
]

# Tag mapping for edge labels
TAG_MAP = {
    "multiset": "+", "inhibit": "-", "permute": "π",
    "noise": "~", "rate_limit": "R", "threshold": "T",
    "veto": "X", "mandatory": "*", "priority": "!",
    "dependency": "&", "fallback": "|", "barrier": "=",
    "kwta_excitatory": "K", "kwta_absolute": "k",
    "log": "?", "show_slot": "#", "show_dimension": "$",
    "show_population": "%"
}    
    
## -----------------------------------------------------------------------------
## Circuit Factory
## -----------------------------------------------------------------------------


def Circuit(expr):
    """
    Parses a circuit dataflow dictionary and returns a compiled circuit interface.
    Replicates the data-driven execution flow and state isolation.
    """
    nodes = {}
    pathways = {}
    
    preprocess = []
    postprocess = []
    inputslots = []
    outputedges = []
    
    receiveparams = []
    sendparams = []
    permutations = {}

    # Isolated runtime state buffers
    tick = 0
    nextstate = {}
    currentstate = {}
    
    nodeid = 0
    edgeid = 0

    def slotparams(slot):
        hyperparameters = expr.get("hyperparameters", {})
        default = hyperparameters.get("default", [100, 3])
        # Accommodate both int and string keys from JSON
        np_val = hyperparameters.get(slot, hyperparameters.get(str(slot), default))
        
        if not (isinstance(np_val, list) and len(np_val) == 2):
            return [100, 3]
        return np_val

    def fillparams(x):
        if isinstance(x, list):
            lists = [fillparams(i) for i in x]
            dims = [l[0] for l in lists]
            return [dims[0], min(l[1] for l in lists)]
        elif isinstance(x, int):
            return slotparams(x)
        elif isinstance(x, dict):
            return slotparams(x["slot"])
        return None

    def compilepathway(receive):
        nonlocal edgeid
        
        if isinstance(receive, list):
            return [compilepathway(r) for r in receive]

        edgeid += 1
        current_id = edgeid

        e = {
            "to_node_id": nodeid,
            "label": "",
            "tags": []
        }

        if isinstance(receive, int):
            e["slot"] = receive
        elif isinstance(receive, dict):
            e.update(receive)

        e["hyperparameters"] = slotparams(e.get("slot"))

        if "inhibit" in e["tags"] and "multiset" not in e["tags"]:
            e["tags"].append("multiset")

        pathways[current_id] = e
        currentstate[e.get("slot")] = []
        
        # Initialize 1-based permutation array
        n = e["hyperparameters"][0]
        perm = rng.choice(range(1, n + 1), size=n, replace=False).tolist()
        permutations[current_id] = perm
        
        return current_id

    def compile_node(node):
        nonlocal nodeid
        nodeid += 1
        current_node_id = nodeid

        rec_paths = [compilepathway(r) for r in node.get("receive", [])]
        
        # Flatten send array and extract slots
        raw_sends = node.get("send", [])
        flat_sends = []
        def _flat(items):
            for i in items:
                if isinstance(i, list): _flat(i)
                else: flat_sends.append(i)
        _flat(raw_sends)
        
        send_slots = []
        for s in flat_sends:
            if isinstance(s, int):
                send_slots.append(s)
            elif isinstance(s, dict) and "slot" in s:
                send_slots.append(s["slot"])

        # Base configuration dictionary
        config = dict(node)
        config.update({
            "receive_paths": rec_paths,
            "node_id": current_node_id,
            "send_slots": send_slots,
            "scale": expr.get("hyperparameters", {}).get("default"),
            "receive_blocks": [fillparams(r) for r in node.get("receive", [])],
            "send_blocks": [fillparams(s) for s in node.get("send", [])]
        })

        # Resolve plugin dependency dynamically
        plugin_name = config.get("plugin")
        if isinstance(plugin_name, str):
            plugin_func = getattr(sys.modules[__name__], plugin_name, None)
            if callable(plugin_func):
                config["plugin"] = plugin_func
            else:
                raise ValueError(f"Invalid plugin '{plugin_name}'.")

        comp_name = node.get("component")
        if not isinstance(comp_name, str):
            return
            
        # Dynamic module namespace lookup
        comp_func = getattr(sys.modules[__name__], comp_name, None)
        if not callable(comp_func):
            raise ValueError(f"Invalid circuit component '{comp_name}'.")

        comp_result = comp_func(config)
        
        # Strict overriding sequence
        final_config = {
            "shape": "Circle", "label": "", "fill": 6, "color": 0, "size": 12,
            "checks": [], "function": None
        }
        final_config.update(config)
        final_config.update(comp_result)
        
        # Static error checking, based on component-supplied "checks"
        for check in final_config.get("checks", []):
            if check in circuit_checks:
                if not circuit_checks[check](final_config["receive_blocks"], final_config["send_blocks"]):
                    error_msg = circuit_messages.get(check, f"Check {check} failed.").format(comp_name)
                    raise CircuitError(error_msg)        
        
        if comp_name == "input":
            preprocess.append(final_config["function"])
            inputslots.append(final_config["send_slots"][0])
            receiveparams.append(final_config["send_blocks"][0])
            final_config["label"] = final_config["label"].replace("#", str(len(inputslots)))

        if comp_name == "output":
            postprocess.append(final_config["function"])
            outputedges.append(final_config["receive_paths"][0])
            sendparams.append(final_config["receive_blocks"][0])
            final_config["label"] = final_config["label"].replace("#", str(len(outputedges)))

        nodes[current_node_id] = final_config

    # Trigger compilation
    for node in expr.get("dataflow", []):
        compile_node(node)

    # Compile link table for from_node_id values
    links = {}
    for node in nodes.values():
        for slot in node.get("send_slots", []):
            links[slot] = node["node_id"]

    for edge in pathways.values():
        edge["from_node_id"] = links.get(edge.get("slot"), 0)

    def patheval(id_val):
        e = pathways[id_val]
        tags = set(e.get("tags", []))
        n, p = e["hyperparameters"]
        
        x = currentstate.get(e.get("slot"), [])
        
        # Upstream validation of 1-based non-zero data
        if not isinstance(x, list) or 0 in x:
            raise ValueError(f"Invalid data in slot {e.get('slot')}: {x}")
            
        gating = e.get("gating", [1])
        if gating[(tick - 1) % len(gating)] == 0:
            return []
            
        # The ONLY source of inhibition
        if "inhibit" in tags:
            x = [-abs(i) for i in x]
            
        if "multiset" in tags:
            x = multiset(x)
        else:
            x = resolve_normal(x)
            
        if "permute" in tags:
            perm = permutations[id_val]
            x = sorted([(1 if i > 0 else -1) * perm[abs(i) - 1] for i in x])
            
        if "rate_limit" in tags and len(x) > p:
            x = sorted(rng.choice(x, size=p, replace=False).tolist())
            
        if "threshold" in tags and len(x) < p:
            x = []
            
        if "noise" in tags:
            if not x:
                x = sorted(rng.choice(range(1, n + 1), size=p, replace=False).tolist())
            else:
                x = []
                
        if "log" in tags:
            print(f"Slot {e.get('slot')}: {x}")
            
        return x



    def pathmerge(ids):
        if isinstance(ids, int):
            ids = [ids]
            
        x_list = [patheval(i) for i in ids]
        paths = [pathways[i] for i in ids]
        
        def has_tag(t):
            return [t in p.get("tags", []) for p in paths]
            
        veto_tags = has_tag("veto")
        if any(x for i, x in enumerate(x_list) if veto_tags[i] and x):
            return []
            
        mandatory_tags = has_tag("mandatory")
        if any(not x for i, x in enumerate(x_list) if mandatory_tags[i]):
            return []
            
        priority_tags = has_tag("priority")
        if any(x for i, x in enumerate(x_list) if priority_tags[i] and x):
            x_list = [x if priority_tags[i] else [] for i, x in enumerate(x_list)]
            
        dependency_tags = has_tag("dependency")
        if any(not x for i, x in enumerate(x_list) if not dependency_tags[i]):
            x_list = [[] if dependency_tags[i] else x for i, x in enumerate(x_list)]
            
        fallback_tags = has_tag("fallback")
        if any(x for i, x in enumerate(x_list) if not fallback_tags[i] and x):
            x_list = [[] if fallback_tags[i] else x for i, x in enumerate(x_list)]
            
        barrier_tags = has_tag("barrier")
        if any(barrier_tags) and any(not x for i, x in enumerate(x_list) if barrier_tags[i]):
            x_list = [[] if barrier_tags[i] else x for i, x in enumerate(x_list)]
            
        merged = multiset(x_list)
        
        kwta_exc_tags = has_tag("kwta_excitatory")
        kwta_abs_tags = has_tag("kwta_absolute")
        
        if any(kwta_exc_tags) or any(kwta_abs_tags):
            k = min(p["hyperparameters"][1] for p in paths)
            U = [i for i in merged if i > 0] if any(kwta_exc_tags) else merged
            
            tally = Counter(U)
            if len(tally) >= k:
                freqs = sorted(tally.values())
                rankedmax = freqs[-k]
                if rankedmax >= 2:
                    merged = sorted([val for val, count in tally.items() if count >= rankedmax])
                else:
                    merged = []
            else:
                merged = []
                
        return merged
        
        
    def componenteval(config):
        if config.get("component") in ("input", "output"):
            return
            
        inputs = [pathmerge(rp) for rp in config.get("receive_paths", [])]
        
        func = config.get("function")
        result = func(*inputs) if func else tuple([] for _ in config.get("send_slots", []))
            
        if not isinstance(result, tuple):
            result = (result,)
            
        for slot, res in zip(config.get("send_slots", []), result):
            nextstate[slot] = res

    def evaluate(x):
        nonlocal tick, currentstate, nextstate
        tick += 1
        
        for slot, val in zip(inputslots, x):
            currentstate[slot] = val
            nextstate[slot] = val
            
        for config in nodes.values():
            componenteval(config)
            
        # Snapshot state, preparing for extraction and next cycle
        currentstate = dict(nextstate)
        
        return [pathmerge(edge) for edge in outputedges]

    def multiplex(x):
        if len(x) != len(inputslots):
            raise ValueError(f"Function arguments do not match input nodes: {inputslots}")
            
        multiplex = expr.get("options", {}).get("multiplex", [1])
        if not all(m in (0, 1) for m in multiplex):
            multiplex = [1]
            
        y = []
        for gate in multiplex:
            if gate == 1:
                y = evaluate(x)
            else:
                y = evaluate([[] for _ in x])
        return y

    def f(*blocks):
        x = list(blocks)
        if len(x) != len(inputslots):
            raise ValueError(f"Function arguments do not match input nodes: {inputslots}")
            
        x_enc = [prep(val) for prep, val in zip(preprocess, x)]
        y_raw = multiplex(x_enc)
        y = [post(val) for post, val in zip(postprocess, y_raw)]
        
        return tuple(y)
        
    def schematics(filename):
        """Generates a static PNG graph visualization of the circuit."""
        G = nx.MultiDiGraph()

        # Build nodes
        for nid, node_data in nodes.items():
            fill_color = NORD_PALETTE[node_data.get("fill", 6)]
            text_color = NORD_PALETTE[node_data.get("color", 0)]
            label = node_data.get("label", "")
            
            # Map node shapes and apply shape-specific area multipliers
            if node_data.get("shape") == "Square":
                shape = "s"
                size_multiplier = 100
            else:
                shape = "o" # Default Circle
                size_multiplier = 180 # Scale circles up relative to squares

            G.add_node(
                nid, 
                label=label, 
                fill_color=fill_color, 
                text_color=text_color,
                shape=shape,
                size=node_data.get("size", 12) * size_multiplier
            )
        # Build edges
        for eid, edge_data in pathways.items():
            u = edge_data.get("from_node_id")
            v = edge_data.get("to_node_id")
            
            if not u or not v:
                continue

            tags = edge_data.get("tags", [])
            
            # Construct edge label logic
            tag_symbols = "".join([TAG_MAP.get(t, "") for t in tags])
            user_label = edge_data.get("label", "")
            raw_label = f"{user_label}{tag_symbols}"
            
            # Substitute dynamic variables
            hyperparams = edge_data.get("hyperparameters", [0, 0])
            replacements = {
                "#": str(edge_data.get("slot", "")),
                "$": str(hyperparams[0]),
                "%": str(hyperparams[1])
            }
            
            final_label = raw_label
            for old, new in replacements.items():
                final_label = final_label.replace(old, new)
                
            # Clean up default labels from UI display
            display_label = final_label.replace("-", "").replace("+", "").replace("*", "✱")
                
            # Edge styling
            edge_color = NORD_PALETTE[0]
            edge_width = 1.0
            
            if "-" in tag_symbols:
                edge_color = NORD_PALETTE[11] # Thick red for inhibition
                edge_width = 3.5
            elif "+" in tag_symbols:
                edge_color = NORD_PALETTE[8] # Thick blue for excitation
                edge_width = 3.5

            G.add_edge(
                u, v, 
                label=display_label, 
                color=edge_color, 
                width=edge_width
            )

        # Render graph
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Create a clean graph strictly for layout calculation
        G_layout = nx.MultiDiGraph()
        G_layout.add_nodes_from(G.nodes())
        G_layout.add_edges_from(G.edges(keys=True))
        
        # Assign attributes (respected by AGraph, often dropped by PyDot)
        G_layout.graph['rankdir'] = 'LR'
        G_layout.graph['ranksep'] = '0.85' 
        G_layout.graph['nodesep'] = '0.85' 

        # Left-to-right hierarchical layout using Graphviz (dot)
        try:
            from networkx.drawing.nx_agraph import graphviz_layout
            pos = graphviz_layout(G_layout, prog='dot', args='-Grankdir=LR')
        except ImportError:
            try:
                from networkx.drawing.nx_pydot import pydot_layout
                # PyDot wrapper drops the rankdir graph attribute.
                # Calculate standard Top-to-Bottom and rotate mathematically to enforce Left-to-Right.
                pos_tb = pydot_layout(G_layout, prog='dot')
                pos = {n: (-y, x) for n, (x, y) in pos_tb.items()}
            except ImportError:
                print("Warning: Install 'pygraphviz' or 'pydot' (and OS-level Graphviz) for left-to-right layout.")
                pos = nx.spring_layout(G_layout, seed=42)
                
        # Render graph on a slightly larger canvas
        fig, ax = plt.subplots(figsize=(11, 7))
        
        # Draw edges individually to calculate curve routing for bidirectional and parallel overlaps
        edges = G.edges(data=True, keys=True)
        for u, v, key, data in edges:
            rad = 0.0
            if G.has_edge(v, u) or G.number_of_edges(u, v) > 1:
                # Alternate the curvature radius for parallel edges: 0.2, -0.2, 0.4, -0.4...
                magnitude = 0.2 + 0.2 * (key // 2)
                direction = 1 if key % 2 == 0 else -1
                rad = magnitude * direction
            
            nx.draw_networkx_edges(
                 G, pos, 
                 edgelist=[(u, v)], 
                 edge_color=data['color'], 
                 width=data['width'],
                 arrows=True,
                 arrowstyle='-|>',
                 arrowsize=18, 
                 node_size=G.nodes[v]['size'],
                 node_shape=G.nodes[v]['shape'], # Instructs Matplotlib to calculate intersection for this specific shape
                 connectionstyle=f'arc3,rad={rad}',
                 ax=ax
             )   
                      
        # Aggregate labels for parallel edges into multiline strings centered between the curves
        edge_labels = {}
        for u, v, key, data in edges:
            lbl = data.get('label', '')
            if lbl:
                current = edge_labels.get((u, v), "")
                # Prevent duplicating identical labels on perfectly mirrored parallel edges
                if lbl not in current:
                    edge_labels[(u, v)] = f"{current}\n{lbl}" if current else lbl
        
        nx.draw_networkx_edge_labels(
            G, pos, edge_labels=edge_labels, 
            font_family="Inter Variable", 
            font_color=NORD_PALETTE[0],
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="none"),
            label_pos=0.5,
            ax=ax
        )
        
        # Draw nodes
        for node, data in G.nodes(data=True):
            nx.draw_networkx_nodes(
                G, pos, nodelist=[node], 
                node_color=data['fill_color'], 
                node_shape=data['shape'],
                node_size=data['size'],
                edgecolors=NORD_PALETTE[1], 
                linewidths=1.5,
                ax=ax
            )
            
        # Draw node labels
        node_labels = {node: data['label'] for node, data in G.nodes(data=True)}
        nx.draw_networkx_labels(
            G, pos, labels=node_labels, 
            font_family="Inter Variable", 
            font_color=NORD_PALETTE[0],
            font_weight="bold",
            ax=ax
        )
        
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close(fig)
    def clear():
        for node in nodes.values():
            c = node.get("clear")
            if callable(c):
                c()

    dispatch = {
        "function": f,
        "schematics": schematics,
        "clear": clear,
        "receive_blocks": receiveparams,
        "send_blocks": sendparams,
        "nodes": lambda: nodes
    }
    
    name = expr.get("options", {}).get("name")
    if name is not None:
        dispatch["name"] = name
        
    return dispatch
        
    