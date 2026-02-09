#!/bin/bash
# Smart Rebuild Script for Vulpis
# Integrates cleanup, python backend build, and tauri build

# Exit on error
set -e

echo "🚀 Starting Smart Build Process..."

# 1. Cleanup: Detach any stuck DMG volumes and kill old processes
echo "🧹 Step 1: Cleaning up environment..."
# Kill old backend processes if running
pkill -f "python-backend" || true
# Force detach any mounted DMGs from previous failed builds to avoid "Resource busy" errors
hdiutil info | grep "Vulpis" | grep "/dev/disk" | awk '{print $1}' | sort -u | xargs -n 1 hdiutil detach -force 2>/dev/null || true

# 2. Build Python Backend
echo "🐍 Step 2: Building Python Backend..."

# Get directory of this script (desktop-app)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Get project root (parent of desktop-app)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root (same as GitHub Actions)
cd "$PROJECT_ROOT"
echo "📁 Working directory: $(pwd)"

# Clean previous python builds
rm -rf desktop-app/dist desktop-app/build desktop-app/python-dist
# Clean any generated spec file
rm -f python-backend.spec

# Get Streamlit path for static assets
ST_PATH=$(python -c "import streamlit, os; print(os.path.dirname(streamlit.__file__))")
echo "📦 Streamlit path: $ST_PATH"

# Build copy-metadata args based on what's available
COPY_META_ARGS=""
for pkg in streamlit chromadb langchain langchain-core langchain-community langchain-openai rfc3987_syntax jsonschema streamlit_paste_button; do
    if python -c "import importlib.metadata; importlib.metadata.distribution('$pkg')" 2>/dev/null; then
        COPY_META_ARGS="$COPY_META_ARGS --copy-metadata $pkg"
        echo "  ✓ Found package: $pkg"
    else
        echo "  ✗ Package not found: $pkg (skipping metadata)"
    fi
done

# Apply patches to installed packages (styling etc)
python scripts/patch_paste_button.py

# Build with PyInstaller using command line (same as GitHub Actions)
# Key: Run from project root, output to desktop-app/python-dist
pyinstaller --clean --noconfirm \
    --name python-backend \
    --onedir \
    --contents-directory . \
    $COPY_META_ARGS \
    --add-data "app.py:." \
    --add-data "core:core" \
    --add-data "assets:assets" \
    --add-data "pages:pages" \
    --add-data "$ST_PATH/static:streamlit/static" \
    --add-data "$ST_PATH/runtime:streamlit/runtime" \
    --hidden-import=core.kb_manager \
    --hidden-import=core.rag_agent \
    --hidden-import=core.question_db \
    --hidden-import=core.document_loader \
    --hidden-import=core.vector_store \
    --hidden-import=core.text_splitter \
    --hidden-import=chromadb.telemetry.product.posthog \
    --collect-all streamlit_paste_button \
    --collect-all chromadb \
    --collect-all rfc3987_syntax \
    --exclude-module matplotlib \
    --exclude-module scipy \
    --exclude-module IPython \
    --exclude-module notebook \
    --exclude-module tkinter \
    --exclude-module test \
    --exclude-module unittest \
    --exclude-module pydoc \
    --exclude-module email.test \
    --distpath desktop-app/python-dist \
    --workpath desktop-app/build \
    app.py

# Clean generated spec file in project root
rm -f python-backend.spec

# Check output and set executable
if [ -d "desktop-app/python-dist/python-backend" ]; then
    chmod +x desktop-app/python-dist/python-backend/python-backend
    
    # Copy necessary data folders (same as GitHub Actions)
    if [ -d "vector_db" ]; then cp -r vector_db desktop-app/python-dist/python-backend/; fi
    if [ -d "data" ]; then cp -r data desktop-app/python-dist/python-backend/; fi
    
    echo "✅ Python backend built successfully."
else
    echo "❌ Python build failed: desktop-app/python-dist/python-backend not found."
    exit 1
fi

# 3. Build Tauri Frontend & Bundle
echo "🦀 Step 3: Building Tauri App..."
cd "$SCRIPT_DIR"

# Install dependencies just in case
npm install

# Build
npm run tauri build

echo "========================================"
echo "🎉 Build Success! Installer location:"
ls -lh src-tauri/target/release/bundle/dmg/*.dmg
echo "========================================"
