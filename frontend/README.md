# Mini Enterprise Collaboration & Workflow Application

A full-stack enterprise workflow management application built with **FastAPI, PostgreSQL, SQLAlchemy, Alembic, React, and Tailwind CSS**.

The application provides secure authentication, role-based access control, task management, task assignment, dashboard analytics, and audit activity tracking for Admin, Manager, and Employee users.

---

## Features

### Authentication

- User registration
- Secure password hashing with bcrypt
- JWT-based authentication
- Login using email and password
- Protected API endpoints
- Persistent frontend authentication
- Logout functionality

### Role-Based Access Control

The application supports three roles:

- **Admin**
- **Manager**
- **Employee**

Each role has different permissions across the application.

### Task Management

- Create tasks
- View tasks
- Update tasks
- Delete tasks
- Assign tasks to users
- Update task status
- Set task priority
- Set task due dates
- Filter tasks by status
- Filter tasks by priority
- Filter tasks by assignee
- Pagination support

### Task Status

Tasks can have one of the following statuses:

- To Do
- In Progress
- Done

### Task Priority

Tasks support three priority levels:

- Low
- Medium
- High

### Activity / Audit History

The application records important task actions, including:

- Task creation
- Task assignment
- Status changes
- Task updates
- Task deletion

Activity records include:

- User who performed the action
- Action type
- Action details
- Timestamp

Audit records are preserved even after a task is deleted.

### Dashboard

The dashboard provides workflow statistics including:

- Total tasks
- To Do tasks
- In Progress tasks
- Completed tasks
- Low priority tasks
- Medium priority tasks
- High priority tasks
- Assigned tasks
- Unassigned tasks
- Overdue tasks

### User Directory

Admins can view registered users with:

- User ID
- Name
- Email
- Role
- Active/inactive status

### Responsive Frontend

The React frontend supports:

- Desktop navigation
- Responsive mobile navigation
- Mobile sidebar menu
- Responsive task cards
- Responsive user directory
- Responsive dashboard layouts

---

# Role Permissions

| Feature | Admin | Manager | Employee |
|---|---:|---:|---:|
| Dashboard | ✅ | ✅ | ✅ |
| View Users | ✅ | ❌ | ❌ |
| Create Tasks | ✅ | ✅ | ❌ |
| View Tasks | ✅ | Own/Assigned | Assigned |
| Assign Tasks | ✅ | Own Tasks | ❌ |
| Update Tasks | ✅ | Own Tasks | Status |
| Delete Tasks | ✅ | Own Tasks | ❌ |
| View Activity | ✅ | Own/Assigned | Assigned |

---

# Technology Stack

## Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- Alembic
- JWT
- python-jose
- Passlib
- bcrypt
- psycopg

## Frontend

- React
- Vite
- React Router
- Axios
- Tailwind CSS

## Development Tools

- Visual Studio Code
- Git
- GitHub
- PostgreSQL
- PowerShell

---

# Project Structure

```text
mini-enterprise-workflow/
│
├── backend/
│   │
│   ├── app/
│   │   ├── dependencies/
│   │   │   └── auth.py
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── task.py
│   │   │   └── activity.py
│   │   │
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── tasks.py
│   │   │   ├── activities.py
│   │   │   └── dashboard.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── task.py
│   │   │   ├── activity.py
│   │   │   └── dashboard.py
│   │   │
│   │   ├── database.py
│   │   └── main.py
│   │
│   ├── alembic/
│   │   └── versions/
│   │
│   ├── .env
│   ├── alembic.ini
│   └── requirements.txt
│
├── frontend/
│   │
│   ├── src/
│   │   ├── api/
│   │   │   └── axios.js
│   │   │
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   ├── Navbar.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── ProtectedRoute.jsx
│   │   │
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Tasks.jsx
│   │   │   ├── Users.jsx
│   │   │   └── Activity.jsx
│   │   │
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   │
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── README.md
