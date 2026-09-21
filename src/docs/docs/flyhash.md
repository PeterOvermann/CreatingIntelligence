
ENCODERS & DECODERS

# flyhash

<img width="130" alt="image" src="img/flyhash.png"><br>

Encodes dense vector data as Sparse Distributed Representations (SDRs)
using the classic flyhash algorithm.

See also: https://creatingintelligence.org/#sdr-encoders

## Details

- Encoder plugin for the [`input`](input.md) component.
- Encodes dense, real-valued vectors to SDRs.
- Maps similar vectors to similar SDRs.


## Flyhash encoding


The following circuit encodes dense vectors as SDRs:


```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "plugin": "flyhash", "send": [1]},
	{"component": "output", "receive": [1]}
  ]}
```

<img width="130" alt="image" src="img/input_flyhash.png"><br>

