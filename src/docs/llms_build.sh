#!/bin/bash

# Resolve the absolute path to the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Hardcode the source directory to 'docs' relative to the script directory
SRC="$(cd "$SCRIPT_DIR/docs" &> /dev/null && pwd)"
if [ -z "$SRC" ]; then
    echo "Error: Source directory 'docs' not found relative to script."
    exit 1
fi

# Navigate up two levels to reach the project root
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &> /dev/null && pwd)"
DEST_DIR="$PROJECT_ROOT/docs"
OUT_FILE="$DEST_DIR/llms-full.txt"

# Define Python sources directory exactly as in the HTML build script
PY_SRC_DIR="$SCRIPT_DIR/../python/creating_intelligence"

mkdir -p "$DEST_DIR"
> "$OUT_FILE"

# 1. Append the manuscript (ci.txt) at the very top
if [ -f "$SCRIPT_DIR/llms-ci.txt" ]; then
    echo -e "# Source: Creating Intelligence (Manuscript)\n" >> "$OUT_FILE"
    cat "$SCRIPT_DIR/llms-ci.txt" >> "$OUT_FILE"
    echo -e "\n\n" >> "$OUT_FILE"
else
    echo "Warning: llms-ci.txt not found next to the build script in $SCRIPT_DIR"
fi

# Generate Python Snippet Preprocessor
cat << 'EOF' > /tmp/inject_snippets.py
import sys, re, os, ast

py_dir = sys.argv[2]
with open(sys.argv[1], "r", encoding="utf-8") as f:
    content = f.read()

def replacer(match):
    py_file = match.group(1)
    target = match.group(2)
    py_path = os.path.join(py_dir, py_file)
    
    try:
        with open(py_path, "r", encoding="utf-8") as pf:
            code = pf.read()
        
        for node in ast.parse(code).body:
            if getattr(node, 'name', None) == target:
                snippet = ast.get_source_segment(code, node)
                return f"```python\n{snippet}\n```"
                
        return f"<!-- Target '{target}' not found in {py_file} -->\n{match.group(0)}"
    except Exception as e:
        return f"<!-- Error processing {py_file}: {e} -->\n{match.group(0)}"

# Replace the insertion markers with the actual code snippets
print(re.sub(r'\*from\s+([a-zA-Z0-9_.-]+)\s+insert\s+([a-zA-Z0-9_]+)\*', replacer, content))
EOF

# 2. Process and append README.md
if [ -f "$SRC/README.md" ]; then
    echo -e "# Source: README.md\n" >> "$OUT_FILE"
    python3 /tmp/inject_snippets.py "$SRC/README.md" "$PY_SRC_DIR" >> "$OUT_FILE"
    echo -e "\n\n" >> "$OUT_FILE"
else
    echo "Warning: README.md not found in $SRC"
fi

# 3. Extract markdown filenames and process them sequentially
if [ -f "$SRC/_sidebar.md" ]; then
    FILES=$(sed -n 's/.*(\([^)]*\.md\)).*/\1/p' "$SRC/_sidebar.md")
    
    for file in $FILES; do
        if [ "$file" = "README.md" ]; then
            continue
        fi
        
        if [ -f "$SRC/$file" ]; then
            echo -e "# Source: $file\n" >> "$OUT_FILE"
            python3 /tmp/inject_snippets.py "$SRC/$file" "$PY_SRC_DIR" >> "$OUT_FILE"
            echo -e "\n\n" >> "$OUT_FILE"
        else
            echo "Warning: $file listed in _sidebar.md but not found in$SRC."
        fi
    done
else
    echo "Warning: _sidebar.md not found in $SRC."
fi

# 4. Append full Python source files
for py_file in "circuits.py" "memory_python.py"; do
    full_py_path="$PY_SRC_DIR/$py_file"
    if [ -f "$full_py_path" ]; then
        echo -e "# Source: $py_file (Full Source)\n" >> "$OUT_FILE"
        echo -e "\`\`\`python" >> "$OUT_FILE"
        cat "$full_py_path" >> "$OUT_FILE"
        echo -e "\n\`\`\`\n\n" >> "$OUT_FILE"
    else
        echo "Warning: $py_file not found in$PY_SRC_DIR."
    fi
done

echo "Successfully generated combined documentation at $OUT_FILE"