import os
import sys
import socket
from streamlit.web import cli as stcli

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

if __name__ == "__main__":
    # 1. Determine path to app.py
    # In PyInstaller bundle, app.py is in the root of the bundle (sys._MEIPASS)
    # or inside 'core' depending on how we packed it. 
    # Based on our spec, app.py is at the root of the bundle.
    
    if getattr(sys, 'frozen', False):
        script_path = os.path.join(sys._MEIPASS, "app.py")
    else:
        # Dev mode: assume app.py is in parent directory
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))

    # 2. Find Port
    port = find_free_port()
    print(f"Starting Streamlit App at: {script_path} on port {port}")
    print(f"PYTHON_BACKEND_PORT={port}")
    sys.stdout.flush()

    # 3. Construct Arguments
    sys.argv = [
        "streamlit",
        "run",
        script_path,
        "--global.developmentMode=false",
        f"--server.port={port}",
        "--server.headless=true",
        "--server.address=127.0.0.1",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--server.enableWebsocketCompression=false",
        "--browser.gatherUsageStats=false",
    ]

    # 4. Launch
    sys.exit(stcli.main())
