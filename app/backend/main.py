from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from routers import auth, usuarios, config, feriados, processos


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pré-aquece os caches de feriados e prazos no startup para evitar lentidão na primeira requisição."""
    try:
        from database import get_db
        from services.dias_uteis import carregar_feriados
        from services.status import _carregar_prazos_fixos, _carregar_prazos_validacao
        db = get_db()
        carregar_feriados(db)
        _carregar_prazos_fixos(db)
        _carregar_prazos_validacao(db)
        print("✅ Caches pré-aquecidos com sucesso.")
    except Exception as e:
        print(f"⚠️  Falha ao pré-aquecer caches: {e}")
    yield


app = FastAPI(
    title="SEBRAE Gestão de Contratos",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
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
