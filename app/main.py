"""FastAPI application entry point for the local Plant Disease Detection app."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import __version__, db
from .config import BASE_DIR, settings
from .routers import admin, detect, history, meta
from .services import model_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    model_service.load()
    if not model_service.is_loaded():
        print(f"[WARN] Model could not be loaded: {model_service.info().get('error')}")
    yield
    model_service.unload()


app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description="Local plant disease detection with a trained Keras model and optional Gemini support.",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "app" / "static")), name="static")
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(settings.DATA_DIR)), name="media")

app.include_router(meta.router)
app.include_router(detect.router)
app.include_router(history.router)
app.include_router(admin.router)


@app.get("/health", include_in_schema=False)
def root_health() -> dict:
    """Convenience alias for browser/process health probes."""
    return meta.health()


@app.get("/", include_in_schema=False)
def user_dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"app_name": settings.APP_NAME, "version": settings.APP_VERSION, "page": "dashboard"},
    )


@app.get("/admin", include_in_schema=False)
def admin_panel(request: Request):
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"app_name": settings.APP_NAME, "version": settings.APP_VERSION, "page": "admin"},
    )


@app.exception_handler(404)
async def not_found(request: Request, exc: Exception) -> JSONResponse:
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return JSONResponse(status_code=404, content={"detail": "Page not found"})
