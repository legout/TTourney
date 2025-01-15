from dataclasses import dataclass
from typing import List, Optional

from .match import Match


@dataclass
class Round:
    number: int
    matches: List[Match]
    name: Optional[str] = None
    stage: Optional[str] = None
    completed: bool = False

    def __post_init__(self):
        if self.name is None:
            self.name = f"Round {self.number}"
            
    @property
    def is_completed(self) -> bool:
        return all(match.is_completed for match in self.matches)

    def add_match(self, match: Match):
        match.round = self.number
        if self.stage:
            match.stage = self.stage
        self.matches.append(match)

    def as_dict(self):
        return {
            "number": self.number,
            "name": self.name,
            "stage": self.stage,
            "completed": self.completed,
            "matches": [m.as_dict() for m in self.matches],
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            number=data["number"],
            name=data["name"],
            stage=data.get("stage"),
            completed=data["completed"],
            matches=[Match.from_dict(m) for m in data["matches"]],
        )
