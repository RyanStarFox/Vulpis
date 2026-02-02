#!/usr/bin/env python3
"""
Launcher Script for Desktop App
Replaces python-backend.py to ensure clean build on GitHub Actions.
"""
import os
import sys

# DEBUG: Force immediate print to confirm execution
print("🚀 LAUNCHER STARTED! Vulpis is booting...", flush=True)

def get_app_dir():
    """Get the directory where the app files are located."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        if hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        else:
            exe_dir = os.path.dirname(sys.executable)
            internal_dir = os.path.join(exe_dir, '_internal')
            if os.path.exists(internal_dir):
                return internal_dir
            return exe_dir
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def main():
    app_dir = get_app_dir()
    print(f"DEBUG: App Directory resolved to: {app_dir}", flush=True)
    
    # Change to app directory
    os.chdir(app_dir)
    
    # Set up environment
    os.environ['STREAMLIT_SERVER_PORT'] = '8501'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '127.0.0.1'
    os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    os.environ['STREAMLIT_BROWSER_SERVER_ADDRESS'] = '127.0.0.1'
    
    # Find app.py
    app_py = os.path.join(app_dir, 'app.py')
    if not os.path.exists(app_py):
        print(f"CRITICAL ERROR: app.py not found at {app_py}")
        # Debug listdir
        try:
             print(f"Contents of {app_dir}: {os.listdir(app_dir)}", flush=True)
        except:
             pass
        sys.exit(1)
    
    print(f"Starting Streamlit from: {app_py}", flush=True)
    
    # Find available port
    import socket
    def find_available_port(start_port, max_tries=20):
        for port in range(start_port, start_port + max_tries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', port)) != 0:
                    return port
        return start_port

    port = find_available_port(8501)
    # CRITICAL: This specific string is regex-matched by Tauri Rust code
    print(f"PYTHON_BACKEND_PORT={port}", flush=True)
    
    # Patch argv for Streamlit
    # Streamlit reads sys.argv[0] as the script name
    sys.argv = [
        'streamlit',
        'run',
        app_py,
        '--global.developmentMode=false',
        f'--server.port={port}',
        '--server.address=127.0.0.1',
        '--server.headless=true',
        '--server.enableCORS=false', # Forced to true by logic but we set it
        '--server.enableXsrfProtection=false',
        '--browser.gatherUsageStats=false',
    ]
    
    print("DEBUG: Calling stcli.main()...", flush=True)
    
    try:
        from streamlit.web import cli as stcli
        sys.exit(stcli.main())
    except Exception as e:
        print(f"CRITICAL ERROR launching Streamlit: {e}", flush=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
