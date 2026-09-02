from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.auth import router as auth_router
from app.routers.tasks import router as tasks_router
from app.routers.users import router as users_router
from app.routers.activities import router as activities_router
from app.routers.dashboard import router as dashboard_router


app = FastAPI(
    title="Mini Enterprise Collaboration & Workflow Application",
    description="Phase 1 - Role-Based Task Management System",
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


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tasks_router)
app.include_router(activities_router)
app.include_router(dashboard_router)


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