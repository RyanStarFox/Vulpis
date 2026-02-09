import os
import shutil
import sys
from pathlib import Path

def patch_paste_button():
    try:
        import streamlit_paste_button
    except ImportError:
        print("streamlit_paste_button not installed. Skipping patch.")
        return

    # Get package location
    pkg_dir = Path(streamlit_paste_button.__file__).parent
    
    # Fix paths relative to project root (where script is run)
    # If run from project root, patches/ is in current dir
    # If run from scripts/, patches/ is in ../patches
    
    cwd = Path.cwd()
    if (cwd / "patches").exists():
        patches_dir = cwd / "patches"
    elif (cwd.parent / "patches").exists():
        patches_dir = cwd.parent / "patches"
    else:
        # Fallback for CI/CD if paths are different
        patches_dir = Path("patches")
        
    print(f"Using patches directory: {patches_dir}")

    # 1. Patch CSS
    css_file = pkg_dir / "frontend" / "style.css"
    patch_css = patches_dir / "streamlit_paste_button_style.css"

    if patch_css.exists():
        print(f"Patching {css_file}...")
        shutil.copy(patch_css, css_file)
        print("✅ CSS Patch applied.")
    else:
        print(f"❌ CSS Patch file not found at {patch_css}")

    # 2. Patch JS
    js_file = pkg_dir / "frontend" / "main.js"
    patch_js = patches_dir / "streamlit_paste_button_main.js"

    if patch_js.exists():
        print(f"Patching {js_file}...")
        shutil.copy(patch_js, js_file)
        print("✅ JS Patch applied.")
    else:
        print(f"❌ JS Patch file not found at {patch_js}")

if __name__ == "__main__":
    patch_paste_button()
