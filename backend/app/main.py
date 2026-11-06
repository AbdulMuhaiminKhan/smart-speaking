"""FastAPI application entry point."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, live, sessions
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    settings.models_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(title="SmartSpeaking API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
        content = (
            exc.detail
            if isinstance(exc.detail, dict)
            else {"code": "error", "message": str(exc.detail)}
        )
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", []) if p not in {"body", "query"})
        return JSONResponse(
            status_code=422,
            content={"code": "invalid_input", "message": f"{field}: {first.get('msg', 'invalid')}"},
        )

    app.include_router(health.router)
    app.include_router(sessions.router)
    app.include_router(live.router)
    return app


app = create_app()
