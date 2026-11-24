"""Start the API:  uv run uvicorn app.main:app --reload   (docs at http://localhost:8000/docs)"""

from fastapi import FastAPI

from app.routes import router

app = FastAPI(title="Medical Diagnostics Support API")
app.include_router(router)
