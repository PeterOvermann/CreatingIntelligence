CIRCUIT CONFIGURATION

# Design Principles

This page collects the design principles and design patterns for building systems
with the Creating Intelligence framework. The reference pages
for [circuits](circuits.md), [components](components.md) and
[pathways](pathways.md) document what the framework offers. Here we describe how to use it well.

See also: https://creatingintelligence.org/#circuits


## Programs and circuits

### The circuit is the program

The framework has no procedural layer. There are no instructions, loops or
branches that steer data between components. Behavior arises from the
circuit's topology and from the components' internal rules. Control flow is
expressed through data conditions: pathway merging options (`veto`,
`mandatory`, `priority`, `dependency`, `fallback`, `barrier`), population
thresholds, update rules, and feedback loops. Code outside the circuit should
do no more than feed inputs and read outputs. If a design needs driver logic
to decide when or where data flows, that logic is a missing part of the
circuit and should eventually move into it.

### JSON dataflow descriptions

A program is represented by a JSON dataflow description, or the equivalent
Python dictionary. The description lists the components with their `send`
and `receive` slots, the hyperparameters of each pathway, and global options.
This format is human-readable, can be rendered as circuit schematics, and
serves as the exchange format between the Python and Mathematica versions. It
is also a format that generative search can operate on. A design
is complete when it can be written down in this form.

### Stateful components, stateless pathways

All state lives in components: delayed signals, integrated states, held
values, and associative memory traces. 
Pathways are stateless conduits. They may transform
their payload (permutation, rate limiting, thresholding, multiset and
inhibitory tags) and gate it, but they do not remember what flowed through them
in a previous cycle. Temporal gating is governed by the global clock, not by the
data. If a design needs to remember something from one cycle to the next, this
requires a component, at minimum a [`delay`](delay.md).

### One clock, parallel evaluation

One clock cycle means that every component evaluates its inputs and produces
its outputs once. Each component reads the outputs that the upstream components
produced in the previous cycle (and the current values of the circuit's
inputs), and its own outputs become visible only in the next cycle. The result therefore does not depend on the order in which the
components are evaluated. A cycle can be viewed as parallel execution of
all components. A circuit function call normally runs one cycle. With the
`multiplex` option it runs one cycle per entry of the multiplex pattern,
passing the input on entries marked 1 and empty input on entries marked 0.
This lets an embedded circuit run at a higher rate than its surroundings. With
the `latch` option, a call with all inputs empty runs no cycle at all.
This is the basis for [event-driven processing](#event-driven-processing).

### Shared circuits run in dataflow order

The one and only exception to parallel evaluation is a shared circuit that is embedded
several times within the same circuit. Components are evaluated in the order
in which they appear in the dataflow description, and every embedding calls
the shared instance once. A shared circuit embedded k times therefore runs k
cycles per cycle of the enclosing circuit, and each call sees the state left
behind by the previous call. In the following example, the shared circuit
`LAG` (input → delay → delay → output, registered with
`"options": {"name": "LAG"}`) delays its input by one cycle and is embedded
twice, once for each input:

```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "plugin": "codec", "send": [1]},
	{"component": "input", "plugin": "codec", "send": [2]},
	{"component": "circuit", "plugin": "shared", "name": "LAG",
		"send": [11], "receive": [1]},
	{"component": "circuit", "plugin": "shared", "name": "LAG",
		"send": [12], "receive": [2]},
	{"component": "output", "plugin": "codec", "receive": [11]},
	{"component": "output", "plugin": "codec", "receive": [12]}
  ]}
```

Fed with ("a1", "b1"), ("a2", "b2"), ("a3", "b3"), it returns (None, "a1"),
("b1", "a2"), ("b2", "a3"). The first embedding returns what the second one
received in the previous cycle, and the second returns what the first one
received in the same cycle. Two separate instances would return
(None, None), ("a1", "b1"), ("a2", "b2"). When a shared instance holds state
that the order of calls can affect, such as a delay or a memory that learns,
place the embeddings in the dataflow description in the order in which the
accesses should happen.

### One cycle per hop

Every hop from one component to the next takes one cycle. The [`input`](input.md)
and [`output`](output.md) gateways are the exception: they pass data without
delay. A chain input → k components → output delays the signal by k − 1 cycles,
so a single `delay` between input and output does not delay at all. Embedding is
transparent: a `circuit` component that wraps a chain of k components delays the
signal exactly like that chain. Count hops when signals from different paths must
meet in the same cycle, and when estimating how long a feedback loop takes to
respond.


### Event-driven processing

Many signals are events: they occur on some cycles and are empty on others.
The event-driven paradigm in this framework is to skip empty inputs, not to
hold the last input. A component that receives nothing leaves its state
unchanged, as if the cycle had not happened, so an empty cycle neither
overwrites, decays nor advances it. At the circuit level, including embedded
circuits, this is realized with the `latch` option. A latched circuit skips
every cycle in which all of its inputs are empty: nothing is evaluated, and
its clock does not advance. So delays, gating and multiplexing progress only on
cycles with input. A sparse input stream therefore has no gaps inside the latched
circuit. 

One consequence: a latched circuit cannot run on internal feedback
alone, so generative loops that produce output from empty input must not be
latched.

### Data conditions

Prefer data-dependent conditions over clock-based schedules. The framework
offers temporal gating of pathways and the `multiplex` option, but a design
that routes signals by clock phase hard-codes a timetable that has to match
the timing of the data. Conditions on the data itself (an empty or non-empty
pathway, a population threshold, a merge tag such as `priority` or
`dependency`) adapt to the actual flow of events. Use clock patterns only
where a fixed rhythm is genuinely part of the design, for example an
embedded module deliberately running at a different rate than its
surroundings.


## Components and plugins

### Components encapsulate basic operations

A component should perform one basic operation: delaying or integrating a
signal, storing and retrieving associations, encoding or decoding. Complex
behavior emerges from wiring simple components together, not from building
complex components. Components should be explainable and reusable, which
keeps the structure of a system visible in its schematics. When a component's
description needs several sentences joined by "and then", it is probably a
circuit.

### One memory per component

A component encapsulates at most one topological memory instance. Memory
components are drawn as squares and dataflow components as circles: each
square in a schematic stands for exactly one memory. A function that needs two
memories, for example an item store and a sequence memory, is a subcircuit of
two components and should be packaged as an embedded circuit. This keeps learning
local and inspectable: every stored association belongs to one identifiable
component.

### Guard inputs, not outputs

Each component is responsible for protecting its inputs and its internal state
from overflow and runaway activity. Storage and retrieval in topological memory
scale with the square of the input population, O(P²), so an oversized input
is costly and risks combinatorial over-activation. 

Components guard themselves
with their own options: `threshold` (minimum input population), `rate_limit`
(maximum input population, enforced by subsampling), `decimate`, `capacity`
and `decay` for integrated states, and population bounds on learning.
Components normally do not restrict their output population. A memory query
may legitimately return a superposition of many items that together exceed
the system's sparsity envelope, and that superposition carries information,
namely the set of alternatives. It is up to the receiver, or to the pathway
(`rate_limit`, `threshold`, kWTA tags), to decide how much of it to take.

### Fixed block signature

Each component instance has a fixed number of input slots and output slots,
one per block of its block-coded input and output. Optional blocks are not
allowed: every block is always present, and the absence of a signal is
expressed by an empty set on that block, never by a missing block. A
component whose behavior would depend on whether a block is connected should
instead take an option, or be split into separate components. This keeps
dataflow descriptions unambiguous and lets the framework check every
component's signature connectivity when the circuit is compiled.

### Options and plugins configure components

The functionality of a component is controlled by its options and by the
choice of plugin. Component-level options are passed through into the
plugin: the plugin factory receives the component's full configuration,
including the hyperparameters of its blocks. A plugin's own settings are
therefore written on the component, for example the number of categories of
the `category` encoder on its `input` component:

```json
{"component": "input", "plugin": "category", "send": [1], "categories": 20}
```

Plugins read the options they need and ignore the rest. Choose option names
that are unambiguous within a component and its plugins.

### Custom components

New components can be created as needed and plugged into the framework. A
component is a factory function that receives its configuration (including
the hyperparameters of its `send` and `receive` blocks) and returns a dispatch
dictionary with its `function` and optional properties such as `clear` and
visualization settings. The framework uses closures and configuration dictionaries
instead of class hierarchies: inserting the factory into the package namespace
makes it available to circuit descriptions by name. A new component should
still follow the principles on this page: one basic operation, at most one
memory.

### Custom plugins

The same mechanism applies to plugins: encoders and decoders for [`input`](input.md) and
[`output`](output.md), update rules for [`auto`](auto.md), [`delay`](delay.md) and [`temporal`](temporal.md), and the plugins of
the [`circuit`](circuit.md) component that connect embedded circuits 
(`shared`, `file`).
Plugins extend a base component while inheriting its properties and
hyperparameters. Prefer a plugin over a new component when the change concerns
only how a component updates its state, or when the plugin's mechanism may be reusable across multiple components.

### Shared instances live in shared circuits

A component instance appears exactly once in a dataflow description. If the
same instance is needed in several places, for example one item store used by
several decoding stages, wrap it in a circuit, instantiate that circuit under a
`name`, and embed it wherever it is needed with the [`circuit`](circuit.md) component and
the `shared` plugin. Accesses to the shared instance happen in the order of
the embeddings in the dataflow description, so they remain deterministic (see
[Shared circuits run in dataflow order](#shared-circuits-run-in-dataflow-order)).

```json
{ "hyperparameters": {"default": [1000, 10]},
  "dataflow": [
	{"component": "input", "send": [1]},
	{"component": "circuit", "plugin": "shared", "send": [11],
		"receive": [1], "name": "ITEMS"},
	{"component": "output", "receive": [11]}
  ]}
```

The hyperparameters of a shared circuit must match the slots it is connected
to. Do not share by default: instances that learn different things in
different places are better kept separate (see
[One memory per component](#one-memory-per-component)).


## Representations

### Blocks are pathways

Each block of a block-coded representation maps to its own pathway: a list of
slots in `send` or `receive` denotes disjoint blocks, each with its own
hyperparameters. Block coding is therefore hard-wired. Use it for a fixed,
small number of roles that are known at design time, such as the three parts
of a triple, the rows of a frame, the token and the label of a labeled
hyperedge, or different sensory modalities. A memory component treats its
blocks as one contiguous set, so storing a block-coded pattern links
information across the blocks.

### No blocks for variable-length sequences

Do not use blocks to encode positions in a sequence of variable length.
Position blocks are hard-wired, so they cap the sequence length at design time,
and they force every stage to route items by position. Sequences are temporal
processes in this framework. Encode order with permutations (the
[`permutation`](permutation.md) update rule, or `permute`-tagged pathways), with pointer chains,
or by nesting: a chunk replaced by its label becomes a single item in a longer
sequence.

### Permutations are never inverted

A permutation is a one-way, hard-wired shuffling of signals along a pathway,
and each permuted pathway has its own unique mapping. Designs must not rely on
inverse permutations, which assume a bidirectional symmetry with no neural
counterpart. When information is needed in its earlier form, keep or restore
the earlier signal instead of inverting the permuted one. When a permuted
signal must be compared with known items, permute the candidates forward along
the same mapping and compare the results.

### No start or end markers

Avoid fixed start-of-sequence or end-of-sequence tokens, which are a common device in
language models. A fixed code that occurs in many stored patterns becomes a
memory hub: its element pairs are written by every pattern and saturate, and
the marker alone can exceed the matching threshold and pull up unrelated
patterns or cause ties during memory retrieval. The same applies to any code shared by construction,
such as position tags, length tags or depth codes. Better alternatives
include:

- marking the first item of a sequence by routing it through its own
  permutation
- detecting ends from the data, for example an empty retrieval or a failed
  extension
- using a unique label per structure rather than a shared marker

### Memory limits the size of bundles

A bundle of seven plus or minus two SHRs (a hyperassociation) is a legitimate pattern to store in memory, and it can be used to query the memory after applying proportional decimation. Beyond this practical limit, the number of retrieval attempts needed rapidly increases.

## Memory and learning

### Binary storage does not represent probabilities

Topological memory stores the presence of connections, not their strength.
Writing an association once or a hundred times leaves the same memory state,
and storage deduplicates by design. Binary storage is also a prerequisite for
auto-associative memory: counters would let self-correlations inflate until
the memory collapsed into an identity operator. Probabilities and preferences
therefore do not live in the stored weights. Instead, they arise from network
activity:

- superpositions of alternatives retrieved together
- votes of competing signals aggregated in multisets and resolved by kWTA
- stochastic subsampling, which chooses among several valid matches with
  probabilities that follow the number of matching elements

Do not try to encode frequencies by repeated storage.

### The default matching threshold is tuned for SHRs

The default pattern matching threshold `T` is computed from the memory's
hyperparameters so that a memory filled to capacity with random SHRs of
uniform population produces no false positive matches. It is the right choice
for symbolic tokens and their bundles. Overlapping SDRs, which encode
similarity through shared elements, may require custom settings: an explicit
relative `threshold` decides how much overlap counts as "the same". For
example, it sets how far apart two color hues must be to receive different
tokens.

### Exact matching with `fraction` 1.0

The `fraction` option sets the share of the query population that must match.
With `fraction` 1.0, every element of the query must be part of the match:
the noise-removing iterations of the retrieval algorithm are skipped, and a
query either matches as a whole or returns an empty result. This is typically
used for heteroencoding combinations of symbolic tokens, such as bigrams or
chunks, where each distinct combination must map to its own token. Under the
default threshold, a stored pair would also match a query that shares only one
of its two tokens, because one SHR alone exceeds `T`. Use the default threshold
where noise tolerance or similarity is the point, for example when clustering
SDRs.

### Always learning

For heteroassociations (including temporal associations), storing every observed association, even when the
prediction was correct, is typically a better approach than learning only
from failed predictions. Storage is idempotent, so repeating an identical
association costs nothing. When the context varies, each new instance adds
links from other element pairs of the context to the same target, which
broadens the base the association rests on. Learning only on failure records
only the context at the moment of failure. Later successes then rest on a
narrow subset of elements that is easily lost when the context varies or
decays. The [`temporal`](temporal.md) and [`predictor`](predictor.md) components always learn for this reason.


## Coding rules

### Sets and multisets

All signals are sparse sets over a universe of N elements, numbered 1 to N.
There are three forms:

- **Sets:** sorted lists of distinct positive integers.
- **Multisets:** sorted lists of positive integers in which elements may
  occur more than once.
- **Inhibitory multisets:** multisets that may also contain negative
  integers, the inhibitory counterparts of the positive elements. After
  aggregation, an element never occurs with both signs at once, because
  excitatory and inhibitory counts cancel out.

The element 0 never appears in any of these data structures. It carries no meaning
and would be indistinguishable from its own negation. Block-coded signals are
joined by offsetting each block by the dimensions of the blocks before it.

### Sorted output, unchecked input

Components emit sorted lists. Receivers rely on this: they do not check
or re-sort their inputs. The guarantee is a contract between components, so
every new component, plugin and encoder must uphold it on every output
block, including empty ones and results assembled from several sources.

### Factory functions, closures, dispatch dictionaries

The software architecture is built entirely on factory functions. A factory
takes a configuration (a Python dictionary, or an `Association` in
Mathematica) and returns a dispatch dictionary: a dictionary of properties and
functions, typically including the component's `function` and a `clear`
destructor. State lives in closures inside the factory, captured by the
returned functions, not in objects. The same pattern runs through all
layers: `Circuit`, components, plugins and the `Memory` backend.

### No class hierarchies

There are no classes and no inheritance. Variants are created by passing a
different configuration or plugin to the same factory, and plugins extend a
component by merging their dispatch dictionary into the component's. This
style is related to Clojure's data-oriented programming: plain maps as
configuration and as return values, functions as first-class values, and
composition instead of type hierarchies. Unlike idiomatic Clojure, which
favors immutable values and keeps mutable state in explicit reference types,
the closures here hold mutable state directly. The closest classic match is
the message-passing style of *Structure and Interpretation of Computer
Programs*, where a constructor returns a dispatch procedure that closes over
local state.
