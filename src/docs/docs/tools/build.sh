#!/bin/bash

# Resolve the absolute path to the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

# Navigate up one level from tools/ to reach src/docs/docs
SRC="$(cd "$SCRIPT_DIR/.." &> /dev/null && pwd)"

# Navigate up four levels from tools/ to reach the project root, then set DEST
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." &> /dev/null && pwd)"
DEST="$PROJECT_ROOT/docs/docs"

# Define Python sources directory
PY_SRC_DIR="$SCRIPT_DIR/../../../python/creating_intelligence"

# 1. Create target directories and migrate assets
mkdir -p "$DEST"
cp -r "$SRC/img" "$DEST/" 2>/dev/null

# 2. Extract CSS
awk '/<style>/{flag=1; next} /<\/style>/{flag=0} flag' "$SRC/index.html" > "$DEST/style.css"

# 3. Generate Sidebar HTML
# Rewrites markdown links to HTML, and wraps leading symbols before &emsp; in a fixed-width span
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
  <!-- Load base Docsify theme -->
  <link rel="stylesheet" href="//cdn.jsdelivr.net/npm/docsify/lib/themes/vue.css">
  <!-- Load extracted custom styles -->
  <link rel="stylesheet" href="style.css">
  <!-- Static Layout Fixes -->
    <style>
      .content {
        overflow-y: auto;
        height: calc(100vh - 40px);
        top: 40px;
        left: 300px;
      }
      .sidebar {
        overflow-y: auto;
        height: calc(100vh - 40px);
        top: 40px;
        padding-top: 15px;
        width: 300px; 
      }
      .sidebar-icon {
        display: inline-block;
        width: 1.5em;
        text-align: center;
        margin-right: 0.25em;
      }
      /* Inject Pandoc Syntax Highlighting CSS */
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

# Inject the compiled sidebar directly into the template
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
  
  <!-- Mermaid Support -->
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs";
    mermaid.initialize({ startOnLoad: true });
    
    // Map Pandoc's codeblock output to Mermaid's expected DOM structure
    document.querySelectorAll('pre > code.language-mermaid').forEach(el => {
        const pre = el.parentElement;
        const div = document.createElement('div');
        div.className = 'mermaid';
        div.textContent = el.textContent;
        pre.replaceWith(div);
    });
  </script>
</body>
</html>
EOF

# 4.5 Generate Python Snippet Preprocessor
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

# Match exactly: *from [filename.py] insert [target]*
print(re.sub(r'\*from\s+([a-zA-Z0-9_.-]+)\s+insert\s+([a-zA-Z0-9_]+)\*', replacer, content))
EOF

# 5. Process Content Files
for file in "$SRC"/*.md; do
    filename=$(basename "$file")
    
    # Exclude the raw sidebar source from page generation
    if [ "$filename" = "_sidebar.md" ]; then
        continue
    fi
    
    # Route README.md to index.html, and map all other .md files to .html
    if [ "$filename" = "README.md" ]; then
        outname="index.html"
    else
        outname="${filename%.md}.html"
    fi
    
    # Inject python snippets, rewrite internal links, and compile with Pandoc
    # The autolink_bare_uris extension converts plain URLs to links
    python3 /tmp/inject_snippets.py "$file" "$PY_SRC_DIR" | \
    sed -E 's/\]\(\/?([^)]+)\.md\)/](\1.html)/g' | \
    pandoc -f markdown+autolink_bare_uris -t html \
        --template=/tmp/template.html \
        -o "$DEST/$outname"
done

echo "Static site generated in $DEST"