import os
import httpx
from openai import OpenAI
from dotenv import load_dotenv

# 数据目录配置
from core.settings_utils import get_user_data_dir

# Use user data directory for all persistent data
user_data_dir = get_user_data_dir()
DATA_DIR = os.path.join(user_data_dir, "data")
env_path = os.path.join(user_data_dir, '.env')

# 加载 .env 文件中的环境变量
# 优先从用户数据目录加载，如果没有则尝试加载当前目录作为回退
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv() # Fallback to CWD

# API配置 (文本生成模型)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")
MODEL_NAME = os.getenv("MODEL_NAME", "")

# Embedding 模型API配置
# 如果未独立设置，默认回退到使用 OPENAI_API_KEY/BASE
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", OPENAI_API_KEY)
EMBEDDING_API_BASE = os.getenv("EMBEDDING_API_BASE", OPENAI_API_BASE)
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "")

# 多模态模型(VL) API配置
# 如果未独立设置，默认回退到使用 OPENAI_API_KEY/BASE
VL_API_KEY = os.getenv("VL_API_KEY", OPENAI_API_KEY)
VL_API_BASE = os.getenv("VL_API_BASE", OPENAI_API_BASE)
VL_MODEL_NAME = os.getenv("VL_MODEL_NAME", "")

# 课件图像理解配置
ENABLE_IMAGE_CAPTIONING = os.getenv("ENABLE_IMAGE_CAPTIONING", "False").lower() == "true"
IMAGE_CAPTION_MODEL = os.getenv("IMAGE_CAPTION_MODEL", "") 
# Captioning 也可以有独立的 key，目前复用 VL_API_KEY


# 数据目录配置
from core.settings_utils import get_user_data_dir

# Use user data directory for all persistent data
user_data_dir = get_user_data_dir()
DATA_DIR = os.path.join(user_data_dir, "data")

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
    # Declare all globals that need updating
    global user_data_dir, DATA_DIR, env_path, OPENAI_API_KEY, OPENAI_API_BASE, MODEL_NAME
    global EMBEDDING_API_KEY, EMBEDDING_API_BASE, OPENAI_EMBEDDING_MODEL
    global VL_API_KEY, VL_API_BASE, VL_MODEL_NAME
    global ENABLE_IMAGE_CAPTIONING, IMAGE_CAPTION_MODEL
    global VECTOR_DB_PATH, COLLECTION_NAME
    global ENABLE_HYBRID_SEARCH, HYBRID_SEARCH_ALPHA
    global CHUNK_SIZE, CHUNK_OVERLAP, SIZE_ERROR, OVERLAP_ERROR, MAX_TOKENS
    global TOP_K, EXERCISE_TOP_K, EXERCISE_TOP_K_TOPIC, QUIZ_CONTEXT_LENGTH, PANDOC_PATH, MEMORY_WINDOW_SIZE
    
    # Reload dotenv
    # Note: load_dotenv doesn't override by default, so we must force override
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        load_dotenv(override=True)
        
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

