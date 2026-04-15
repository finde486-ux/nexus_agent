from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Any

class TaskClassification(Enum):
    SIMPLE = auto()
    MEDIUM = auto()
    COMPLEX = auto()

@dataclass
class Task:
    task_id: str
    description: str
    classification: TaskClassification
    metadata: Dict[str, Any]
    status: str = "PENDING"
    result: Optional[Any] = None
