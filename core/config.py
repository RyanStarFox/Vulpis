import os
import sys
import shutil
import httpx
from openai import OpenAI
from dotenv import load_dotenv

print("=" * 60, flush=True)
print("[config] CONFIG MODULE LOADING", flush=True)
print(f"[config] Python: {sys.version}", flush=True)
print(f"[config] CWD: {os.getcwd()}", flush=True)
print(f"[config] __file__: {__file__}", flush=True)
print(f"[config] sys.frozen: {getattr(sys, 'frozen', False)}", flush=True)
if hasattr(sys, '_MEIPASS'):
    print(f"[config] _MEIPASS: {sys._MEIPASS}", flush=True)
print("=" * 60, flush=True)

# 数据目录配置
from core.settings_utils import get_user_data_dir

def _get_env_example_path():
    """Get path to .env.example template file."""
    # In frozen app, look in _MEIPASS
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        path = os.path.join(sys._MEIPASS, '.env.example')
        print(f"[config] _get_env_example_path (frozen): {path}", flush=True)
        return path
    # In development, look relative to this file
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.example')
    print(f"[config] _get_env_example_path (dev): {path}", flush=True)
    return path

def _ensure_env_file():
    """Ensure .env file exists in user data directory. If not, create from .env.example."""
    user_dir = get_user_data_dir()
    env_path = os.path.join(user_dir, '.env')
    
    print(f"[config] User data dir: {user_dir}", flush=True)
    print(f"[config] Expected .env path: {env_path}", flush=True)
    print(f"[config] .env exists: {os.path.exists(env_path)}", flush=True)
    
    if os.path.exists(env_path):
        # Read and log first few lines (without sensitive data)
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"[config] .env has {len(lines)} lines", flush=True)
            # Log keys found (not values)
            keys = [l.split('=')[0].strip() for l in lines if '=' in l and not l.strip().startswith('#')]
            print(f"[config] Keys in .env: {keys}", flush=True)
        except Exception as e:
            print(f"[config] WARNING: Could not read .env: {e}", flush=True)
        return env_path
    
    # .env doesn't exist, try to copy from .env.example
    example_path = _get_env_example_path()
    print(f"[config] No .env found. Template path: {example_path}", flush=True)
    print(f"[config] Template exists: {os.path.exists(example_path)}", flush=True)
    
    if os.path.exists(example_path):
        try:
            shutil.copy(example_path, env_path)
            print(f"[config] SUCCESS: Created .env from template: {env_path}", flush=True)
        except Exception as e:
            error_msg = f"[config] FATAL: Could not create .env: {e}"
            print(error_msg, flush=True)
            raise RuntimeError(error_msg)
    else:
        # No template found - this is an ERROR, not a fallback
        error_msg = f"[config] FATAL: No .env and no .env.example template found at {example_path}"
        print(error_msg, flush=True)
        # List directory contents to debug
        try:
            parent_dir = os.path.dirname(example_path)
            print(f"[config] Contents of {parent_dir}: {os.listdir(parent_dir)[:20]}", flush=True)
        except Exception as e:
            print(f"[config] Could not list dir: {e}", flush=True)
        raise RuntimeError(error_msg)
    
    return env_path

# Use user data directory for all persistent data
user_data_dir = get_user_data_dir()
DATA_DIR = os.path.join(user_data_dir, "data")
print(f"[config] DATA_DIR: {DATA_DIR}", flush=True)

# Ensure .env exists (create from template if needed)
env_path = _ensure_env_file()

# Load .env file - NO FALLBACK
print(f"[config] Loading .env from: {env_path}", flush=True)
result = load_dotenv(dotenv_path=env_path, override=True)
print(f"[config] load_dotenv result: {result}", flush=True)

# Verify loading by checking a known key
test_key = os.getenv("MODEL_NAME", "__NOT_SET__")
print(f"[config] Verification - MODEL_NAME from env: '{test_key}'", flush=True)

# API配置 (文本生成模型)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")
MODEL_NAME = os.getenv("MODEL_NAME", "")

# Log main API config with source
_raw_key = os.getenv("OPENAI_API_KEY")
_raw_base = os.getenv("OPENAI_API_BASE")
_raw_model = os.getenv("MODEL_NAME")
print(f"[config] OPENAI_API_KEY from .env: {'YES' if _raw_key else 'NO (empty/missing)'}", flush=True)
print(f"[config] OPENAI_API_BASE from .env: {_raw_base if _raw_base else '(empty/missing)'}", flush=True)
print(f"[config] MODEL_NAME from .env: {_raw_model if _raw_model else '(empty/missing)'}", flush=True)

# Embedding 模型API配置
# 如果未独立设置，默认回退到使用 OPENAI_API_KEY/BASE
_raw_emb_key = os.getenv("EMBEDDING_API_KEY")
_raw_emb_base = os.getenv("EMBEDDING_API_BASE")
_raw_emb_model = os.getenv("OPENAI_EMBEDDING_MODEL")

# Check if embedding config is explicitly set or falling back
if _raw_emb_key:
    EMBEDDING_API_KEY = _raw_emb_key
    print(f"[config] EMBEDDING_API_KEY: from .env (explicit)", flush=True)
else:
    EMBEDDING_API_KEY = OPENAI_API_KEY
    print(f"[config] EMBEDDING_API_KEY: FALLBACK to OPENAI_API_KEY", flush=True)

if _raw_emb_base:
    EMBEDDING_API_BASE = _raw_emb_base
    print(f"[config] EMBEDDING_API_BASE: from .env = '{_raw_emb_base}'", flush=True)
else:
    EMBEDDING_API_BASE = OPENAI_API_BASE
    print(f"[config] EMBEDDING_API_BASE: FALLBACK to OPENAI_API_BASE = '{OPENAI_API_BASE}'", flush=True)

if _raw_emb_model:
    OPENAI_EMBEDDING_MODEL = _raw_emb_model
    print(f"[config] OPENAI_EMBEDDING_MODEL: from .env = '{_raw_emb_model}'", flush=True)
else:
    OPENAI_EMBEDDING_MODEL = ""
    print(f"[config] OPENAI_EMBEDDING_MODEL: (empty/missing)", flush=True)

# 多模态模型(VL) API配置
# 如果未独立设置，默认回退到使用 OPENAI_API_KEY/BASE
VL_API_KEY = os.getenv("VL_API_KEY", OPENAI_API_KEY)
VL_API_BASE = os.getenv("VL_API_BASE", OPENAI_API_BASE)
VL_MODEL_NAME = os.getenv("VL_MODEL_NAME", "")

# 课件图像理解配置
ENABLE_IMAGE_CAPTIONING = os.getenv("ENABLE_IMAGE_CAPTIONING", "False").lower() == "true"
IMAGE_CAPTION_MODEL = os.getenv("IMAGE_CAPTION_MODEL", "") 
# Captioning 也可以有独立的 key，目前复用 VL_API_KEY

# 向量数据库配置
# Force vector DB to live in user data dir as well
VECTOR_DB_PATH = os.path.join(user_data_dir, "vector_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "")

# 混合检索配置 (Hybrid Search)
ENABLE_HYBRID_SEARCH = os.getenv("ENABLE_HYBRID_SEARCH", "True").lower() == "true"
HYBRID_SEARCH_ALPHA = float(os.getenv("HYBRID_SEARCH_ALPHA", "0.5")) # 0.5 means equal weight to vector and keyword

# 文本处理配置
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
SIZE_ERROR = int(os.getenv("SIZE_ERROR", "100"))
OVERLAP_ERROR = int(os.getenv("OVERLAP_ERROR", "20"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

# RAG配置
TOP_K = int(os.getenv("TOP_K", "6"))
EXERCISE_TOP_K = int(os.getenv("EXERCISE_TOP_K", "100")) # Pool size for random quiz
EXERCISE_TOP_K_TOPIC = int(os.getenv("EXERCISE_TOP_K_TOPIC", "30")) # Pool size when topic is specified
QUIZ_CONTEXT_LENGTH = int(os.getenv("QUIZ_CONTEXT_LENGTH", "2000"))
PANDOC_PATH = os.getenv("PANDOC_PATH", "") # Optional custom path for pandoc
MEMORY_WINDOW_SIZE = int(os.getenv("MEMORY_WINDOW_SIZE", "10"))



def get_openai_client(api_key=None, base_url=None):
    """
    Factory function to create an OpenAI client with SSL verification disabled (verify=False).
    Use this instead of creating OpenAI() directly to ensure self-signed certificates are accepted.
    """
    # Fallback to defaults if None is passed
    if api_key is None: api_key = OPENAI_API_KEY
    if base_url is None: base_url = OPENAI_API_BASE
    
    # Log what we're using
    _masked = f"{api_key[:8]}...{api_key[-4:]}" if api_key and len(api_key) > 12 else "(empty)"
    print(f"[get_openai_client] api_key: {_masked}", flush=True)
    print(f"[get_openai_client] base_url: {base_url if base_url else '(empty/default)'}", flush=True)
    
    # Prepare arguments
    kwargs = {
        "api_key": api_key,
        "http_client": httpx.Client(verify=False)
    }
    
    # Only pass base_url if it's not empty, otherwise let OpenAI library use its default
    if base_url:
        kwargs["base_url"] = base_url
    
    return OpenAI(**kwargs)

def reload():
    """Force reload of all configuration from .env file."""
    # Declare all globals FIRST (before any usage)
    global user_data_dir, DATA_DIR, env_path, OPENAI_API_KEY, OPENAI_API_BASE, MODEL_NAME
    global EMBEDDING_API_KEY, EMBEDDING_API_BASE, OPENAI_EMBEDDING_MODEL
    global VL_API_KEY, VL_API_BASE, VL_MODEL_NAME
    global ENABLE_IMAGE_CAPTIONING, IMAGE_CAPTION_MODEL
    global VECTOR_DB_PATH, COLLECTION_NAME
    global ENABLE_HYBRID_SEARCH, HYBRID_SEARCH_ALPHA
    global CHUNK_SIZE, CHUNK_OVERLAP, SIZE_ERROR, OVERLAP_ERROR, MAX_TOKENS
    global TOP_K, EXERCISE_TOP_K, EXERCISE_TOP_K_TOPIC, QUIZ_CONTEXT_LENGTH, PANDOC_PATH, MEMORY_WINDOW_SIZE
    
    print("=" * 40, flush=True)
    print(f"[config.reload] RELOAD CALLED", flush=True)
    print(f"[config.reload] env_path: {env_path}", flush=True)
    print(f"[config.reload] env_path exists: {os.path.exists(env_path)}", flush=True)
    
    # Read .env content for debugging
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            keys = [l.split('=')[0].strip() for l in lines if '=' in l and not l.strip().startswith('#')]
            print(f"[config.reload] Keys in .env: {keys}", flush=True)
        except Exception as e:
            print(f"[config.reload] Could not read .env: {e}", flush=True)
    
    # Reload dotenv - NO FALLBACK
    if os.path.exists(env_path):
        result = load_dotenv(dotenv_path=env_path, override=True)
        print(f"[config.reload] load_dotenv result: {result}", flush=True)
    else:
        error_msg = f"[config.reload] FATAL: .env not found at {env_path}"
        print(error_msg, flush=True)
        raise RuntimeError(error_msg)
        
    # Re-read all variables
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")
    MODEL_NAME = os.getenv("MODEL_NAME", "")
    
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", OPENAI_API_KEY)
    EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", OPENAI_API_BASE)
    OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "")
    
    VL_API_KEY = os.getenv("VL_API_KEY", OPENAI_API_KEY)
    VL_API_BASE = os.getenv("VL_API_BASE", OPENAI_API_BASE)
    VL_MODEL_NAME = os.getenv("VL_MODEL_NAME", "")
    
    ENABLE_IMAGE_CAPTIONING = os.getenv("ENABLE_IMAGE_CAPTIONING", "False").lower() == "true"
    IMAGE_CAPTION_MODEL = os.getenv("IMAGE_CAPTION_MODEL", "")
    
    VECTOR_DB_PATH = os.path.join(user_data_dir, "vector_db")
    COLLECTION_NAME = os.getenv("COLLECTION_NAME", "")
    
    ENABLE_HYBRID_SEARCH = os.getenv("ENABLE_HYBRID_SEARCH", "True").lower() == "true"
    HYBRID_SEARCH_ALPHA = float(os.getenv("HYBRID_SEARCH_ALPHA", "0.5"))
    
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
    SIZE_ERROR = int(os.getenv("SIZE_ERROR", "100"))
    OVERLAP_ERROR = int(os.getenv("OVERLAP_ERROR", "20"))
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
    
    TOP_K = int(os.getenv("TOP_K", "6"))
    EXERCISE_TOP_K = int(os.getenv("EXERCISE_TOP_K", "100"))
    EXERCISE_TOP_K_TOPIC = int(os.getenv("EXERCISE_TOP_K_TOPIC", "30"))
    QUIZ_CONTEXT_LENGTH = int(os.getenv("QUIZ_CONTEXT_LENGTH", "2000"))
    PANDOC_PATH = os.getenv("PANDOC_PATH", "")
    MEMORY_WINDOW_SIZE = int(os.getenv("MEMORY_WINDOW_SIZE", "10"))
    
    # Debug output
    masked_key = f"{OPENAI_API_KEY[:8]}...{OPENAI_API_KEY[-4:]}" if OPENAI_API_KEY and len(OPENAI_API_KEY) > 12 else "(empty)"
    print(f"[config.reload] DONE. OPENAI_API_KEY loaded: {masked_key}", flush=True)
    print(f"[config.reload] OPENAI_API_BASE: {OPENAI_API_BASE}", flush=True)
