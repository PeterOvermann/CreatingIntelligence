
GETTING STARTED

# Installation

See also: [Quickstart](quickstart.md)



## PyPI built distribution



```python
pip install creating-intelligence
```


## Build from source



```bash
git clone https://github.com/peterovermann/creatingintelligence
creatingintelligence/src/python/setup.sh
```

Building the package from source requires a C development environment.


## Optional components

Graphviz (*dot*) is required for advanced circuit schematics. If it is not present at runtime, visualization features will use a fallback layout.

Install Graphviz manually if needed:

  - **Windows:** winget install Graphviz.Graphviz
  - **macOS:** brew install graphviz
  - **Ubuntu/Debian:** sudo apt-get install graphviz
  - **Fedora:** sudo dnf install graphviz
  - **Arch:** sudo pacman -S graphviz



