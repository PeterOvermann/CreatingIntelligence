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


# Generalization in hetero-associative memory: a query retrieves a pattern
# that was never stored and is not a union of stored patterns.
#
# Memory: N = 1000, P = 10, identical input and output dimensions. Every
# pattern is a bundle of SHRs with P = 5 each:
#
#   inputs    A = 1..5      B = 6..10     C = 11..15
#   outputs   p = 101..105  q = 106..110  r = 111..115  t = 116..120
#
# Two write operations (> a -> b), then three queries (> a, followed by the
# result):
#
#   AB -> pqr
#   AC -> pqt
#
#   AB          retrieves pqr
#   AC          retrieves pqt
#   3..15       retrieves pq      never stored, and no union of stored outputs
#
# The query 3..15 contains 8 elements of AB (3..10) and 8 elements of AC
# (3..5, 11..15), both above the matching threshold T = 7. Each of these
# subsets fully supports pq, so the match is their union, the whole query.
# r and t are supported by only one of the two subsets and are dropped: the
# query retrieves the part of the outputs on which both associations agree.
#
# The outputs are bundles of three SHRs, so that the shared part pq fills
# the kWTA quota of P = 10 elements. If the shared part is smaller than P,
# the remaining places go to the elements of only one output, which tie, and
# the result is the union of both outputs.
#
# Usage: python3 generalization.py


from creating_intelligence import Memory


M = Memory({"A_parameters": [1000, 10], "B_parameters": [1000, 10]})


def fmt(s):
    """Elements in ascending order."""
    return " ".join(map(str, sorted(s))) or "{}"


def store(a, b):
    M["store"](a, b)
    print(f"> {fmt(a):26s}->  {fmt(b)}")


def retrieve(a):
    print(f"> {fmt(a)}")
    print(f"  {fmt(M['retrieve'](a))}")


print("# store")
store([1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
      [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115])
store([1, 2, 3, 4, 5, 11, 12, 13, 14, 15],
      [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 116, 117, 118, 119, 120])

print()
print("# retrieve")
retrieve([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
retrieve([1, 2, 3, 4, 5, 11, 12, 13, 14, 15])
retrieve([3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15])

M["clear"]()
