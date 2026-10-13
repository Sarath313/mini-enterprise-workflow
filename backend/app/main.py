
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import settings
from app.routers.auth import router as auth_router
from app.routers.tasks import router as tasks_router
from app.routers.users import router as users_router
from app.routers.activities import router as activities_router
from app.routers.dashboard import router as dashboard_router

from app.routers import comments
from app.routers import approvals
from app.routers import documents
from app.routers import audit_logs
from app.routers import notifications


app = FastAPI(
    title="Mini Enterprise Collaboration & Workflow Application",
    description="Backend API for enterprise task management and collaboration",
    version="1.0.0",
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tasks_router)
app.include_router(activities_router)
app.include_router(dashboard_router)
app.include_router(comments.router)
app.include_router(approvals.router)
app.include_router(documents.router)
app.include_router(audit_logs.router)
app.include_router(notifications.router)


@app.get("/")
def root():
    return {
        "message": "Mini Enterprise Collaboration & Workflow Application API is running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
