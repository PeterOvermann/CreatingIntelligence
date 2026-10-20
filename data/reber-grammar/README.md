# Reber Grammar

Grammatical and ungrammatical strings of the finite-state grammar introduced by
Reber (1967) for artificial grammar learning experiments, in the version used by
Cleeremans, Servan-Schreiber and McClelland (1989).


## Files

| File | Content |
|:-----|:--------|
| `grammar.csv` | the grammar as transition rules: `state`, `letter`, `next` |
| `reber.txt` | 100,000 grammatical strings, one per line |
| `non-reber.txt` | 10,000 ungrammatical strings, one per line |
| `generate.py` | generates the two string files from `grammar.csv` |


## Grammar

Strings consist of the letters T, P, S, X and V, framed by B and E. The grammar
has six inner states, 0 to 5, and the state `end`:

| state | letter | next |
|:-----:|:------:|:----:|
| end | B | 0 |
| 0 | T | 1 |
| 0 | P | 2 |
| 1 | S | 1 |
| 1 | X | 3 |
| 2 | T | 2 |
| 2 | V | 4 |
| 3 | X | 2 |
| 3 | S | 5 |
| 4 | P | 3 |
| 4 | V | 5 |
| 5 | E | end |

The grammar is cyclic: every string starts and ends in the state `end`. A
string is grammatical if it leads from `end` back to `end`. Consecutive strings
therefore form a continuous stream, as in the prediction task of Cleeremans et
al. Each of the letters T, P, S, X and V labels two different transitions, so
the next letter depends on the current state, not only on the current letter.
The current letter together with the preceding one determines the state.


## Generation

`generate.py` uses a fixed random seed:running it reproduces the files.

**Grammatical strings** are random walks from `end` back to `end`. At each
state, the two outgoing transitions are chosen with equal probability. The
strings are independent draws, listed in the order they were generated, with
repetitions: short strings recur often, reflecting their probability under the
grammar. Every letter between B and E is one of two equally likely choices, so
a string of length $n$ has probability $2^{-(n-2)}$. The file is a fixed,
reproducible training stream: experiments that read it in order see the same
sequence of strings, with the same frequencies.

**Ungrammatical strings** are derived from grammatical strings by replacing one
inner letter (any letter except B and E) with a different letter from T, P, S,
X, V, such that the result is no longer grammatical. This follows the common
construction of ungrammatical test items in artificial grammar learning. The
source strings are generated separately, so the two files are independent
samples.


## Statistics

| | |
|:--|:--|
| grammatical strings | 100,000 |
| distinct grammatical strings | 2,425 |
| string length | 5 to 40, mean 8.0 |
| most frequent strings | BTXSE (12.6%), BPVVE (12.3%), BTSXSE (6.3%) |
| ungrammatical strings | 10,000 |
| distinct ungrammatical strings | 2,589 |


## Datasets

For grammar learning, use the beginning of `reber.txt` for training and
hold out the end for testing, for example the first 90,000 strings for
training and the last 10,000 for testing. Because the string distribution is
dominated by short strings, almost all held-out strings also occur in the
training part. In the split above, only 129 of the 10,000 held-out strings do
not. To test generalization to unseen strings, select the held-out strings that
do not occur in the training part.


## References

Reber, A. S. (1967). Implicit learning of artificial grammars. *Journal of
Verbal Learning and Verbal Behavior*, 6(6), 855–863.

Cleeremans, A., Servan-Schreiber, D., & McClelland, J. L. (1989). Finite state
automata and simple recurrent networks. *Neural Computation*, 1(3), 372–381.
