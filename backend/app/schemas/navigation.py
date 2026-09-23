from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NavNodeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    synonyms: List[str] = []
    category: Optional[str] = None
    panoee_scene_id: Optional[str] = None
    description: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None


class NavNodeUpdate(BaseModel):
    name: Optional[str] = None
    synonyms: Optional[List[str]] = None
    category: Optional[str] = None
    panoee_scene_id: Optional[str] = None
    description: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None


class NavNodeResponse(BaseModel):
    id: int
    name: str
    synonyms: List[str]
    category: Optional[str] = None
    panoee_scene_id: Optional[str] = None
    description: Optional[str] = None
    building: Optional[str] = None
    floor: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
