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

import json
from creating_intelligence import Circuit

def match_pattern(expected, actual):
    if expected == "_":
        return True
    
    if isinstance(expected, list) and isinstance(actual, list):
        if expected == ["__"]:
            return len(actual) >= 1
        
        if expected and expected[-1] == "__":
            prefix = expected[:-1]
            if len(actual) < len(prefix):
                return False
            return all(match_pattern(e, a) for e, a in zip(prefix, actual[:len(prefix)]))
        
        if len(expected) != len(actual):
            return False
        
        return all(match_pattern(e, a) for e, a in zip(expected, actual))
        
    return expected == actual

def run_testsuite(json_path):
    with open(json_path, "r") as f:
        testsuite = json.load(f)

    circuits_count = 0
    tests_count = 0
    failures_count = 0

    for test in testsuite:
        circuit_config = test["circuit"]
        circuits_count += 1
        
        print("Circuit JSON:")
        print(json.dumps(circuit_config, indent=2))
        
        circuit_instance = Circuit(circuit_config)
        run_fn = circuit_instance["function"]
        
        for case_idx, case in enumerate(test.get("cases", [])):
            tests_count += 1
            inp = case.get("input", [])
            expected = case.get("output", [])
            
            # Unpack the list directly so each nested list maps to one input slot
            actual_tuple = run_fn(*inp)
            actual = list(actual_tuple)
            
            print(f"Input:    {inp}")
            print(f"Output:   {actual}")
            
            if not match_pattern(expected, actual):
                failures_count += 1
                print(f"Regression found. ")
                print(f"Expected: {expected}")
         
        # Clear the stateful components of the circuit after its test cases finish
        if "clear" in circuit_instance and callable(circuit_instance["clear"]):
            circuit_instance["clear"]()
            
        print("-" * 40)

    print("\nTest Summary:")
    print(f"Circuits generated: {circuits_count}")
    print(f"Test cases run:     {tests_count}")
    print(f"Regressions:        {failures_count}")

if __name__ == "__main__":
    run_testsuite("testsuite.json")


    