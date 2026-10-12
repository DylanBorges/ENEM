from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging
import json

from app.core.config import settings
from app.api.v1 import api_router
from app.db.base import Base
from app.db.session import engine
import app.models  # Garante registro das tabelas

# Configuração de Logs Estruturados JSON (LGPD: sem senhas, sem tokens, sem textos integrais)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enem_api")


def _seed_reference_data_if_empty():
    from app.db.reference_seed import seed_reference_data_if_empty

    count = seed_reference_data_if_empty(engine)
    if count:
        logger.info(json.dumps({"event": "seeded_reference_data_complete", "rows": count}))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicialização: cria tabelas se não existirem
    Base.metadata.create_all(bind=engine)
    _seed_reference_data_if_empty()
    logger.info(json.dumps({"event": "startup", "service": "enem-api", "status": "ready"}))
    yield
    logger.info(json.dumps({"event": "shutdown", "service": "enem-api"}))


app = FastAPI(
    title="ENEM Intelligence API",
    version="0.1.0",
    description=(
        "API oficial da plataforma ENEM Intelligence. "
        "Atenção: todas as notas geradas são estimativas independentes e não oficiais do INEP."
    ),
    lifespan=lifespan,
)

# CORS Middleware (suporta domínios locais e qualquer preview/produção do Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Log seguro em JSON
    log_data = {
        "event": "http_request",
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "client_ip": request.client.host if request.client else None,
    }
    logger.info(json.dumps(log_data))
    return response


# Health endpoints
@app.get("/", tags=["health"])
@app.head("/", tags=["health"])
@app.get("/health", tags=["health"])
@app.get("/health/live", tags=["health"])
def health_live():
    return {"status": "ok", "service": "enem-api"}


@app.get("/health/ready", tags=["health"])
def health_ready():
    # Verifica conectividade com banco de dados
    try:
        with engine.connect() as conn:
            return {"status": "ready", "database": "connected"}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": "database_unavailable"},
        )


# API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)
