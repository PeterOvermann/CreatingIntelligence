
### Build and Installation Instructions

Run `setup.sh` to create a virtual environment `~/.ci` and build the *creating_intelligence* package.

### Memory Backend Configuration

By default, the package uses the performance-optimized C memory backend. Switch to an alternative
backend version by placing a configuration file `\.env` at the root of this repository. This environment setting selects the native Python implementation:

```
MEMORY_BACKEND="python"
```

