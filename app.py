"""Entry point for local dev (`python app.py`) and WSGI servers.

A WSGI server (waitress/gunicorn) imports `app` from this module.
"""
from cypher import create_app

app = create_app()


if __name__ == "__main__":
    # Local development server. Reloader off so the in-process scheduler
    # (added later) is not started twice.
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
