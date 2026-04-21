from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from routers import auth, usuarios, config, feriados, processos

app = FastAPI(
    title="SEBRAE Gestão de Contratos",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers da API
app.include_router(auth.router,      prefix="/api")
app.include_router(usuarios.router,  prefix="/api")
app.include_router(config.router,    prefix="/api")
app.include_router(feriados.router,  prefix="/api")
app.include_router(processos.router, prefix="/api")

# Serve o frontend estático
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

    @app.get("/", include_in_schema=False)
    def root():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/{page}.html", include_in_schema=False)
    def page(page: str):
        path = os.path.join(frontend_dir, f"{page}.html")
        if os.path.exists(path):
            return FileResponse(path)
        return FileResponse(os.path.join(frontend_dir, "index.html"))
