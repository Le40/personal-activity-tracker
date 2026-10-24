import ctypes
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from ctypes import wintypes


# --------------------------------------------------
# APPLICATION SETTINGS
# --------------------------------------------------

HOST = "127.0.0.1"
PORT = 8000
LOG_LEVEL = "info"


# --------------------------------------------------
# WINDOW SETTINGS
# --------------------------------------------------

WINDOW_WIDTH = 350
WINDOW_HEIGHT = 650


# --------------------------------------------------
# PATHS
# --------------------------------------------------

IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    PROJECT_DIR = Path(sys.executable).resolve().parent
else:
    PROJECT_DIR = Path(__file__).resolve().parent

EDGE_PROFILE = Path(os.environ["LOCALAPPDATA"]) / "ActivityTrackerEdge"


# --------------------------------------------------
# DERIVED SETTINGS
# --------------------------------------------------

URL = f"http://{HOST}:{PORT}/"


# --------------------------------------------------
# FIND MICROSOFT EDGE
# --------------------------------------------------

def find_edge():
    locations = [
        Path(os.environ["PROGRAMFILES(X86)"]),
        Path(os.environ["PROGRAMFILES"]),
    ]

    for location in locations:
        edge = location / "Microsoft" / "Edge" / "Application" / "msedge.exe"

        if edge.exists():
            return edge

    raise FileNotFoundError("Microsoft Edge was not found.")


# --------------------------------------------------
# START FASTAPI SERVER
# --------------------------------------------------

def run_server():
    log = open(PROJECT_DIR / "tracker-server.log", "a", encoding="utf-8", buffering=1)

    sys.stdout = log
    sys.stderr = log

    import uvicorn

    from app.activities.models import Base
    from app.database import engine
    from app.main import app

    # Create database tables if they don't exist.
    Base.metadata.create_all(bind=engine)

    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level=LOG_LEVEL,
    )


# --------------------------------------------------
# WAIT FOR FASTAPI
# --------------------------------------------------

def wait_for_server(server):
    for _ in range(50):
        if server.poll() is not None:
            raise RuntimeError("FastAPI failed to start.")

        try:
            with urllib.request.urlopen(URL + "health", timeout=0.3):
                return
        except OSError:
            time.sleep(0.2)

    raise RuntimeError("FastAPI did not become ready.")


# --------------------------------------------------
# APPLICATION LAUNCHER
# --------------------------------------------------

def wait_for_browser_window(server):
    user32 = ctypes.windll.user32

    user32.FindWindowW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
    ]
    user32.FindWindowW.restype = wintypes.HWND

    window_title = "Activity Tracker"

    # Wait for Edge to create the application window.
    deadline = time.monotonic() + 45

    while time.monotonic() < deadline:
        if user32.FindWindowW(None, window_title):
            break

        if server.poll() is not None:
            raise RuntimeError("FastAPI stopped during browser startup.")

        time.sleep(0.25)
    else:
        raise RuntimeError("PATRICK window did not appear.")

    # Keep the server running while the window exists.
    window_missing_since = None

    while server.poll() is None:
        if user32.FindWindowW(None, window_title):
            window_missing_since = None
        elif window_missing_since is None:
            window_missing_since = time.monotonic()
        elif time.monotonic() - window_missing_since >= 2:
            return

        time.sleep(0.25)

    raise RuntimeError("FastAPI stopped unexpectedly.")

def main():
    # Prevent starting a second server on the same port.
    with socket.socket() as connection:
        if connection.connect_ex((HOST, PORT)) == 0:
            raise RuntimeError(
                f"Port {PORT} is already in use. Close the previous server."
            )

    edge = find_edge()

    # Select the appropriate command for starting FastAPI.
    if IS_FROZEN:
        command = [sys.executable, "--server"]
    else:
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--server",
        ]

    # Start FastAPI without opening a console window.
    with open(PROJECT_DIR / "tracker-server.log", "a") as log:
        server = subprocess.Popen(
            command,
            cwd=PROJECT_DIR,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        try:
            wait_for_server(server)

            # Open the application in a compact Edge window.
            browser = subprocess.Popen([
                str(edge),
                f"--user-data-dir={EDGE_PROFILE}",
                f"--app={URL}",
                f"--window-size={WINDOW_WIDTH},{WINDOW_HEIGHT}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-mode",
            ])

            # Keep FastAPI running while the Edge window is open.
            wait_for_browser_window(server)

        finally:
            # Shut down FastAPI when Edge closes.
            if server.poll() is None:
                server.terminate()
                server.wait(timeout=5)


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------

if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--server"]:
            run_server()
        else:
            main()

    # Last-resort error handler.
    except Exception as error:  # noqa: BLE001
        ctypes.windll.user32.MessageBoxW(
            None,
            str(error),
            "Activity Tracker",
            0x10,
        )