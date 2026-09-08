
### General Information

This Python implementation of the *Creating Intelligence* framework is functionally
equivalent to the [Mathematica](../../mathematica) prototype.

The Topological Assoicative Memory kernel is available in multiple interchangeable versions:

- memory_python.py: A direct implementation of the core memory algorithm, serving as a starting point for derived work.
- memory_c_ffi.py: Wrapper for the Standard C memory kernel (**recommended**).



### Software Design Notes

This package uses a data-driven architecture inspired by the Clojure language.

The memory backend, data encoders and decoders, circuit components and their plugins
are all defined through factory functions that compile a configuration dictionary into
a dispatch dictionary.

This paradigm entirely avoids class hierarchies, inheritance, and standard class constructors.

The compiler uses right-to-left sequential overriding using Python's dictionary union operator (|):
Configuration defaults are overwritten by user inputs, which are overwritten by component-specific hard requirements.

The internal state of each module instance is encapsulated in the local variables within
its factory function's scope. Nested functions (closures) mutate this enclosed state.
The dispatched dictionary exposes a public interface to the module's state.

Users can easily define custom circuit modules and patch them into the package's namespace.


