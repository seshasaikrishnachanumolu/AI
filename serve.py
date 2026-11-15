"""Production server (Waitress). Use this instead of `run.py` for demos and deployment.

    python serve.py            # http://0.0.0.0:8000
"""
import os

from waitress import serve

from app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Serving on http://localhost:{port}  (health: /health)")
    serve(app, host="0.0.0.0", port=port, threads=8)
