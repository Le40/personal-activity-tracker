import ctypes
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8000/"
EDGE_PROFILE = Path(os.environ["LOCALAPPDATA"]) / "ActivityTrackerEdge"


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


def main():
    # Avoid starting a second server on the same port.
    with socket.socket() as connection:
        if connection.connect_ex(("127.0.0.1", 8000)) == 0:
            raise RuntimeError("Port 8000 is already in use. Close the previous server.")

    edge = find_edge()

    with open(PROJECT_DIR / "tracker-server.log", "a") as log:
        server = subprocess.Popen(
            [
                sys.executable,
                "-m", "uvicorn",
                "app.main:app",
                "--host", "127.0.0.1",
                "--port", "8000",
                "--log-level", "warning",
            ],
            cwd=PROJECT_DIR,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        try:
            wait_for_server(server)

            browser = subprocess.Popen([
                str(edge),
                f"--user-data-dir={EDGE_PROFILE}",
                f"--app={URL}",
                "--window-size=300,600",
                "--disable-background-mode",
            ])

            # Wait until the Edge process exits.
            browser.wait()

        finally:
            # Shut down FastAPI when Edge closes.
            if server.poll() is None:
                server.terminate()
                server.wait(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        ctypes.windll.user32.MessageBoxW(
            None,
            str(error),
            "Activity Tracker",
            0x10,
        )