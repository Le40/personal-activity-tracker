import ctypes
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# --------------------------------------------------
# APPLICATION SETTINGS
# --------------------------------------------------
HOST = "127.0.0.1"
PORT = 8000
LOG_LEVEL = "warning"

# --------------------------------------------------
# WINDOW SETTINGS
# --------------------------------------------------
WINDOW_WIDTH = 350
WINDOW_HEIGHT = 650

# --------------------------------------------------
# PATHS
# --------------------------------------------------
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

def main():
    # Prevent starting a second server on the same port.
    with socket.socket() as connection:
        if connection.connect_ex((HOST, PORT)) == 0:
            raise RuntimeError(
                f"Port {PORT} is already in use. Close the previous server."
            )

    edge = find_edge()

    # Start FastAPI without opening a console window.
    with open(PROJECT_DIR / "tracker-server.log", "a") as log:
        server = subprocess.Popen(
            [
                sys.executable,
                "-m", "uvicorn",
                "app.main:app",
                "--host", HOST,
                "--port", str(PORT),
                "--log-level", LOG_LEVEL,
            ],
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
                "--disable-background-mode",
            ])

            # Keep FastAPI running while the Edge window is open.
            browser.wait()

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
        main()
    # Last-resort error handler: display unexpected startup errors to the user.
    except Exception as error:  # noqa: BLE001
        ctypes.windll.user32.MessageBoxW(
            None,
            str(error),
            "Activity Tracker",
            0x10,
        )