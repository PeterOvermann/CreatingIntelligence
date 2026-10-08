
CIRCUIT COMPONENTS

# temporal

<img width="240" alt="image" src="img/temporal.png"><br>

Temporal associative memory component.


## Details and properties

- Learns the association of the previous state with the current input.
- Predicts the next input based on the current state.
- Always learns, even when the prediction is correct. This may broaden the base temporal associations.
- A closed feedback loop enables generative behavior.
- Uses update rule plugins to control the mechanics of temporal integration.
- Supports temporal integration of signals across evaluation cycles, governed by update rule plugins.
- With the [`permutation`](permutation.md) update rule, the temporal order of inputs is preserved.
- Supports the same set of update rules as the [`delay`](delay.md) component.
- Controls sparsity through stochastic subsampling mechanisms.  
- Represents the integrated state as a multiset.
- Supports multiple input or output blocks.


<br>

 
| Property        | Default | Description |
|:------------|:-----:|:----------------------------------------|
| `send`        |  *required*    |  `[integer,...]` representing one or more output slots |
| `receive`     |  *required*    |  one or more input slots with pathway tags |
| `plugin`	    | [`replacement`](replacement.md) | update rule, governing the temporal integration logic |  
| `latch`	    | false | whether to skip the update if the input is empty |  
| `threshold`     | 0    |  clear input if relative population is below threshold |
| `rate_limit`    | infinite | subsample input if population exceeds the rate limit |    
| `decay`         | 0    | pre-integration decay (leak rate) |
| `capacity`      | 1    | relative population carried over from previous state (bypassed with default `replacement` plugin) |
| `decimate`      | 1    | proportional stochastic decimation |

<br>

Use standard [style options](components.md) to customize the component's appearance in circuit schematics.



## Temporal associative memory with replacement update

The `temporal` component applies the [`replacement`](replacement.md) update rule by default.
At every timestep, it replaces its internal state with the current input,
bypassing the `capacity` setting. This mechanism directly associates
each signal to the subsequent signal.


```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1]},
	{"component": "temporal", "send": [11], "receive": [1]},
	{"component": "output", "receive": [11]}
  ]}
```

<img width="240" alt="image" src="img/temporal_replacement.png"><br>



## Temporal associative memory with difference update

The [`difference`](difference.md) 
update rule replaces the internal state with 
the symmetric multiset difference of the state and the incoming signal.


```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1]},
	{"component": "temporal", "plugin": "difference", 
		"send": [11], "receive": [1]},
	{"component": "output", "receive": [11]}
  ]}
```

<img width="240" alt="image" src="img/temporal_difference.png"><br>

## Temporal associative memory with complement plugin

```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1]},
	{"component": "temporal", "plugin": "complement", 
		"send": [11], "receive": [1], "capacity": 2},
	{"component": "output", "receive": [11]}
  ]}
```

<img width="240" alt="image" src="img/temporal_complement.png"><br>


## Temporal associative memory with state augmentation

The  [`augmentation`](augmentation.md) update rule plugin
aggregates an orderless temporal state.


```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1]},
	{"component": "temporal", "plugin": "augmentation", 
		"send": [11], "receive": [1], "capacity": 5},
	{"component": "output", "receive": [11]}
  ]}
```

<img width="240" alt="image" src="img/temporal_augmentation.png"><br>



## Temporal associative memory with state permutation

The [`permutation`](permutation.md) update rule plugin accumulates a temporal state by iteratively permuting it at every timestep, encoding the ordering of prior inputs.


```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1]},
	{"component": "temporal", "plugin": "permutation", 
		"send": [11], "receive": [1], "capacity": 2},
	{"component": "output", "receive": [11]}
  ]}
```

<img width="240" alt="image" src="img/temporal_permutation.png"><br>




## Source code

*from circuits.py insert temporal*




