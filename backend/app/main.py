from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.users import router as users_router


app = FastAPI(
    title="Mini Enterprise Collaboration & Workflow Application",
    description="Phase 1 - Role-Based Task Management System",
    version="1.0.0",
)


app.include_router(auth_router)
app.include_router(users_router)


@app.get("/")
def root():
    return {
        "message": "Mini Enterprise Workflow API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }