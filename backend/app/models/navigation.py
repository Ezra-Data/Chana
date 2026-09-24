
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.database import Base


class NavNode(Base):
    __tablename__ = "nav_nodes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    synonyms = Column(JSON, default=list, nullable=False)  # e.g., ["comp lab", "computer room", "ICT lab"]
    category = Column(String(100), nullable=True)  # e.g., "academic", "admin", "facility"
    panoee_scene_id = Column(String(255), nullable=True)  # Scene ID for Panoee deep-linking
    description = Column(Text, nullable=True)
    building = Column(String(255), nullable=True)
    floor = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<NavNode id={self.id} name={self.name}>"
