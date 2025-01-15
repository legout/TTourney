import uuid
from dataclasses import dataclass
from typing import List, Tuple

from .player import Player


@dataclass
class Match:
    player1: Player
    player2: Player
    round: int | str
    sets: List[Tuple[int, int]] = None
    result: Tuple[int, int] = None
    winner: str = None
    looser: str = None

    def __post_init__(self):
        self.match_id: str = f"{self.player1.id}_{self.player2.id}"

    def set_sets(self, *set_, sets: List[tuple[int, int]] | List[int] | None = None):
        """Set the sets of the match. If sets is None, set sets from set_.
        If set_ is a list of integers, convert them to sets.

        Args:
            *set_ (List[int]): List of integers representing sets.
            sets (List[tuple[int, int]] | List[int], optional): List of sets. Defaults
                to None.

        Raises:
            ValueError: If sets is None and set_ is not a list of integers.

        Example:
            match.set_sets(9, 8, 7)
            match.set_sets([(11, 9), (11, 8), (11, 7)])
            match.set_sets([9, 8, 7])
        """
        if sets is None:
            sets = list(set_)

        if isinstance(sets[0], int):
            self.sets = []
            for set in sets:
                if set >= 0:
                    self.sets.append((11, set) if set < 10 else (set + 2, set))
                else:
                    self.sets.append((-set, 11) if -set < 10 else (-set, -set + 2))
            sets = [(sets[i], sets[i + 1]) for i in range(0, len(sets), 2)]
        else:
            self.sets = sets
        self.set_result()
        self.set_winner_looser()

    def set_result(self, result: Tuple[int, int] = None):
        """Set the result of the match. If result is None, calculate the result from the sets.

        Args:
            result (Tuple[int, int], optional): Tuple of integers representing the result. Defaults to None.

        Example:
            match.set_result((3, 1))
            match.set_result()
        """

        if result:
            self.result = result
            return
        wins_p1 = sum(1 for s in self.sets if s[0] > s[1])
        wins_p2 = sum(1 for s in self.sets if s[1] > s[0])
        self.result = (wins_p1, wins_p2)

    def set_winner_looser(self, winner: Player = None):
        """Set the winner of the match. If winner is None, calculate the winner from the result.

        Args:
            winner (Player, optional): Player object representing the winner. Defaults to None.

        Example:
            match.set_winner(match.player1)
            match.set_winner()
        """
        self.winner = (
            self.player1.id if self.result[0] > self.result[1] else self.player2.id
        )
        self.looser = (
            self.player1.id if self.result[0] < self.result[1] else self.player2.id
        )

    def __str__(self):
        result = f"{self.player1.name} vs {self.player2.name}"
        if self.sets:
            sets_str = ", ".join([f"{s[0]}:{s[1]}" for s in self.sets])
            result += f" ({sets_str})"
        return result

    @property
    def is_completed(self):
        return self.result is not None

    def as_dict(self):
        return {
            "player1": self.player1.as_dict(),
            "player2": self.player2.as_dict(),
            "round": self.round,
            "sets": self.sets,
            "result": self.result,
            "winner": self.winner,
            "looser": self.looser,
            "match_id": self.match_id,
            "is_completed": self.is_completed,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            Player.from_dict(data["player1"]),
            Player.from_dict(data["player2"]),
            data["round"],
            data.get("sets"),
            data.get("result"),
            data.get("winner"),
            data.get("looser"),
            data.get("match_id", str(uuid.uuid4())),
        )
