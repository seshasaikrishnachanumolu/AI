"""Production server (Waitress). Use this instead of `run.py` for demos and deployment.

    python serve.py                       # http://localhost:8000, reachable from this computer only
    $env:HOST="0.0.0.0"; python serve.py  # also reachable from other devices on your network (trusted networks only)
    $env:PORT="8001"; python serve.py     # use another port if 8000 is busy
"""
import os

from waitress import serve

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Serving on http://localhost:{port}  (health check: /health)")
    if host != "127.0.0.1":
        print(f"Listening on {host}: other devices on your network can connect.")
    serve(app, host=host, port=port, threads=8)
