from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import evals, agents, datasets, experiments, injection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all DB tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="EvalForge API",
    description="LLM Agent Benchmarking & Trustworthiness Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(evals.router,        prefix="/api/v1/evals",       tags=["Evals"])
app.include_router(agents.router,       prefix="/api/v1/agents",      tags=["Agents"])
app.include_router(datasets.router,     prefix="/api/v1/datasets",    tags=["Datasets"])
app.include_router(experiments.router,  prefix="/api/v1/experiments", tags=["Experiments"])
app.include_router(injection.router,    prefix="/api/v1/injection",   tags=["Injection"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}
