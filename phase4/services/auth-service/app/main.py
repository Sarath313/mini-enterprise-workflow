from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth
from app.routers import protected


app = FastAPI(
    title="Mini Enterprise - Authentication Microservice",
    description="Auth0 OAuth 2.0 / OpenID Connect authentication service",
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


app.include_router(auth.router)
app.include_router(protected.router)


@app.get("/")
async def root():
    return {
        "service": "Authentication Microservice",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }