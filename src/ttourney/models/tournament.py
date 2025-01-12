import uuid
from datetime import date
from typing import List, Optional

from ..db.database import get_db_connection
from .group import Group
from .match import Match
from .player import Player


class Tournament:
    def __init__(
        self, name: str, tournament_date: date, db_url: str = "sqlite:///:memory:"
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.date = tournament_date
        self.players: List[Player] = []
        self.groups: List[Group] = []
        self.knockout_matches: List[Match] = []
        self.db_session = get_db_connection(db_url)

    def __del__(self):
        if self.db_session:
            self.db_session.close()

    def add_player(self, player: Player):
        self.players.append(player)

    def create_groups(self, players_per_group: int):
        sorted_players = sorted(self.players, key=lambda p: p.score, reverse=True)
        num_groups = len(sorted_players) // players_per_group
        if num_groups == 0:
            num_groups = 1

        # Distribute players to groups using snake system
        self.groups = [Group([], f"Group {chr(65+i)}") for i in range(num_groups)]
        for i, player in enumerate(sorted_players):
            group_idx = (
                i % num_groups
                if (i // num_groups) % 2 == 0
                else num_groups - 1 - (i % num_groups)
            )
            self.groups[group_idx].players.append(player)

    def setup_knockout_stage(self, players_per_group: int):
        qualified_players = []
        for group in self.groups:
            rankings = group.get_rankings()
            qualified_players.extend(rankings[:players_per_group])

        # Create knockout matches
        while len(qualified_players) > 1:
            round_matches = []
            for i in range(0, len(qualified_players), 2):
                if i + 1 < len(qualified_players):
                    match = Match(qualified_players[i], qualified_players[i + 1])
                    round_matches.append(match)
            self.knockout_matches.extend(round_matches)
            qualified_players = []  # Next round will be populated when results are entered

    def simulate(self):
        import random

        # Simulate group stage
        for group in self.groups:
            matches = group.generate_matches()
            for match in matches:
                sets = [(random.randint(5, 11), random.randint(0, 9)) for _ in range(3)]
                match.set_sets(sets)
            group.update_standings()

        # Simulate knockout stage
        for match in self.knockout_matches:
            sets = [(random.randint(5, 11), random.randint(0, 9)) for _ in range(3)]
            match.set_sets(sets)
