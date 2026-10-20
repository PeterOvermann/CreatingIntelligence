
CIRCUIT COMPONENTS

# transition

<img width="240" alt="image" src="img/transition.png"><br>

State transition memory component, learning heteroassociations within a shared representational space.


See also: https://creatingintelligence.org/#state-transition-memory


## Details and properties

- Stores heteroassociations A → B, where A and B share the same representational space.
- Receives the teaching signal B from the first half of its `receive` blocks, and the query A from the second half.
- Always learns A → B (has no effect if the teaching signal B is empty), then queries the memory with pattern A.
- Uses update rule plugins to control how the retrieved pattern interacts with the query.
- Holds no internal state. 
- Retrieved patterns are valid queries: routed back through a feedback path, the component generates learned trajectories. Without a feedback path, it performs a single transition per query.
- Controls sparsity through stochastic subsampling mechanisms.
- Resolves multiset and inhibitory input prior to processing.
- Supports multiple data blocks. Each output block requires a matching teaching block and a matching query block.
- Takes the memory's query hyperparameters from the query blocks and its target hyperparameters from the output blocks. 
- An output block with population 0 excludes its block from storage and retrieval.

<br>


| Property        | Default | Description |
|:------------|:-----:|:----------------------------------------|
| `send`        |  *required*    |  `[integer,...]` representing one or more output slots |
| `receive`     |  *required*    |  teaching slots followed by query slots, each matching `send`, with optional pathway tags |
| `plugin`	    | `replacement` | update rule |
| `threshold`     | *automatic*    |  relative pattern matching threshold |
| `rate_limit`    | unlimited | subsample the query if it exceeds the specified relative rate limit (applies to storage and retrieval) |
| `decimate`      | 1    | proportional stochastic decimation, applied to the query during retrieval |

<br>

Use standard [style options](components.md) to customize the component's appearance in circuit schematics.

Note on matching: with the default threshold, a single symbolic token (SHR) exceeds the pattern matching threshold. A query can therefore match a stored key with which it shares only one of its tokens. Where a transition must only fire on the complete key, for example a state combined with an input symbol, set `matching` to 1.0. An undefined transition then returns an empty result.



## State transitions with replacement update

As the default update rule for the [`transition`](transition.md) component,
`replacement` returns the retrieved pattern B. In a teaching cycle, it returns
the teaching signal.

In the following circuit, the first input provides the teaching signal and the second input the query. Storing the transitions A → B and B → C, then querying with A, returns B.


```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1], "label": "teach"},
	{"component": "input", "send": [2], "label": "query"},
	{"component": "transition", "plugin": "replacement",
		"send": [11], "receive": [1, 2]},
	{"component": "output", "receive": [11]}
  ]}
```

<img width="240" alt="image" src="img/transition_replacement.png"><br>


## State transitions with complement update

As a plugin for the [`transition`](transition.md) component, the `complement`
update rule removes the query pattern from the retrieved pattern, returning only the elements that the transition adds to the query. This matters where the target pattern overlaps with the query, for instance in production rules operating on bundles.

The following circuit routes the output back to the query input, merging it with external input. Once a query starts the process, the circuit follows the stored transitions A → B → C → D cycle by cycle, and terminates when a state has no stored successor.

The same feedback path supports learning. Presenting A as the query together with B as the teaching signal, followed by C and D as teaching signals alone, stores the entire chain, because each teaching cycle returns the taught pattern, which becomes the next query. The first teaching signal must arrive in the same cycle as the query: a query presented alone retrieves nothing and leaves nothing on the feedback path.

Because the circuit runs on its own output during retrieval, it must not be latched.


```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1], "label": "teach"},
	{"component": "input", "send": [2], "label": "query"},
	{"component": "transition", "plugin": "complement",
		"send": [11], "receive": [1, [2, 11]]},
	{"component": "output", "receive": [11]}
  ]}
```

<img width="240" alt="image" src="img/transition_complement.png"><br>


## Finite automata with block-coded queries

A deterministic finite automaton maps the current state S and an input symbol a to the next state S'. The query combines S and a, either as a bundle in a single block or as two disjoint blocks. In the block-coded form, the teaching signal is S' with an empty symbol block.

The following circuit uses the block-coded form. Its two output blocks are paired with a state block and a symbol block. The symbol's teaching block is supplied by an `empty` component, and the symbol's output slot 12 is declared with population 0, so that the memory stores and retrieves the state block only. The next state is fed back to the query's state block, where it is merged with the start state input. `threshold` 1.0 ensures that an undefined transition returns an empty result and halts the automaton.

To run the automaton, present the start state together with the first symbol and, while teaching, the next state. From then on, present one symbol per cycle, with the next state as the teaching signal while teaching and without it afterwards. The circuit is latched, so cycles without input are skipped: on an unlatched cycle without a symbol, the fed-back state alone would retrieve the superposition of all its successors.


```json
{ "options": {"latch": true},
  "hyperparameters": {"default": [2000, 10], "12": [2000, 0]},
  "dataflow": [
	{"component": "input", "send": [1], "label": "S`"},
	{"component": "input", "send": [3], "label": "S"},
	{"component": "input", "send": [4], "label": "a"},
	{"component": "empty", "send": [2]},
	{"component": "transition", "send": [11, 12],
		"receive": [1, 2, [3, 11], 4], "threshold": 1.0},
	{"component": "output", "receive": [11]}
  ]}
```

<img width="240" alt="image" src="img/transition_dfa.png"><br>


## Source code

*from circuits.py insert transition*
