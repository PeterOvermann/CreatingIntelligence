
CIRCUIT COMPONENTS

# noise

<img width="130" alt="image" src="img/noise.png"><br>

A circuit component that generates pseudo-random sparse sets.

## Details and properties

- The `noise` component has no input and returns one output block.
- The dimension and population of the generated representations is governed by the outbound slot's hyperparameters.

<br>

| Property        | Default | Description |
|:------------|:-----:|:----------------------------------------|
| `send`        | *required*     |  a single output slot  |


Use standard [style options](components.md) to customize the component's appearance in circuit schematics.


## Additive noise

Add random noise to the input signal:


```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1]},
	{"component": "noise", "send": [2]},
	{"component": "output", "receive": [[1, 2]]}
  ]}
```

<img width="130" alt="image" src="img/noise_output.png"><br>


## Subtractive noise

Use an inhibitory pathway to make the noise subtractive:


```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1]},
	{"component": "noise", "send": [2]},
	{"component": "output", "receive": [[1, {"slot": 2, "tags": ["inhibit"]}]]}
  ]}
```

<img width="130" alt="image" src="img/inhibit_noise.png"><br>



## Source code

*from circuits.py insert noise*



