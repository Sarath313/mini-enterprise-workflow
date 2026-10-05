# Mini Enterprise Collaboration & Workflow Application

## Phase 4 - OAuth Authentication & Microservices Integration

Phase 4 extends the Mini Enterprise platform with OAuth authentication and a microservices architecture.

## Architecture

React + Vite Frontend
        |
        v
Authentication Service - Port 8001
        |
        +----> User Service - Port 8002
        |
        +----> Tenant Admin Service - Port 8003

Authentication uses Auth0 with Google OAuth and Microsoft OAuth through Microsoft Entra ID.

## Services

### Authentication Microservice
Port: 8001

Features:
- Auth0 OAuth 2.0 / OpenID Connect
- Google authentication
- Microsoft authentication
- JWT access-token validation
- Protected API
- Current-user endpoint
- Provider detection
- Logout

Endpoints:

GET /auth/google/login
GET /auth/google/callback
GET /auth/google/logout
GET /auth/microsoft/login
GET /auth/microsoft/callback
GET /auth/microsoft/logout
GET /auth/me
GET /auth/provider
GET /api/protected
GET /health

### User Microservice
Port: 8002

Features:
- User creation/synchronization
- User profile retrieval
- User lookup
- User updates
- Auth0 JWT validation
- PostgreSQL database

Endpoints:

POST /users/
GET /users/me
GET /users/{user_id}
PATCH /users/{user_id}
GET /health

### Tenant Admin Microservice
Port: 8003

Features:
- Tenant creation
- Tenant retrieval
- Tenant users
- User status management
- User role management
- Tenant-owner authorization
- PostgreSQL database

Endpoints:

POST /tenants/
GET /tenants/{tenant_id}
GET /tenants/{tenant_id}/users
POST /tenants/{tenant_id}/users
PATCH /tenants/{tenant_id}/users/{user_id}/status
PATCH /tenants/{tenant_id}/users/{user_id}/role
GET /health

### Frontend
Port: 5173

Technology:
- React
- Vite
- Tailwind CSS
- Axios
- React Router

Features:
- Google login
- Microsoft login
- OAuth callback handling
- Protected dashboard
- Access-token storage
- Provider information
- Logout

## Authentication Flow

React
  |
  v
Authentication Service
  |
  v
Auth0
  |
  +---- Google
  |
  +---- Microsoft / Entra ID
  |
  v
OAuth Callback
  |
  v
User Service
  |
  v
React Dashboard

Protected APIs receive:

Authorization: Bearer <access_token>

## Running Locally

Authentication Service:

cd phase4/services/auth-service
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8001

User Service:

cd phase4/services/user-service
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8002

Tenant Service:

cd phase4/services/tenant-service
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --port 8003

Frontend:

cd phase4frontend
npm run dev

## Swagger Documentation

Authentication:
http://localhost:8001/docs

User:
http://localhost:8002/docs

Tenant:
http://localhost:8003/docs

## Docker

Docker Compose configuration is provided in:

phase4/docker-compose.yml

The Compose configuration includes:
- Authentication Service
- User Service
- Tenant Service
- React Frontend
- User PostgreSQL database
- Tenant PostgreSQL database

## Security

Secrets are excluded from Git using .gitignore.

Use .env.example as the configuration template.

Never commit:
- Auth0 Client Secret
- Google Client Secret
- Microsoft Entra Client Secret
- Database passwords

## Project Status

Phase 1 - Core workflow and RBAC: Completed

Phase 2 - Workflow, comments, approvals and audit history: Completed

Phase 3 - Documents, notifications and AI insights: Completed

Phase 4 - OAuth authentication and microservices: Implemented

Auth0 external-provider configuration may require final dashboard-side configuration before live Google/Microsoft login can be completed.

## Technologies

Python
FastAPI
SQLAlchemy
PostgreSQL
Pydantic
JWT
Auth0
React
Vite
Tailwind CSS
Axios
Docker
Docker Compose
