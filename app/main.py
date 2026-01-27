from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as api_router
from app.config import ConfigureLogging, GetSettings


def CreateApp() -> FastAPI:
    settings = GetSettings()
    ConfigureLogging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    @app.get("/health")
    def Health() -> dict:
        return {
            "status": "ok",
            "model_id": settings.model_id,
        }

    return app


app = CreateApp()
