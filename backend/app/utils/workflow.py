from fastapi import HTTPException, status


VALID_TRANSITIONS = {
    "todo": {"in_progress"},
    "in_progress": {"todo", "review"},
    "review": {"in_progress", "done"},
    "done": set(),
}


def validate_status_transition(
    current_status: str,
    new_status: str,
) -> None:
    if current_status == new_status:
        return

    allowed_statuses = VALID_TRANSITIONS.get(current_status, set())

    if new_status not in allowed_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Invalid status transition: "
                f"{current_status} → {new_status}"
            ),
        )