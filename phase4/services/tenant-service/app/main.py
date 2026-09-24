from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.models.tenant import Tenant
from app.models.tenant_user import TenantUser
from app.routers import tenants


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Mini Enterprise - Tenant Admin Microservice",
    description="Tenant and organization administration service",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(tenants.router)


@app.get("/")
async def root():
    return {
        "service": "Tenant Admin Microservice",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }