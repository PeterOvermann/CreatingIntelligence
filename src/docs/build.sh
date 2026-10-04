#!/bin/bash

# Require the source directory as an argument
if [ -z "$1" ]; then
    echo "Usage: $0 <source_directory>"
    exit 1
fi

# Resolve the absolute path to the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Set the source directory from the script argument
SRC="$(cd "$SCRIPT_DIR/$1" &> /dev/null && pwd)"
if [ -z "$SRC" ]; then
    echo "Error: Source directory '$1' not found."
    exit 1
fi

# Navigate up two levels from the new script location to reach the project root
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." &> /dev/null && pwd)"

# Extract the base name of the argument and use it as the final destination directory
TARGET_NAME=$(basename "$1")
DEST="$PROJECT_ROOT/docs/$TARGET_NAME"

# Define LLM output targets based on the dynamic target name
LLM_DEST_DIR="$PROJECT_ROOT/docs"
LLM_OUT_FILE="$LLM_DEST_DIR/llms-${TARGET_NAME}.txt"

# Define the base directory for source code inclusion
BASE_SRC_DIR="$SCRIPT_DIR/.."

# 1. Create target directories and migrate assets
mkdir -p "$DEST"
cp -r "$SRC/img" "$DEST/" 2>/dev/null

# 2. (obsolete)


# 3. Generate Sidebar HTML
sed -E 's/\]\(\/?([^)]+)\.md\)/](\1.html)/g' "$SRC/_sidebar.md" | \
sed -E 's/\[([^&]+)&emsp;/\[<span class="sidebar-icon">\1<\/span>/g' > /tmp/sidebar_temp.md
pandoc /tmp/sidebar_temp.md -o /tmp/sidebar.html

# 4. Construct the Pandoc Template
cat << 'EOF' > /tmp/template.html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>$if(title)$$title$$else$Creating Intelligence &mdash; Documentation$endif$</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <link rel="stylesheet" href="../style.css">
    <style>
      $highlighting-css$
    </style>
</head>

<body>
  <div class="menubar">
    <a href="../index.html" class="menu-item-1">Creating Intelligence</a>
    <div class="menu-group">
      <a href="index.html">Documentation</a>
      <a href="https://github.com/peterovermann/creatingintelligence">GitHub</a>
      <a href="mailto:mail&#64;creatingintelligence&#46;org">Contact</a>
    </div>
  </div>
  <main>
    <aside class="sidebar">
      <h1 class="app-name"><a href="index.html">Documentation</a></h1>
      <div class="sidebar-nav">
EOF

cat /tmp/sidebar.html >> /tmp/template.html

cat << 'EOF' >> /tmp/template.html
      </div>
    </aside>
    <section class="content">
      <article class="markdown-section">
        $body$
      </article>
    </section>
  </main>
  
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
    mermaid.initialize({ startOnLoad: true });
    
    document.querySelectorAll('pre > code.language-mermaid').forEach(el => {
        const pre = el.parentElement;
        const div = document.createElement('div');
        div.className = 'mermaid';
        div.textContent = el.textContent;
        pre.replaceWith(div);
    });
  </script>

  <script>
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        const savedScroll = sessionStorage.getItem('sidebarScrollPosition');
        if (savedScroll !== null) {
            sidebar.scrollTop = parseInt(savedScroll, 10);
        }
        window.addEventListener('beforeunload', () => {
            sessionStorage.setItem('sidebarScrollPosition', sidebar.scrollTop);
        });
    }
  </script>
  
  <script>
    const currentPath = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.sidebar-nav a').forEach(link => {
      if (link.getAttribute('href') === currentPath) {
        link.classList.add('active');
      }
    });
  </script>
</body>
</html>
EOF

# 4.5 Generate Snippet Preprocessor (Shared)
cat << 'EOF' > /tmp/inject_snippets.py
import sys, re, os, ast

base_dir = sys.argv[2]

with open(sys.argv[1], "r", encoding="utf-8") as f:
    content = f.read()

def replacer_func(match):
    rel_path = match.group(1).strip()
    target = match.group(2).strip()
    py_path = os.path.join(base_dir, "python", "creating_intelligence", rel_path)
    
    try:
        with open(py_path, "r", encoding="utf-8") as pf:
            code = pf.read()
        
        for node in ast.parse(code).body:
            if getattr(node, 'name', None) == target:
                snippet = ast.get_source_segment(code, node)
                return f"```python\n{snippet}\n```"
                
        return f"<!-- Target '{target}' not found in {rel_path} -->\n{match.group(0)}"
    except Exception as e:
        return f"<!-- Error processing {rel_path}: {e} -->\n{match.group(0)}"

def replacer_file(match):
    rel_path = match.group(1).strip()
    src_path = os.path.join(base_dir, rel_path)
    
    if rel_path.endswith(".py"):
        lang = "python"
    elif rel_path.endswith(".m"):
        lang = "mathematica"
    elif rel_path.endswith(".c") or rel_path.endswith(".h"):
        lang = "c"
    else:
        lang = ""
    
    try:
        with open(src_path, "r", encoding="utf-8") as pf:
            code = pf.read()
        return f"```{lang}\n{code.strip()}\n```"
    except Exception as e:
        return f"<!-- Error processing {rel_path}: {e} -->\n{match.group(0)}"

# Match: *from [relative/filepath.py] insert [target]*
content = re.sub(r'\*from\s+(.+?)\s+insert\s+([a-zA-Z0-9_]+)\*', replacer_func, content)

# Match: *insert [relative/filepath]*
content = re.sub(r'\*insert\s+(.+?)\*', replacer_file, content)

print(content)
EOF

# 5. Process Content Files for HTML Documentation
for file in "$SRC"/*.md; do
    filename=$(basename "$file")
    
    if [ "$filename" = "_sidebar.md" ]; then
        continue
    fi
    
    if [ "$filename" = "README.md" ]; then
        outname="index.html"
    else
        outname="${filename%.md}.html"
    fi
    
    python3 /tmp/inject_snippets.py "$file" "$BASE_SRC_DIR" | \
    sed -E 's/\]\(\/?([^)]+)\.md\)/](\1.html)/g' | \
    pandoc -f markdown+autolink_bare_uris -t html \
        --template=/tmp/template.html \
        -o "$DEST/$outname"
done

echo "Site generated in $DEST"

# 6. Process LLM Text Generation
mkdir -p "$LLM_DEST_DIR"
> "$LLM_OUT_FILE"

if [ -f "$SRC/README.md" ]; then
    echo -e "# Source: README.md\n" >> "$LLM_OUT_FILE"
    python3 /tmp/inject_snippets.py "$SRC/README.md" "$BASE_SRC_DIR" >> "$LLM_OUT_FILE"
    echo -e "\n\n" >> "$LLM_OUT_FILE"
else
    echo "Warning: README.md not found in $SRC"
fi

if [ -f "$SRC/_sidebar.md" ]; then
    FILES=$(sed -n 's/.*(\([^)]*\.md\)).*/\1/p' "$SRC/_sidebar.md")
    
    for file in $FILES; do
        if [ "$file" = "README.md" ]; then
            continue
        fi
        
        if [ -f "$SRC/$file" ]; then
            echo -e "# Source: $file\n" >> "$LLM_OUT_FILE"
            python3 /tmp/inject_snippets.py "$SRC/$file" "$BASE_SRC_DIR" >> "$LLM_OUT_FILE"
            echo -e "\n\n" >> "$LLM_OUT_FILE"
        else
            echo "Warning: $file listed in _sidebar.md but not found in $SRC."
        fi
    done
else
    echo "Warning: _sidebar.md not found in $SRC."
fi

echo "LLM context generated in $LLM_OUT_FILE"