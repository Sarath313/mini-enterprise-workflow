from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import users

from app.models.user import User


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Mini Enterprise - User Microservice",
    description="User profile and account management service",
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


app.include_router(users.router)


@app.get("/")
async def root():
    return {
        "service": "User Microservice",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }