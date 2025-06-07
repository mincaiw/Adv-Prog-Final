import datetime
from dataclasses import dataclass, field
from typing import Optional, Tuple

@dataclass
class Minwon:
    id: str
    title: str
    content: str
    date: datetime.date
    coordinates: Optional[Tuple[float, float]]
    author: Optional[str]
    category: str
    like_count: int
    status: str
