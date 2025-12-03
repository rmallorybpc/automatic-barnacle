"""Feature data model."""
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from datetime import datetime
import json


@dataclass
class Feature:
    """Represents a GitHub product feature or update."""
    
    id: str
    title: str
    description: str
    source_type: str  # "changelog", "roadmap", "graphql_schema_diff"
    source_url: Optional[str] = None
    product_area: str = "Unknown"
    tags: List[str] = field(default_factory=list)
    date_discovered: str = field(default_factory=lambda: datetime.now().isoformat())
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        data = self.to_dict()
        # Handle embedding separately to avoid huge JSON
        if data.get('embedding'):
            data['embedding'] = f"<{len(data['embedding'])} dimensions>"
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Feature':
        """Create Feature from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
