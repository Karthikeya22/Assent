from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from assent_api.routers import auth, cases, health
from assent_api.settings import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="Assent API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    for r in (health.router, auth.router, cases.router):
        app.include_router(r)
    return app


app = create_app()
