from pydantic import BaseModel


class DashboardResponse(BaseModel):
    total_tasks: int

    todo_tasks: int
    in_progress_tasks: int
    done_tasks: int

    low_priority_tasks: int
    medium_priority_tasks: int
    high_priority_tasks: int

    assigned_tasks: int
    unassigned_tasks: int

    overdue_tasks: int