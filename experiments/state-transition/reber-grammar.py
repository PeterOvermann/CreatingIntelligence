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


# Reber grammar: a finite automaton in transition memory.
#
# The circuit in ReberGrammar.json implements the finite-state grammar of
# Reber (1967) with a "transition" memory component. The query is a bundle
# of the current state and the current letter, and the memory returns the
# next state. The state is fed back and bundled with the next letter.
#
# The threshold is set above the population of a single token and below
# that of a complete (state, letter) key. A transition therefore fires only
# on its complete key. An undefined transition returns the empty set, and
# neither a lone letter nor a lone state can restart the automaton, so it
# stays halted for the rest of the string.
#
# The grammar is cyclic: every string starts and ends in the state "end".
# Each string is presented with the start state "end" together with its
# first letter. After an accepted string, the fed-back state is "end" as
# well; after a rejected string, it is empty. Either way, the query for the
# first letter is the same, and no reset is needed.
#
# The script teaches each rule of the grammar once, then classifies strings
# from the corpus in data/reber-grammar. A string is accepted if the
# automaton reaches the state "end" after its last letter.
#
# Usage: python3 reber-grammar.py [--strings 1000]


import os
import csv
import json
import argparse
from creating_intelligence import Circuit


START = "end"


def read_lines(path):
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(
        description="Reber grammar as a finite automaton in transition memory.")
    parser.add_argument("--strings", type=int, default=1000,
                        help="number of grammatical and of ungrammatical test strings")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, "..", "..", "data", "reber-grammar")

    with open(os.path.join(script_dir, "ReberGrammar.json"), "r") as f:
        config = json.load(f)
    with open(os.path.join(data_dir, "grammar.csv"), newline="") as f:
        rules = [(r["state"], r["letter"], r["next"]) for r in csv.DictReader(f)]

    # Test strings: the end of strings_valid.txt, held out from any future
    # training, and the beginning of strings_invalid.txt
    n = args.strings
    valid = read_lines(os.path.join(data_dir, "reber.txt"))[-n:]
    invalid = read_lines(os.path.join(data_dir, "non-reber.txt"))[:n]

    circuit_instance = Circuit(config)
    run = circuit_instance["function"]      # run(next state, state, letter)

    # Teaching: each rule is presented once. The training cycle's output is
    # fed back, so an empty cycle follows each rule: the fed-back state alone
    # falls below the threshold, and the next rule starts with a clean query.
    for state, letter, nxt in rules:
        run(nxt, state, letter)
        run([], [], [])

    def trace(string):
        states = [run([], START, string[0])[0]]
        states += [run([], [], letter)[0] for letter in string[1:]]
        return states

    def show(state):
        return "-" if state is None else state if isinstance(state, str) else "|".join(state)

    print("Examples (letter:state after the letter, - = no transition):")
    for s in valid[:3] + invalid[:3]:
        states = trace(s)
        verdict = "accepted" if states[-1] == START else "rejected"
        print(f"  {s:12s} {' '.join(f'{l}:{show(q)}' for l, q in zip(s, states))}   {verdict}")
    print()

    # Grammatical and ungrammatical strings alternate, so that every
    # rejected string is followed by a string that must be accepted.
    accepted_valid = accepted_invalid = 0
    for v, i in zip(valid, invalid):
        accepted_valid += trace(v)[-1] == START
        accepted_invalid += trace(i)[-1] == START

    print(f"rules taught:           {len(rules)}")
    print(f"grammatical accepted:   {accepted_valid}/{len(valid)}")
    print(f"ungrammatical rejected: {len(invalid) - accepted_invalid}/{len(invalid)}")
    print(f"accuracy:               "
          f"{(accepted_valid + len(invalid) - accepted_invalid) / (len(valid) + len(invalid)):.3f}")


if __name__ == "__main__":
    main()
