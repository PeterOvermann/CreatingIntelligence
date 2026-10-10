#!/usr/bin/env bash
# dev_build.sh - development build of creating_intelligence without setup.py.
#
# NOT the regular way to install the package: use setup.sh (macOS/Linux) or
# setup.bat (Windows). This script is for quick builds while working on the
# code, e.g. in sandboxes, and installs nothing.
#
#   1. compiles ../c/memory.c into a shared library (libmemory.so)
#   2. assembles the Python package next to it
#   3. smoke-tests both backends (C and pure Python), if the runtime
#      dependencies are available; otherwise warns and skips the test
#
# Usage:  ./dev_build.sh [OUT_DIR]          (default: build/local, gitignored)
# Env:    PYTHON (default python3), CC (default gcc),
#         CFLAGS (default -O3 -Wall -Wextra)
# Then:   export PYTHONPATH="<OUT_DIR>"
#
# Linux and macOS. Does not create a venv: activate an environment with the
# dependencies first (e.g. ~/.ci from setup.sh).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
C_DIR="$SCRIPT_DIR/../c"
PKG_SRC="$SCRIPT_DIR/creating_intelligence"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
OUT_DIR="$(mkdir -p "${1:-$SCRIPT_DIR/build/local}" && cd "${1:-$SCRIPT_DIR/build/local}" && pwd)"
PKG_OUT="$OUT_DIR/creating_intelligence"

CC="${CC:-gcc}"
CFLAGS="${CFLAGS:--O3 -Wall -Wextra}"
PYTHON="${PYTHON:-python3}"
PY_FILES=(__init__.py circuits.py memory_c_ffi.py memory_python.py)

# Start from an empty package dir so no stale files survive a rebuild.
rm -rf "$PKG_OUT"
mkdir -p "$PKG_OUT"

# 1. Shared library. The loader searches the package dir for libmemory<suffix>
#    over importlib.machinery.EXTENSION_SUFFIXES, which contains plain ".so"
#    on both Linux and macOS.
echo "[1/3] Compiling libmemory.so"
# shellcheck disable=SC2086  # CFLAGS is intentionally word-split
"$CC" $CFLAGS -fPIC -shared -I"$C_DIR" "$C_DIR/memory.c" \
    -o "$PKG_OUT/libmemory.so" -lm

# 2. Python package
echo "[2/3] Copying package files"
for f in "${PY_FILES[@]}"; do
    cp "$PKG_SRC/$f" "$PKG_OUT/"
done

# 3. Smoke test, only if every package in requirements.txt can be imported
#    (distribution names equal module names for all current entries).
echo "[3/3] Smoke-testing backends"
MISSING=$("$PYTHON" - "$REQUIREMENTS" <<'EOF'
import importlib.util, re, sys
names = []
for line in open(sys.argv[1]):
    line = line.split("#")[0].strip()
    if line:
        names.append(re.split(r"[<>=!~;\[ ]", line, maxsplit=1)[0])
print(", ".join(n for n in names if importlib.util.find_spec(n) is None))
EOF
)

if [[ -n "$MISSING" ]]; then
    echo "======================================================================"
    echo " "
    echo "WARNING: Smoke test skipped. The build is complete, but this Python"
    echo "lacks runtime dependencies of creating_intelligence:"
    echo "  python:  $(command -v "$PYTHON" || echo "$PYTHON")"
    echo "  missing: $MISSING"
    echo " "
    echo "Activate an environment that has them and rerun this script, e.g.:"
    echo "  source ~/.ci/bin/activate          # venv created by setup.sh"
    echo "or install them into this Python:"
    echo "  $PYTHON -m pip install -r $REQUIREMENTS"
    echo " "
    echo "======================================================================"
else
    # Run each backend explicitly, outside the repo, so a failing C build
    # cannot fall back silently. The location check guards against an
    # installed copy (e.g. setup.sh's editable install) shadowing the build.
    for backend in c_ffi python; do
        (cd /tmp && PYTHONPATH="$OUT_DIR" MEMORY_BACKEND="$backend" \
            "$PYTHON" - "$PKG_OUT" <<'EOF'
import os, random, sys
import creating_intelligence as ci

loaded = os.path.dirname(os.path.realpath(ci.__file__))
expected = os.path.realpath(sys.argv[1])
assert loaded == expected, f"imported {loaded}, expected {expected}"

m = ci.Memory({"A_parameters": (1000, 20), "B_parameters": (1000, 20)})
rng = random.Random(1)
pairs = [(sorted(rng.sample(range(1, 1001), 20)),
          sorted(rng.sample(range(1, 1001), 20))) for _ in range(50)]
for a, b in pairs:
    m["store"](a, b)
ok = sum(m["retrieve"](a) == b for a, b in pairs)
assert ok == len(pairs), f"recalled {ok}/{len(pairs)}"
print(f"      {ci.backend:6s} ok  ({ok}/{len(pairs)} pairs recalled)")
EOF
        )
    done
fi

echo
echo "Built in: $OUT_DIR"
echo "Use with: export PYTHONPATH=\"$OUT_DIR\""
