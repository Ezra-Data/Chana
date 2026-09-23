import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge import KnowledgeEntry
from app.models.user import User, UserRole
from app.schemas.knowledge import KnowledgeEntryCreate, KnowledgeEntryUpdate, KnowledgeEntryResponse
from app.middleware.auth import get_current_user, require_role
from app.services import rag_service

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])


@router.get("", response_model=list[KnowledgeEntryResponse])
async def list_entries(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge base entries (admin only)."""
    result = await db.execute(
        select(KnowledgeEntry).order_by(KnowledgeEntry.category, KnowledgeEntry.title)
    )
    entries = result.scalars().all()
    return [KnowledgeEntryResponse.model_validate(e) for e in entries]


@router.post("", response_model=KnowledgeEntryResponse, status_code=201)
async def create_entry(
    data: KnowledgeEntryCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new knowledge base entry.
    Auto-embeds content into ChromaDB for RAG retrieval.
    This is the 'self-improving loop' — add entry, bot answers it immediately.
    """
    entry = KnowledgeEntry(
        category=data.category,
        title=data.title,
        content=data.content,
        source_doc=data.source_doc,
        created_by=current_user.id,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    # Embed into ChromaDB
    rag_service.add_document(
        entry_id=entry.id,
        title=entry.title,
        content=entry.content,
        category=entry.category,
        source_doc=entry.source_doc,
    )

    return KnowledgeEntryResponse.model_validate(entry)


@router.put("/{entry_id}", response_model=KnowledgeEntryResponse)
async def update_entry(
    entry_id: int,
    data: KnowledgeEntryUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Update a knowledge base entry. Re-embeds into ChromaDB."""
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    await db.flush()
    await db.refresh(entry)

    # Re-embed into ChromaDB
    rag_service.add_document(
        entry_id=entry.id,
        title=entry.title,
        content=entry.content,
        category=entry.category,
        source_doc=entry.source_doc,
    )

    return KnowledgeEntryResponse.model_validate(entry)


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: int,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Delete a knowledge base entry and its embeddings."""
    result = await db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    # Remove from ChromaDB
    rag_service.remove_document(entry_id)

    await db.delete(entry)
    await db.flush()


@router.post("/upload-pdf", response_model=KnowledgeEntryResponse, status_code=201)
async def upload_pdf(
    file: UploadFile = File(...),
    category: str = "general",
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF document — extract text, chunk, and embed into the knowledge base."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save file temporarily
    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)

    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Extract text using PyMuPDF
        try:
            import fitz  # pymupdf
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="PDF extraction requires PyMuPDF. Install with: pip install pymupdf"
            )
        doc = fitz.open(file_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n\n"
        doc.close()

        if not full_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        # Create DB entry
        entry = KnowledgeEntry(
            category=category,
            title=file.filename.replace(".pdf", "").replace("_", " ").title(),
            content=full_text.strip(),
            source_doc=file.filename,
            created_by=current_user.id,
        )
        db.add(entry)
        await db.flush()
        await db.refresh(entry)

        # Embed into ChromaDB
        rag_service.add_document(
            entry_id=entry.id,
            title=entry.title,
            content=entry.content,
            category=entry.category,
            source_doc=entry.source_doc,
        )

        return KnowledgeEntryResponse.model_validate(entry)

    finally:
        # Cleanup
        if os.path.exists(file_path):
            os.remove(file_path)
