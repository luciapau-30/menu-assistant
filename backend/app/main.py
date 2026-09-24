from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes import analysis, compatibility, profile, users


app = FastAPI(
    title="Piece of Mind API",
    version="1.0.0"
)


app.include_router(users.router)
app.include_router(profile.router)
app.include_router(analysis.router)
app.include_router(compatibility.router)


@app.get("/")
def root():
    return {
        "message": "Piece of Mind API running"
    }

# Small same-origin demo client; no separate frontend build is required.

app.mount("/app", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="web")
