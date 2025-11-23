from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    user_id: int
    name: str
    email: Optional[str]
