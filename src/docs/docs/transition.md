
CIRCUIT COMPONENTS

# transition

<img width="240" alt="image" src="img/transition.png"><br>

State transition memory component, learning heteroassociations within a shared representational space.


See also: https://creatingintelligence.org/#state-transition-memory


## Details and properties

- Stores heteroassociations A → B, where A and B share the same representational space.
- Receives the teaching signal B from the first half of its `receive` blocks, and the query A from the second half.
- Learns A → B whenever the teaching signal is non-empty. In this case, the teaching signal takes the place of the retrieved pattern (teacher forcing).
- Retrieves a pattern from memory if the teaching signal is empty.
- Uses update rule plugins to control how the retrieved (or taught) pattern interacts with the query.
- Retrieved patterns are valid queries: routed back through a feedback path, the component generates learned trajectories.
- Controls sparsity through stochastic subsampling mechanisms.
- Resolves multiset and inhibitory input prior to processing.
- Supports multiple data blocks. Each output block requires a matching teaching block and a matching query block.

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

Note on matching thresholds: with the default threshold, a query consisting of a single symbolic token (SHR) can match a stored key that bundles several tokens. Where a transition must only fire on the complete key, for example a state combined with an input symbol, set `threshold` to 1.0.



## State transitions with replacement update

As the default update rule for the [`transition`](transition.md) component, `replacement`
returns the retrieved pattern B. In a teaching cycle, it returns the teaching signal.

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

The same feedback path supports learning: presenting A as the query and then B, C, D as consecutive teaching signals stores the entire chain, because each teaching cycle returns the taught pattern, which becomes the next query.


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


## Source code

*from circuits.py insert transition*
