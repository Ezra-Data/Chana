from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json

from app.database import get_db
from app.models.navigation import NavNode
from app.schemas.navigation import NavNodeCreate, NavNodeUpdate, NavNodeResponse
from app.models.user import User, UserRole
from app.middleware.auth import get_current_user, require_role

router = APIRouter(prefix="/api/navigation", tags=["Navigation"])


@router.get("/search", response_model=list[NavNodeResponse])
async def search_locations(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search navigation nodes by name or synonyms (fuzzy matching)."""
    query_lower = q.lower().strip()

    result = await db.execute(select(NavNode))
    all_nodes = result.scalars().all()

    matches = []
    for node in all_nodes:
        score = 0
        # Exact name match
        if node.name.lower() == query_lower:
            score = 100
        # Name contains query
        elif query_lower in node.name.lower():
            score = 80
        # Query contains name
        elif node.name.lower() in query_lower:
            score = 70
        else:
            # Check synonyms
            for synonym in (node.synonyms or []):
                syn_lower = synonym.lower()
                if syn_lower == query_lower:
                    score = 90
                    break
                elif query_lower in syn_lower or syn_lower in query_lower:
                    score = max(score, 60)

        if score > 0:
            matches.append((score, node))

    # Sort by score descending
    matches.sort(key=lambda x: x[0], reverse=True)

    return [NavNodeResponse.model_validate(node) for _, node in matches[:10]]


@router.get("/nodes", response_model=list[NavNodeResponse])
async def list_nodes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all navigation nodes."""
    result = await db.execute(select(NavNode).order_by(NavNode.name))
    nodes = result.scalars().all()
    return [NavNodeResponse.model_validate(n) for n in nodes]


@router.post(
    "/nodes",
    response_model=NavNodeResponse,
    status_code=201,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def create_node(data: NavNodeCreate, db: AsyncSession = Depends(get_db)):
    """Create a navigation node (admin only)."""
    # Check name uniqueness
    existing = await db.execute(select(NavNode).where(NavNode.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Node with this name already exists")

    node = NavNode(**data.model_dump())
    db.add(node)
    await db.flush()
    await db.refresh(node)
    return NavNodeResponse.model_validate(node)


@router.put(
    "/nodes/{node_id}",
    response_model=NavNodeResponse,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def update_node(
    node_id: int, data: NavNodeUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a navigation node (admin only)."""
    result = await db.execute(select(NavNode).where(NavNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(node, key, value)

    await db.flush()
    await db.refresh(node)
    return NavNodeResponse.model_validate(node)


@router.delete(
    "/nodes/{node_id}",
    status_code=204,
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def delete_node(node_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a navigation node (admin only)."""
    result = await db.execute(select(NavNode).where(NavNode.id == node_id))
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")

    await db.delete(node)
    await db.flush()


# ─── Panoee Virtual Tour Configuration (Admin Managed) ────────

import os
import re
from pydantic import BaseModel

class TourConfig(BaseModel):
    tour_url: str

TOUR_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "tour_config.json")

def _get_stored_tour_url() -> str:
    if os.path.exists(TOUR_CONFIG_FILE):
        try:
            with open(TOUR_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("tour_url", "")
        except Exception:
            pass
    return ""

def _save_stored_tour_url(url: str):
    with open(TOUR_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"tour_url": url}, f)


@router.get("/tour")
async def get_tour_url(current_user: User = Depends(get_current_user)):
    """Get the current campus 360 virtual tour URL (available to all authenticated users)."""
    return {"tour_url": _get_stored_tour_url()}


@router.put("/tour", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def update_tour_url(data: TourConfig):
    """Update the campus 360 virtual tour URL (STRICTLY Admin only)."""
    clean_url = data.tour_url.strip()
    # If admin pasted full <iframe> tag, parse out src
    match = re.search(r'src=["\']([^"\']+)["\']', clean_url)
    if match:
        clean_url = match.group(1)

    _save_stored_tour_url(clean_url)
    return {"tour_url": clean_url, "message": "Campus virtual tour updated successfully"}

