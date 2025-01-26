from dataclasses import dataclass
from typing import List, Tuple, Union, Any, Dict

from .player import Player


@dataclass
class Set:
    points1: int
    points2: int

    @classmethod
    def from_string(cls, score: str) -> "Set":
        """Create a Set from a string like '11:9' or '+9' or '-3'"""
        if ":" in score:
            p1, p2 = map(int, score.split(":"))
            return cls(p1, p2)

        points = int(score[1:]) if score[0] in ("+", "-") else int(score)
        if score.startswith("+"):
            return cls(11 if points <= 9 else points + 2, points)
        elif score.startswith("-"):
            return cls(points, 11 if points <= 9 else points + 2)
        else:
            return cls(11 if points <= 9 else points + 2, points)

        raise ValueError(f"Invalid score format: {score}")

    @classmethod
    def from_tuple(cls, score: Tuple[int, int]) -> "Set":
        """Create a Set from a tuple like (11, 9)"""
        return cls(*score)

    @classmethod
    def from_any(cls, score: Union[str, Tuple[int, int], "Set"]) -> "Set":
        """Create a Set from various input formats"""
        if isinstance(score, Set):
            return score
        if isinstance(score, str):
            return cls.from_string(score)
        if isinstance(score, (tuple, list)):
            return cls.from_tuple(score)
        raise ValueError(f"Cannot create Set from {score}")

    def __str__(self) -> str:
        return f"{self.points1}:{self.points2}"

    def is_valid(self) -> bool:
        """Check if set result is valid according to table tennis rules"""
        if self.points1 >= 11 and self.points1 >= self.points2 + 2:
            return True
        if self.points2 >= 11 and self.points2 >= self.points1 + 2:
            return True
        return False

    @property
    def winner(self) -> int:
        """Return 1 if player1 won, 2 if player2 won"""
        if not self.is_valid():
            raise ValueError("Set is not finished")
        return 1 if self.points1 > self.points2 else 2

    @property
    def points(self) -> Tuple[int, int]:
        return (self.points1, self.points2)

    @property
    def points_diff(self) -> int:
        return self.points1 - self.points2

    def as_dict(self) -> Dict[str, Any]:
        return {
            "points1": self.points1,
            "points2": self.points2,
            "winner": self.winner,
            "looser": 1 if self.winner == 2 else 2,
            "points_diff": self.points_diff,
        }


@dataclass
class Match:
    player1: Player
    player2: Player
    round: int | str
    sets: List[Set] = None
    result: Tuple[int, int] = None
    winner: str = None
    looser: str = None

    def __post_init__(self):
        self.match_id: str = f"{self.player1.id}_{self.player2.id}"
        if self.sets is None:
            self.sets = []

    def add_set(self, score: Union[str, Tuple[int, int], Set]):
        """Add a set result to the match"""
        set_ = Set.from_any(score)
        if not set_.is_valid():
            raise ValueError(f"Invalid set result: {set_}")
        self.sets.append(set_)
        self.update_result()

    def set_sets(self, *scores: Union[str, Tuple[int, int], Set]):
        """Set all sets at once"""
        self.sets = []
        for score in scores:
            self.add_set(score)

    def update_result(self):
        """Update match result based on sets"""
        if not self.sets:
            self.result = None
            self.winner = None
            self.looser = None
            return

        wins_p1 = sum(1 for s in self.sets if s.winner == 1)
        wins_p2 = sum(1 for s in self.sets if s.winner == 2)
        self.result = (wins_p1, wins_p2)

        if wins_p1 > wins_p2:
            self.winner = self.player1.id
            self.looser = self.player2.id
        elif wins_p2 > wins_p1:
            self.winner = self.player2.id
            self.looser = self.player1.id
        else:
            self.winner = None
            self.looser = None

    def __str__(self):
        result = f"{self.player1.name} vs {self.player2.name}"
        if self.sets:
            sets_str = ", ".join([str(s) for s in self.sets])
            result += f" ({sets_str})"
        return result

    @property
    def is_completed(self):
        return bool(self.winner)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "player1": self.player1.as_dict(),
            "player2": self.player2.as_dict(),
            "round": self.round,
            "sets": [s.as_dict() for s in self.sets],
            "result": self.result,
            "winner": self.winner,
            "looser": self.looser,
            "match_id": self.match_id,
            "is_completed": self.is_completed,
        }

    @property
    def points(self):
        return sum(s.points1 for s in self.sets), sum(s.points2 for s in self.sets)

    @property
    def points_diff(self):
        return self.points[0] - self.points[1]

    @classmethod
    def from_dict(cls, data):
        match = cls(
            Player.from_dict(data["player1"]),
            Player.from_dict(data["player2"]),
            data["round"],
        )
        if data.get("sets"):
            for set_tuple in data["sets"]:
                match.add_set(set_tuple)
        return match
