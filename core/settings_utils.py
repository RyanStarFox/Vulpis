import os
import sys
import platform
import shutil
import json
from pathlib import Path

def get_user_data_dir():
    """Get the user data directory for the application."""
    app_name = "Vulpis"
    
    if platform.system() == "Windows":
        base_path = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
    elif platform.system() == "Darwin":
        base_path = os.path.expanduser("~/Library/Application Support")
    else:
        base_path = os.path.expanduser("~/.local/share")
        
    data_dir = os.path.join(base_path, app_name)
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def load_settings_from_env():
    """Load settings from .env file in the user data directory."""
    data_dir = get_user_data_dir()
    env_path = os.path.join(data_dir, '.env')
    
    settings = {}
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    settings[key.strip()] = value.strip()
    else:
        # Create empty .env if not exists
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write("# Vulpis Configuration\n")
        except Exception as e:
            print(f"Warning: Could not create .env file at {env_path}: {e}")
            
    return settings

def save_settings_to_env(settings):
    """Save settings to .env file in the user data directory."""
    data_dir = get_user_data_dir()
    env_path = os.path.join(data_dir, '.env')
    
    # Read existing file to preserve comments
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
    # Update lines
    new_lines = []
    updated_keys = set()
    
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            try:
                parts = stripped.split('=', 1)
                key = parts[0].strip()
                if key in settings:
                    new_lines.append(f"{key}={settings[key]}\n")
                    updated_keys.add(key)
                else:
                    new_lines.append(line)
            except IndexError:
                 new_lines.append(line)
        else:
            new_lines.append(line)
            
    # Append new keys
    for key, value in settings.items():
        if key not in updated_keys:
             new_lines.append(f"{key}={value}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    
    print(f"[settings_utils] Settings saved to: {env_path}", flush=True)
    print(f"[settings_utils] Keys saved: {list(settings.keys())}", flush=True)


# ========== KB Persistence ==========

def _get_user_prefs_path():
    """Get path to user preferences JSON file."""
    return os.path.join(get_user_data_dir(), "user_prefs.json")

def load_user_prefs():
    """Load user preferences from JSON file."""
    prefs_path = _get_user_prefs_path()
    if os.path.exists(prefs_path):
        try:
            with open(prefs_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[settings_utils] Failed to load user prefs: {e}", flush=True)
    return {}

def save_user_prefs(prefs):
    """Save user preferences to JSON file."""
    prefs_path = _get_user_prefs_path()
    try:
        with open(prefs_path, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[settings_utils] Failed to save user prefs: {e}", flush=True)

def get_last_selected_kb():
    """Get the last selected knowledge base name."""
    prefs = load_user_prefs()
    return prefs.get("last_selected_kb", None)

def set_last_selected_kb(kb_name):
    """Save the last selected knowledge base name."""
    prefs = load_user_prefs()
    prefs["last_selected_kb"] = kb_name
    save_user_prefs(prefs)


# ========== Pandoc Path Resolution ==========

def get_pandoc_path():
    """
    Get pandoc executable path.
    Priority: 1. Custom path from config  2. System PATH  3. None
    """
    from core.config import PANDOC_PATH
    
    # 1. Custom path from config
    if PANDOC_PATH and os.path.exists(PANDOC_PATH):
        return PANDOC_PATH
    
    # 2. Try system PATH
    system_pandoc = shutil.which("pandoc")
    if system_pandoc:
        return system_pandoc
    
    # 3. Not found
    return None

def test_pandoc():
    """
    Test if pandoc is available and working.
    Returns (success: bool, message: str, path: str or None)
    """
    import subprocess
    
    pandoc_path = get_pandoc_path()
    
    if not pandoc_path:
        return False, "Pandoc 未安装或未找到。请安装 Pandoc 或在设置中指定路径。", None
    
    try:
        result = subprocess.run(
            [pandoc_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown version"
            return True, f"Pandoc 可用: {version_line}", pandoc_path
        else:
            return False, f"Pandoc 执行失败: {result.stderr}", pandoc_path
    except subprocess.TimeoutExpired:
        return False, "Pandoc 响应超时", pandoc_path
    except Exception as e:
        return False, f"Pandoc 测试失败: {str(e)}", pandoc_path

