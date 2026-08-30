"""Local compatibility entrypoint for the MongoDB/Vercel HealthOS API.

Production is served by api/index.py on Vercel. This module lets developers run:
    uvicorn backend.main:app --reload
without starting the archived SQLAlchemy application.
"""

from api.index import app

__all__ = ["app"]
