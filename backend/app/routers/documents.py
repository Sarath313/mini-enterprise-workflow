from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.document import Document
from app.models.task import Task
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.utils.audit import create_audit_log


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


# ---------------------------------------------------------------------------
# File storage configuration
# ---------------------------------------------------------------------------

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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

def can_access_task(
    task: Task,
    current_user: User,
) -> bool:
    """
    Check whether the current user can access a task.

    Admin:
        Can access all tasks.

    Manager:
        Can access tasks they created or tasks assigned to them.

    Employee:
        Can access tasks assigned to them.
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
    Check whether the current user can access a document.

    Admin:
        Can access all documents.

    Uploader:
        Can access documents they uploaded.

    Task-linked document:
        Users with access to the linked task can access the document.
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

    if task is None:
        return False

    return can_access_task(task, current_user)


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
    """
    Upload a document.

    The document can optionally be linked to a task.
    """

    # Validate filename.
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    original_filename = Path(file.filename).name
    extension = Path(original_filename).suffix.lower()

    # Validate file extension.
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported file type. Allowed types: "
                + ", ".join(sorted(ALLOWED_EXTENSIONS))
            ),
        )

    # -----------------------------------------------------------------------
    # Validate linked task
    # -----------------------------------------------------------------------

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

    # -----------------------------------------------------------------------
    # Read and validate file size
    # -----------------------------------------------------------------------

    file_content = await file.read()

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

    # -----------------------------------------------------------------------
    # Determine document version
    # -----------------------------------------------------------------------

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

    if latest_document:
        next_version = latest_document.version + 1
    else:
        next_version = 1

    # -----------------------------------------------------------------------
    # Generate secure filesystem filename
    # -----------------------------------------------------------------------

    stored_filename = f"{uuid4().hex}{extension}"
    stored_path = UPLOAD_DIR / stored_filename

    try:
        # Save physical file.
        stored_path.write_bytes(file_content)

        # Save document metadata.
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

        # Create immutable audit record.
        create_audit_log(
            db=db,
            user_id=current_user.id,
            action="DOCUMENT_UPLOADED",
            entity="document",
            entity_id=document.id,
        )

        # Commit document and audit log together.
        db.commit()
        db.refresh(document)

        return document

    except Exception:
        # Remove physical file if database operation fails.
        if stored_path.exists():
            stored_path.unlink()

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store document",
        )


# ---------------------------------------------------------------------------
# Get / download document
# ---------------------------------------------------------------------------

@router.get(
    "/{document_id}",
)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Download a document after checking access permissions.
    """

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

    if not can_access_document(
        document,
        current_user,
        db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this document",
        )

    file_path = UPLOAD_DIR.parent / document.file_path

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file not found on server",
        )

    # Record successful document access.
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
# Get documents associated with a task
# ---------------------------------------------------------------------------

@router.get(
    "/task/{task_id}",
    response_model=list[DocumentResponse],
)
def get_task_documents(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return all document versions associated with a task.
    """

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

    documents = (
        db.query(Document)
        .filter(Document.task_id == task_id)
        .order_by(
            Document.file_name.asc(),
            Document.version.desc(),
        )
        .all()
    )

    # Record that the task's documents were viewed.
    create_audit_log(
        db=db,
        user_id=current_user.id,
        action="DOCUMENTS_VIEWED",
        entity="task",
        entity_id=task_id,
    )

    db.commit()

    return documents