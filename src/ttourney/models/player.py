import uuid
from dataclasses import dataclass
from typing import List, Optional
from munch import munchify


@dataclass
class Player:
    first_name: str
    last_name: str | None = None
    score: int = 0
    start_number: int | str = 0
    age: Optional[int] = None
    gender: Optional[str] = None
    club: Optional[str] = None
    id: str = ""
    name: str | None = None

    def __post_init__(self):
        if self.last_name is None:
            self.name = self.first_name
        else:
            self.name = f"{self.first_name} {self.last_name}"
        if self.id == "":
            base = f"{self.first_name[:6]}_{self.last_name[:6]}"
            if self.club:
                base += f"_{self.club[:12]}"
            base += f"_{str(uuid.uuid4())[:4]}"
            self.id = base.lower().replace(" ", "_")

    def __str__(self):
        return f"{self.name}, {self.club} (Score: {self.score})"

    def as_dict(self):
        return {
            "id": self.id,
            "first name": self.first_name,
            "last name": self.last_name,
            "start number": self.start_number,
            "score": self.score,
            "age": self.age,
            "gender": self.gender,
            "club": self.club,
        }

    def munchify(self):
        return munchify(self.as_dict())

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["first name"],
            data["last name"],
            data["score"],
            data.get("start number", 0),
            data.get("id", str(uuid.uuid4())),
            data.get("age"),
            data.get("gender"),
            data.get("club"),
        )


def set_start_numbers(players: List[Player]):
    players_ = players[:]
    for i, player in enumerate(players_):
        player.start_number = i + 1
    return players_


# @dataclass
# class Players:
#     players: List[Player]

#     def as_dict(self):
#         return [p.as_dict() for p in self.players]

#     @classmethod
#     def from_dict(cls, data):
#         return cls([Player.from_dict(p) for p in data])

#     @property
#     def df(self):
#         return pd.DataFrame([p.as_dict() for p in self.players])

#     @property
#     def pl(self):
#         return pl.from_pandas(self.df)
