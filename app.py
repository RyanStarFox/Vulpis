# ULTRA-EARLY DIAGNOSTIC - Must be before ANY imports that could fail
import os
import sys

# Immediately write to a file to confirm we're being executed
try:
    _diag_file = os.path.join(
        os.environ.get('HOME', os.environ.get('USERPROFILE', '/tmp')),
        'Library', 'Application Support', 'Vulpis', 'vulpis_early_diag.log'
    )
    os.makedirs(os.path.dirname(_diag_file), exist_ok=True)
    with open(_diag_file, 'a', encoding='utf-8') as f:
        import datetime
        f.write(f"\n{'='*60}\n")
        f.write(f"[{datetime.datetime.now()}] APP.PY EARLY LOAD\n")
        f.write(f"Python: {sys.version}\n")
        f.write(f"CWD: {os.getcwd()}\n")
        f.write(f"__file__: {__file__}\n")
        f.write(f"sys.argv: {sys.argv}\n")
        f.write(f"sys.path[:5]: {sys.path[:5]}\n")
        f.write(f"frozen: {getattr(sys, 'frozen', False)}\n")
        if hasattr(sys, '_MEIPASS'):
            f.write(f"_MEIPASS: {sys._MEIPASS}\n")
        f.write(f"{'='*60}\n")
        f.flush()
except Exception as e:
    print(f"EARLY DIAG FAILED: {e}", flush=True)

# CRITICAL: Path setup for PyInstaller frozen app
# Must be BEFORE any imports from local modules (like 'core')

# For frozen apps, ensure _MEIPASS is in sys.path
if getattr(sys, 'frozen', False):
    if hasattr(sys, '_MEIPASS'):
        _meipass = sys._MEIPASS
        if _meipass not in sys.path:
            sys.path.insert(0, _meipass)
        # Also add _internal if it exists (Mac PyInstaller default)
        _internal = os.path.join(os.path.dirname(sys.executable), '_internal')
        if os.path.exists(_internal) and _internal not in sys.path:
            sys.path.insert(0, _internal)

# Try importing streamlit - wrap in try-except to catch import errors
try:
    import streamlit as st
    import socket
    import mimetypes
    from PIL import Image
    import streamlit.components.v1 as components 
    from streamlit.web import cli as stcli
    import logging
except Exception as e:
    with open(_diag_file, 'a', encoding='utf-8') as f:
        import traceback
        f.write(f"FAILED DURING IMPORTS: {e}\n")
        f.write(traceback.format_exc())
    raise

# Log that basic imports succeeded
try:
    with open(_diag_file, 'a', encoding='utf-8') as f:
        f.write("Basic imports OK. Now importing core modules...\n")
except:
    pass

# Module-level logging - captures when Streamlit runs this script
_log_initialized = False
def _init_module_log():
    global _log_initialized
    if _log_initialized:
        return
    try:
        # This import can fail if core module is not found!
        with open(_diag_file, 'a', encoding='utf-8') as f:
            f.write("Attempting to import core.settings_utils...\n")
        
        from core.settings_utils import get_user_data_dir
        
        with open(_diag_file, 'a', encoding='utf-8') as f:
            f.write("core.settings_utils imported OK\n")
        
        log_dir = get_user_data_dir()
        log_file = os.path.join(log_dir, 'vulpis_app.log')
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, mode='a', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ],
            force=True
        )
        _log_initialized = True
        logging.info("=" * 60)
        logging.info("APP.PY MODULE LOADED BY STREAMLIT")
        logging.info(f"Python: {sys.version}")
        logging.info(f"CWD: {os.getcwd()}")
        logging.info(f"__file__: {__file__}")
        logging.info(f"sys.argv: {sys.argv}")
        
        with open(_diag_file, 'a', encoding='utf-8') as f:
            f.write("_init_module_log completed successfully\n")
    except Exception as e:
        import traceback
        with open(_diag_file, 'a', encoding='utf-8') as f:
            f.write(f"FAILED in _init_module_log: {e}\n")
            f.write(traceback.format_exc())
        print(f"Failed to init logging: {e}", flush=True)

_init_module_log()

# Fix for javascript files returning text/plain on Windows
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

# --- Context Helper ---
try:
    from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
except ImportError:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
    except ImportError:
        get_script_run_ctx = lambda: None

def find_port():
    port = 8501
    for i in range(20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port + i)) != 0:
                return port + i
    return port

def run_launcher():
    # Set up logging to file for debugging
    import logging
    from core.settings_utils import get_user_data_dir
    
    log_dir = get_user_data_dir()
    log_file = os.path.join(log_dir, 'vulpis_launcher.log')
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info("=" * 60)
    logging.info("Vulpis Launcher Starting")
    logging.info("=" * 60)
    logging.info(f"Python Version: {sys.version}")
    logging.info(f"Platform: {sys.platform}")
    logging.info(f"Log file: {log_file}")
    
    # Force UTF-8 for stdout/stderr to prevent encoding errors on Windows
    if sys.platform.startswith('win'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
            logging.info("Configured stdout/stderr to UTF-8")
        except Exception as e:
            logging.warning(f"Failed to reconfigure encoding: {e}")

    app_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
             app_dir = sys._MEIPASS
             logging.info(f"Running as frozen app, _MEIPASS: {app_dir}")
    
    logging.info(f"App directory: {app_dir}")
    
    # app.py is current file
    app_py = os.path.join(app_dir, 'app.py')
    logging.info(f"Target script: {app_py}")
    logging.info(f"Script exists: {os.path.exists(app_py)}")
    
    if not os.path.exists(app_py):
        logging.error(f"CRITICAL: app.py not found at {app_py}")
        logging.error(f"Directory contents: {os.listdir(app_dir)}")
        sys.exit(1)
    
    port = find_port()
    logging.info(f"Allocated port: {port}")
    
    # CRITICAL: Print this TWICE and flush to ensure Tauri Rust captures it despite any Streamlit noise.
    print(f"PYTHON_BACKEND_PORT={port}", flush=True)
    logging.info(f"Sent port signal: PYTHON_BACKEND_PORT={port}")
    
    sys.argv = [
        'streamlit',
        'run',
        app_py,
        '--global.developmentMode=false',
        f'--server.port={port}',
        '--server.address=127.0.0.1',
        '--server.headless=true',
        '--browser.gatherUsageStats=false',
        '--server.enableCORS=false',
        '--server.enableXsrfProtection=false',
    ]
    
    logging.info(f"Streamlit command: {' '.join(sys.argv)}")
    logging.info("Calling stcli.main()...")
    
    try:
        sys.exit(stcli.main())
    except Exception as e:
        logging.exception(f"CRITICAL ERROR during Streamlit launch: {e}")
        sys.exit(1)

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

def main_ui():
    logging.info("main_ui() called")
    
    icon_path = get_resource_path(os.path.join("assets", "logo.png"))
    logging.info(f"Icon path: {icon_path}, exists: {os.path.exists(icon_path)}")
    app_icon = "assets/logo.png"

    # Try loading as Image object (best for favicon per docs)
    if os.path.exists(icon_path):
        try:
            app_icon = Image.open(icon_path)
        except Exception as e:
            print(f"Error loading icon: {e}")


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
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">24h 在线答疑</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <a href="做题练习" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">📝</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">做题练习</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">AI出题批改解析</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <a href="错题整理" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">📓</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">错题整理</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">收集、整理、练习</div>
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
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">一键提炼知识库核心内容</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown("""
        <a href="知识库管理" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">🗂️</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">知识库管理</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">知识的宝库在此</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown("""
        <a href="使用说明" class="card-link" target="_self">
            <div class="nav-card" style="display: flex; flex-direction: column; align-items: center; justify-content: center; align-content: center; text-align: center; margin: 0 auto; padding-left: 0 !important; padding-right: 0 !important; width: 100%;">
                <div class="card-icon" style="margin: 0 auto; text-align: center;">📖</div>
                <div class="card-title" style="font-size: 1.2rem; font-weight: 600; text-align: center !important; width: 100%; display: block; margin: 0.5rem 0; max-width: 100%;">使用说明</div>
                <div class="card-desc" style="font-size: 0.9rem; opacity: 0.8; text-align: center !important; width: 100%; display: block; margin: 0; max-width: 100%;">详细功能介绍 与 操作指南</div>
            </div>
        </a>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("© 2025 [CS4314 Project Vulpis, Developed by RyanStarFox and Zhou Zihan](https://github.com/RyanStarFox/Vulpis)")

if __name__ == "__main__":
    if get_script_run_ctx():
        main_ui()
    else:
        run_launcher()
