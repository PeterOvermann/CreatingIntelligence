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

import os
import sys
import json
from creating_intelligence import Circuit

def main():
    if len(sys.argv) < 2:
        print("Usage: python schematics.py <path_to_file.json>")
        sys.exit(1)

    json_path = sys.argv[1]

    if not os.path.exists(json_path):
        print(f"Error: File '{json_path}' not found.")
        sys.exit(1)

    with open(json_path, "r") as f:
        config = json.load(f)

    circuit_instance = Circuit(config)
    
    # Extract basename and generate the output PNG filename
    base_name = os.path.splitext(os.path.basename(json_path))[0]
    output_png = f"{base_name}.png"
    
    # Invoke the schematics closure
    circuit_instance["schematics"](output_png)
    print(f"Saved schematics to {output_png}")

if __name__ == "__main__":
    main()
