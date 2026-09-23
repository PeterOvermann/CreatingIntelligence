

CREATING INTELLIGENCE

# Documentation


This is a software framework for cognitive computing, based on hyperdimensional sparse representations.

It is used for modeling and simulating spiking neural networks that transmit sparse discrete codes between instances of Topological Associative Memory. In this framework, mathematical sets are the fundamental datatype, representing either Sparse Distributed Representations (SDRs) or Sparse Holographic Representations (SHRs).

## Getting started

[Installation instructions](install.md)

[Quickstart guide](quickstart.md)


## Software architecture

This framework is divided into two layers:

1. **Circuits frontend:** Orchestrates the dataflow between memory instances
2. **Memory backend:** The core topological associative memory algorithm

The Circuits frontend is scripted via JSON configuration files. No programming is required
to set up networks based on standard components. 

The package implements a data-driven software paradigm, using configuration dictionaries
and closures to encapsulate stateful functions. This architecture entirely avoids class hierarchies. Custom circuit components can be plugged into the framework simply by inserting them into the package's namespace.

## Platform support

The Circuits package is available for Python and Mathematica. Both versions are functionally identical.

The Memory backend is implemented in Standard C as a zero-dependency library, and
integrated with Python and Mathematica via foreign function interfaces.

Literal implementations of the core memory algorithm are available for Python and Mathematica, serving as a baseline for derived and experimental memory variants.






