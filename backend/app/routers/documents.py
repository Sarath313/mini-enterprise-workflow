
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.document import Document
from app.models.task import Task
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.utils.audit import create_audit_log


router = APIRouter(prefix="/documents", tags=["Documents"])


# ---------------------------------------------------------------------------
# File storage configuration
# ---------------------------------------------------------------------------

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_ROOT = UPLOAD_DIR.resolve()

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".txt",
    ".csv",
    ".xlsx",
    ".xls",
    ".png",
    ".jpg",
    ".jpeg",
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# Task access control
# ---------------------------------------------------------------------------

def can_access_task(task: Task, current_user: User) -> bool:
    """
    Admin: all tasks.
    Manager: tasks they created or tasks assigned to them.
    Employee: tasks assigned to them.
    """
    if current_user.role == "admin":
        return True

    if current_user.role == "manager":
        return (
            task.created_by == current_user.id
            or task.assigned_to == current_user.id
        )

    return task.assigned_to == current_user.id


# ---------------------------------------------------------------------------
# Document access control
# ---------------------------------------------------------------------------

def can_access_document(
    document: Document,
    current_user: User,
    db: Session,
) -> bool:
    """
    Admins can access all documents.
    Uploaders can access their own documents.
    Other users must have access to the linked task.
    """
    if current_user.role == "admin":
        return True

    if document.uploaded_by == current_user.id:
        return True

    if document.task_id is None:
        return False

    task = (
        db.query(Task)
        .filter(Task.id == document.task_id)
        .first()
    )

    return task is not None and can_access_task(task, current_user)


def get_safe_file_path(document: Document) -> Path | None:
    """
    Resolve the stored path and ensure it remains inside UPLOAD_DIR.
    """
    if not document.file_path:
        return None

    candidate = (UPLOAD_DIR.parent / document.file_path).resolve()

    try:
        candidate.relative_to(UPLOAD_ROOT)
    except ValueError:
        return None

    return candidate


# ---------------------------------------------------------------------------
# Upload document
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    task_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    # Handle both Unix and Windows path separators in submitted filenames.
    original_filename = Path(
        file.filename.replace("\\", "/")
    ).name.strip()

    if not original_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file type. Allowed types: "
                + ", ".join(sorted(ALLOWED_EXTENSIONS))
            ),
        )

    # Validate access to the linked task.
    if task_id is not None:
        task = (
            db.query(Task)
            .filter(Task.id == task_id)
            .first()
        )

        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        if not can_access_task(task, current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this task",
            )

    # Read at most 10 MB plus one byte to detect oversized uploads.
    file_content = await file.read(MAX_FILE_SIZE + 1)

    if not file_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size must not exceed 10 MB",
        )

    # Determine the next version for this document name.
    if task_id is not None:
        latest_document = (
            db.query(Document)
            .filter(
                Document.task_id == task_id,
                Document.file_name == original_filename,
            )
            .order_by(Document.version.desc())
            .first()
        )
    else:
        latest_document = (
            db.query(Document)
            .filter(
                Document.task_id.is_(None),
                Document.file_name == original_filename,
                Document.uploaded_by == current_user.id,
            )
            .order_by(Document.version.desc())
            .first()
        )

    next_version = (
        latest_document.version + 1
        if latest_document
        else 1
    )

    # Use a random stored filename to avoid collisions and path injection.
    stored_filename = f"{uuid4().hex}{extension}"
    stored_path = UPLOAD_DIR / stored_filename
    committed = False

    try:
        stored_path.write_bytes(file_content)

        document = Document(
            file_name=original_filename,
            file_path=str(
                stored_path.relative_to(UPLOAD_DIR.parent)
            ),
            content_type=file.content_type,
            version=next_version,
            uploaded_by=current_user.id,
            task_id=task_id,
        )

        db.add(document)
        db.flush()

        create_audit_log(
            db=db,
            user_id=current_user.id,
            action="DOCUMENT_UPLOADED",
            entity="document",
            entity_id=document.id,
        )

        db.commit()
        committed = True
        db.refresh(document)

        return document

    except Exception:
        db.rollback()

        # Do not remove the file if its metadata was already committed.
        if not committed:
            try:
                stored_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store document",
        )


# ---------------------------------------------------------------------------
# Download document
# ---------------------------------------------------------------------------

@router.get("/{document_id}")
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if not can_access_document(document, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this document",
        )

    file_path = get_safe_file_path(document)

    if file_path is None or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on server",
        )

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="DOCUMENT_DOWNLOADED",
        entity="document",
        entity_id=document.id,
    )
    db.commit()

    return FileResponse(
        path=file_path,
        filename=document.file_name,
        media_type=document.content_type or "application/octet-stream",
    )


# ---------------------------------------------------------------------------
# List documents associated with a task
# ---------------------------------------------------------------------------

@router.get(
    "/task/{task_id}",
    response_model=list[DocumentResponse],
)
def get_task_documents(
    task_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    file_name: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    sort_by: Literal["file_name", "version", "created_at"] = Query(
        default="file_name"
    ),
    sort_order: Literal["asc", "desc"] = Query(default="asc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = (
        db.query(Task)
        .filter(Task.id == task_id)
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if not can_access_task(task, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this task",
        )

    query = db.query(Document).filter(Document.task_id == task_id)
    if file_name is not None:
        query = query.filter(
            Document.file_name.ilike(f"%{file_name.strip()}%")
        )

    order = desc if sort_order == "desc" else asc
    sort_column = {
        "file_name": Document.file_name,
        "version": Document.version,
        "created_at": Document.created_at,
    }[sort_by]
    ordering = [order(sort_column)]
    if sort_by == "file_name":
        ordering.append(Document.version.desc())
    elif sort_by == "version":
        ordering.append(Document.file_name.asc())
    ordering.append(order(Document.id))
    documents = (
        query
        .order_by(*ordering)
        .offset(skip)
        .limit(limit)
        .all()
    )

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="DOCUMENTS_VIEWED",
        entity="task",
        entity_id=task_id,
    )
    db.commit()

    return documents


# ---------------------------------------------------------------------------
# Delete document
# ---------------------------------------------------------------------------

@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if not can_access_document(document, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this document",
        )

    file_path = get_safe_file_path(document)

    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="DOCUMENT_DELETED",
        entity="document",
        entity_id=document.id,
    )

    try:
        db.delete(document)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )

    # Delete the physical file only after the database commit succeeds.
    if file_path is not None:
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            # Metadata and audit record are already deleted/committed.
            # A leftover physical file can be cleaned up separately.
            pass

    return {"message": "Document deleted successfully"}
