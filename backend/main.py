"""Convenience entrypoint.

The canonical app module is ``app.main`` (run: ``uvicorn app.main:app --reload``).
This shim re-exports it so ``uvicorn main:app --reload`` works too, and
``python main.py`` launches a dev server directly.
"""

from app.main import app  # noqa: F401  (re-exported for `uvicorn main:app`)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
