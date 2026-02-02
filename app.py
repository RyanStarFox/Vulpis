import streamlit as st
import os
import sys
import socket
import mimetypes
import threading

# --- DEBUG ALLOCATION ---
# This block helps diagnose Windows/PyInstaller execution flow
try:
    from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
except ImportError:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        get_script_run_ctx = lambda: None

ctx = get_script_run_ctx()
debug_msg = (
    f"\n========== APP.PY LOADED ==========\n"
    f"PID: {os.getpid()}\n"
    f"Thread: {threading.current_thread().name}\n"
    f"__name__: {__name__}\n"
    f"Context Present: {ctx is not None}\n"
    f"Sys Argv: {sys.argv}\n"
    f"===================================\n"
)
print(debug_msg, flush=True)
# ------------------------


# Fix for javascript files returning text/plain on Windows
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')



# --- PyInstaller Hooks ---
# Force PyInstaller to bundle these modules (referenced in pages/)
if False:
    from core import kb_manager
    from core import rag_agent
    from core import question_db
    from core import text_splitter
    from core import document_loader
    from core import vector_store
    
    # Document parsers (implicit dependencies)
    import docx2txt
    import pptx
    import pdfplumber
    import pandas
    
    # Search algorithm
    import rank_bm25

# -------------------------

# (Launcher logic moved to launcher.py)

import streamlit.components.v1 as components



import os
from PIL import Image

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

icon_path = get_resource_path(os.path.join("assets", "logo.png"))
app_icon = "assets/logo.png"

# Try loading as Image object (best for favicon per docs)
if os.path.exists(icon_path):
    try:
        app_icon = Image.open(icon_path)
    except Exception as e:
        print(f"Error loading icon: {e}")

# --- Context Guard for Windows/Mac/PyInstaller ---
# We use get_script_run_ctx() to ensure we are strictly inside a Streamlit execution loop.
# This prevents "missing ScriptRunContext" errors when the script is imported or run directly via python.
try:
    from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
except ImportError:
    # Fallback or different version structure
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        get_script_run_ctx = lambda: None

if get_script_run_ctx():
    st.set_page_config(
        page_title="Vulpis",
        page_icon=app_icon,
        layout="wide",
        initial_sidebar_state="collapsed"  # 默认隐藏侧边栏
    )

    # Inject JS for keyboard shortcut (Cmd/Ctrl + ,)
    components.html("""
    <script>
    document.addEventListener('keydown', function(e) {
        // 188 is comma key
        if ((e.metaKey || e.ctrlKey) && (e.key === ',' || e.keyCode === 188)) {
            e.preventDefault();
            window.top.postMessage({type: 'open-settings'}, '*');
        }
    }, true);
    </script>
    """, height=0, width=0)

    from core import ui_components
    ui_components.render_sidebar()

    # --- Custom CSS for "Card" Style (Dark Mode Adapted) ---
    # 1. Inject sidebar CSS separately (No f-string conflict)
    st.markdown(ui_components.get_sidebar_css(), unsafe_allow_html=True)

    # 2. Inject Page-Specific CSS
    st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    
    div[data-testid="stSidebar"] img {
        max-width: 100%;
        height: auto;
    }
    
    /* Custom Card Class */
    /* Custom Card Class - Base Styles */
    .nav-card {
        background-color: var(--secondary-background-color); 
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid rgba(128, 128, 128, 0.2);
        transition: all 0.3s ease;
        height: 100%;
        min-height: 200px;
        cursor: pointer;
        text-decoration: none;
        color: var(--text-color);
        /* Critical: Center content */
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    
    .nav-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        border-color: var(--primary-color);
    }
    
    .nav-card h3 {
        color: var(--text-color); 
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
        font-size: 1.2rem;
        font-weight: 600;
        width: 100%;
        text-align: center !important; /* 必须加回这里 */
    }
    
    .nav-card p {
        color: var(--text-color);
        opacity: 0.8;
        font-size: 0.9rem;
        width: 100%;
        margin: 0;
        text-align: center !important; /* 必须加回这里 */
    }

    /* Emoji size */
    .card-icon {
        font-size: 3rem;
        margin-bottom: 10px;
    }
    
    /* Force link container to be block and full width */
    a.card-link {
        text-decoration: none;
        color: inherit;
        display: flex !important; /* Changed from block to flex to center inner card */
        width: 100% !important;
        height: 100% !important;
        justify-content: center;
        align-items: center;
    }
    a.card-link:hover {
        text-decoration: none;
        color: inherit;
    }
    
    /* Title Styling */
    .main-title {
        text-align: center;
        color: var(--text-color);
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .sub-title {
        text-align: center;
        color: var(--text-color); 
        opacity: 0.7;
        font-weight: 400;
        margin-bottom: 3rem;
    }
    
    /* Reduce top padding for main container */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Warning Box Custom Styling */
    
    /* --- DEBUG STYLES (Temporary) --- */
    /* Remove these later! */
    /*
    div[data-testid="column"] > div > div > div > div {
        border: 1px dotted yellow !important;
    }
    a.card-link {
        border: 2px solid cyan !important;
    }
    .nav-card {
        border: 2px dashed red !important;
    }
    .nav-card * {
        border: 1px solid lime !important;
    }
    */
    /* End Debug Styles */
    
    .custom-warning-box {
        background-color: rgba(255, 229, 100, 0.1); 
        border: 1px solid rgba(255, 230, 100, 0.4);
        padding: 0; /* Let children handle padding */
        border-radius: 8px;
        color: #ffbd45; /* Streamlit warning text color match */
        display: flex;
        flex-direction: row;
        align-items: stretch; /* 关键：强迫子元素等高 */
        margin-bottom: 2rem;
        overflow: hidden; /* For border radius */
        min-height: 80px;
    }
    
    .warning-content {
        flex: 1; /* Take remaining space */
        padding: 1.5rem;
        display: flex;
        align-items: center;
        gap: 12px;
        border-right: 1px solid rgba(255, 230, 100, 0.2);
    }
    
    .warning-icon {
        font-size: 1.5rem;
        flex-shrink: 0;
    }
    
    .warning-text {
        font-size: 1rem;
        line-height: 1.5;
        color: var(--text-color);
    }
    .warning-text strong {
        color: #ffbd45;
    }
    
    .warning-btn {
        width: 180px; /* Fixed width for button area */
        flex-shrink: 0;
        background-color: rgba(255, 230, 100, 0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        text-decoration: none !important;
        color: #ffbd45 !important;
        font-weight: 600;
        transition: all 0.2s;
        cursor: pointer;
    }
    .warning-btn:hover {
        background-color: rgba(255, 230, 100, 0.25);
        color: #fff !important;
    }
</style>
""", unsafe_allow_html=True)


    # --- Header Section ---
    col_left, col_mid, col_right = st.columns([1, 8, 1], vertical_alignment="center")

    with col_mid:
        import base64
        try:
            with open("assets/logo.png", "rb") as f:
                encoded_logo = base64.b64encode(f.read()).decode()
            st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: center; gap: 20px; margin-bottom: 0.5rem; width: 100%;">
                    <img src="data:image/png;base64,{encoded_logo}" width="100" style="image-rendering: -webkit-optimize-contrast;">
                    <h1 style="margin: 0; font-weight: 800; font-size: 4rem; line-height: 1; display: inline-block;">Vulpis</h1>
                </div>
            """, unsafe_allow_html=True)
        except:
            st.markdown('<h1 class="main-title">Vulpis</h1>', unsafe_allow_html=True)
        st.markdown('<p class="sub-title">基于 RAG 技术的全能学习助手 · 答疑 · 刷题 · 复习 · 管理</p>', unsafe_allow_html=True)

    with col_right:
        st.write("") # Settings button moved to sidebar
        
    st.markdown("---")

    # --- System Check ---
    # --- System Check ---
    from core import config
    from core import settings_utils

    # Get .env path from settings_utils (Source of Truth)
    user_data_dir = settings_utils.get_user_data_dir()
    env_path = os.path.join(user_data_dir, '.env')

    # Auto-create .env if missing (User Request)
    if not os.path.exists(env_path):
        try:
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write("# Vulpis Configuration\\n")
            # Reload config to apply the clean slate if needed, though mostly symbolic here as it's empty
            import importlib
            importlib.reload(config)
        except Exception as e:
            st.error(f"无法创建配置文件: {e}")

    # Check for API Keys (now that .env definitely exists)
    if not all([config.OPENAI_API_KEY, config.MODEL_NAME, config.OPENAI_EMBEDDING_MODEL]):
        st.markdown(f"""
        <div class="custom-warning-box">
            <div class="warning-content">
                <div class="warning-icon">⚠️</div>
                <div class="warning-text">
                    <strong>核心配置不完整</strong>：检测到 API Key 或部分关键模型尚未配置。<br> 
                    (配置文件路径: <code style="font-size: 0.8em;">{env_path}</code>)<br>
                    请点击右侧按钮或展开左侧侧栏，打开系统设置面板。
                </div>
            </div>
            <a href="?open_settings=true" target="_self" class="warning-btn">
                🔧 点击此处设置
            </a>
        </div>
        """, unsafe_allow_html=True)

    # --- Navigation Cards (Clickable Links) ---
    # We use HTML <a> tags wrapping the cards to make them clickable.
    # Target is _self to reload in the same tab, navigating to the page URL.

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <a href="智能助教" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">🧠</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">智能助教</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">24h 在线答疑，支持多模态提问与上下文追问</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <a href="做题练习" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">📝</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">做题练习</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">自定义题型与数量，AI出题并即时批改解析</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <a href="错题整理" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">📓</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">错题整理</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">自动收录错题，支持反复练习与掌握标记</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    st.write("") # Spacer

    col4, col5, col6 = st.columns(3)

    with col4:
        st.markdown("""
        <a href="大纲生成" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">📑</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">大纲生成</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">一键提炼知识库核心内容，生成复习大纲</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown("""
        <a href="知识库管理" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">🗂️</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">知识库管理</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">上传文档、构建索引，打造专属知识底座</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown("""
        <a href="使用说明" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">📖</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">使用说明</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">查看系统详细功能介绍和系统操作指南</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("© 2025 [CS4314 Project, Developed by RyanStarFox and Zhou Zihan](https://github.com/RyanStarFox/CS4314_NLP_Proj2)")
