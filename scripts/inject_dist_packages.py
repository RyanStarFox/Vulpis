import os
import shutil
import sys

# List of critical packages that PyInstaller often misses in complex environments
# (module_object_name, package_folder_name) -> will import module_object_name first
PACKAGES_TO_INJECT = [
    ('docx2txt', 'docx2txt'),
    ('rank_bm25', 'rank_bm25'),
    ('pdfplumber', 'pdfplumber'),
    ('pptx', 'pptx')
]

def inject_packages():
    # Target directory: root of the bundled app (one-dir mode with content in root)
    # Adjust relative path from wherever this script is run (repo root)
    dest_base = os.path.join('desktop-app', 'python-dist', 'python-backend')
    
    print(f"I: Starting manual package injection to: {os.path.abspath(dest_base)}")
    
    if not os.path.exists(dest_base):
        print(f"E: Destination directory does not exist: {dest_base}")
        # Build might have failed or path is wrong
        sys.exit(1)

    import importlib
    
    for mod_name, folder_name in PACKAGES_TO_INJECT:
        try:
            print(f"I: Locating {mod_name}...")
            mod = importlib.import_module(mod_name)
            
            # Determine source path
            if hasattr(mod, '__path__'):
                src = list(mod.__path__)[0]
            elif hasattr(mod, '__file__'):
                src = os.path.dirname(mod.__file__)
            else:
                print(f"W: Could not determine path for {mod_name}, skipping.")
                continue
                
            # Determine dest path
            target_path = os.path.join(dest_base, folder_name)
            
            print(f"I: Copying {mod_name} from '{src}' to '{target_path}'")
            
            # Remove existing if present to ensure clean copy
            if os.path.exists(target_path):
                shutil.rmtree(target_path)
                
            shutil.copytree(src, target_path, dirs_exist_ok=True)
            print(f"S: Successfully injected {mod_name}")
            
        except ImportError:
            print(f"E: Could not import {mod_name} in the build environment. Is it installed?")
        except Exception as e:
            print(f"E: Failed to inject {mod_name}: {e}")

if __name__ == "__main__":
    inject_packages()
