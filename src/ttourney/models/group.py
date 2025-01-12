import datetime as dt
import random
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

import pandas as pd
import polars as pl

from .match import Match
from .player import Player


@dataclass
class Result:
    round: int | str
    wins: int
    losses: int
    sets_won: int
    sets_lost: int
    balls_won: int
    balls_lost: int
    set_difference: int
    ball_difference: int
    direct_encounters: Dict[str, int] = None

    def add_match(self, match: Match, player_id: str):
        if self.direct_encounters is None:
            self.direct_encounters = {}

        if match.winner.id == player_id:
            self.wins += 1
        else:
            self.losses += 1

        if match.player1.id == player_id:
            self.sets_won += match.result[0]
            self.sets_lost += match.result[1]
            self.direct_encounters[match.player2.id] = (
                1 if match.winner.id == player_id else -1
            )
        else:
            self.sets_won += match.result[1]
            self.sets_lost += match.result[0]
            self.direct_encounters[match.player1.id] = (
                1 if match.winner.id == player_id else -1
            )

        for set in match.sets:
            if match.player1.id == player_id:
                self.balls_won += set[0]
                self.balls_lost += set[1]
            else:
                self.balls_won += set[1]
                self.balls_lost += set[0]

        self.set_difference = self.sets_won - self.sets_lost
        self.ball_difference = self.balls_won - self.balls_lost
        self.round = match.round

    def as_dict(self):
        return {
            "wins": self.wins,
            "losses": self.losses,
            "sets_won": self.sets_won,
            "sets_lost": self.sets_lost,
            "balls_won": self.balls_won,
            "balls_lost": self.balls_lost,
            "set_difference": self.set_difference,
            "ball_difference": self.ball_difference,
            "direct_encounters": self.direct_encounters,
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            wins=data["wins"],
            losses=data["losses"],
            sets_won=data["sets_won"],
            sets_lost=data["sets_lost"],
            balls_won=data["balls_won"],
            balls_lost=data["balls_lost"],
            set_difference=data["set_difference"],
            ball_difference=data["ball_difference"],
            direct_encounters=data["direct_encounters"],
        )


class BaseGroup:
    def __init__(self, players: List[Player], name: str):
        self.name = name
        self.players = players
        self.players.sort(key=lambda p: p.score, reverse=True)
        self.matches: List[Match] = []
        self.ranking: List[Player] = self.players[:]
        self.excluded_matches: Set[Tuple[str, str]] = set()
        self._stats = {}
        self._buchholz_scores = {}
        self._direct_encounter_matrix = {}

    @property
    def players_df(self) -> pd.DataFrame:
        if len(self.players) == 0:
            return pl.DataFrame()
        return pl.DataFrame([p.as_dict() for p in self.players])

    @property
    def matches_df(self) -> pd.DataFrame:
        if len(self.matches) == 0:
            return pl.DataFrame()
        return pl.DataFrame([m.as_dict() for m in self.matches])

    @property
    def matches_per_round(self) -> int:
        return len(self.players) // 2

    @property
    def rounds_completed(self) -> int:
        if len(self.matches) == 0:
            return 0
        return (
            self.matches_df.filter(pl.col("is_completed"))
            .group_by("round")
            .agg(pl.count("result") == self.matches_per_round)
            .filter(pl.col("result"))
            .select(pl.max("round"))[0, "round"]
        )

    @property
    def current_round(self) -> int:
        if len(self.matches) == 0:
            return 0

        if self.match_df.select(pl.max("round"))[0, "round"] > self.rounds_completed:
            return self.rounds_completed + 1
        return self.rounds_completed

    def _get_stats(self, round: int = None, update: bool = False) -> pl.DataFrame:
        if round is None:
            round = self.rounds_completed

        if round in self._stats and not update:
            return self._stats[round]

        stats = []
        for player in self.players:
            stats.append(
                self.matches_df.filter(pl.col("round") <= round)
                .filter(pl.col("is_completed"))
                .filter(
                    (pl.col("player1").struct["id"] == player.id)
                    | (pl.col("player2").struct["id"] == player.id)
                )
                .select(
                    pl.lit(round).alias("round"),
                    pl.lit(player.id).alias("player_id"),
                    pl.lit(player.score).alias("score"),
                    (pl.col("winner") == player.id).cast(pl.int32).sum().alias("wins"),
                    (pl.col("winner") != player.id)
                    .cast(pl.int32)
                    .sum()
                    .alias("losses"),
                    (
                        pl.when(pl.col("player1").struct["id"] == player.id)
                        .then(pl.col("result").list[0])
                        .otherwise(pl.col("result").list[1])
                        .sum()
                        .alias("sets_won")
                    ),
                    (
                        pl.when(pl.col("player1").struct["id"] == player.id)
                        .then(pl.col("result").list[1])
                        .otherwise(pl.col("result").list[0])
                        .sum()
                        .alias("sets_lost")
                    ),
                    (
                        pl.when(pl.col("player1").struct["id"] == player.id)
                        .then(pl.col("sets").list[0])
                        .otherwise(pl.col("sets").list[1])
                        .sum()
                        .alias("balls_won")
                    ),
                    (
                        pl.when(pl.col("player1").struct["id"] == player.id)
                        .then(pl.col("sets").list[1])
                        .otherwise(pl.col("sets").list[0])
                        .sum()
                        .alias("balls_lost")
                    ),
                    (pl.col("sets_won") - pl.col("sets_lost")).alias("set_difference"),
                    (pl.col("balls_won") - pl.col("balls_lost")).alias(
                        "ball_difference"
                    ),
                )
            )
        stats = pl.DataFrame(stats)
        self._stats[round] = stats
        return stats

    def _get_buchholz_scores(
        self, round: int = None, update: bool = False
    ) -> pl.DataFrame:
        if round is None:
            round = self.rounds_completed

        if round in self._buchholz_scores and not update:
            return self._buchholz_scores[round]

        stats = self._get_stats(round)
        buchholz_scores = []
        for player in self.players:
            opponent_ids = (
                self.matches_df.filter(pl.col("round") <= round)
                .filter(pl.col("is_completed"))
                .filter(
                    (pl.col("player1").struct["id"] == player.id)
                    | (pl.col("player2").struct["id"] == player.id)
                )
                .select(
                    pl.when(pl.col("player1").struct["id"] == player.id)
                    .then(pl.col("player2").struct["id"])
                    .otherwise(pl.col("player1").struct["id"])
                    .alias("opponent_id")
                )
                .unique()["opponent_id"]
                .to_list()
            )
            buchholz_score = sum(
                stats.filter(pl.col("player_id").isin(opponent_ids))["wins"]
            )
            buchholz_scores.append({player.id: buchholz_score})

        buchholz_scores = pl.DataFrame(buchholz_scores)
        self._buchholz_scores[round] = buchholz_scores
        return buchholz_scores

    def _get_direct_encounter_matrix(
        self, round: int = None, update: bool = False
    ) -> pl.DataFrame:
        if round is None:
            round = self.rounds_completed

        if round in self._direct_encounter_matrix and not update:
            return self._direct_encounter_matrix[round]
        # Add direct match results
        direct_encounters = []
        for player in self.players:
            direct_encounter = {p.id: 0 for p in self.players}

            matches = (
                self.matches_df.filter(pl.col("round") <= round)
                .filter(
                    (pl.col("player1").struct["id"] == player.id)
                    | (pl.col("player2").struct["id"] == player.id)
                )
                .filter(pl.col("is_completed"))
            )

            for match in matches.to_dicts():
                opponent_id = (
                    match["player1"]["id"]
                    if match["player1"]["id"] != player.id
                    else match["player2"]["id"]
                )
                direct_encounter[opponent_id] = (
                    1 if match["winner"] == player.id else -1
                )
            direct_encounters.append(direct_encounter)

        direct_encounters = pl.DataFrame(direct_encounters)
        self._direct_encounter_matrix[round] = direct_encounters
        return direct_encounters

    def _get_played_matches(self, round: int = None) -> Set[Tuple[str, str]]:
        if round is None:
            round = self.rounds_completed
        matches = (
            self.matches_df.filter(pl.col("round") <= round)
            .filter(pl.col("is_completed"))
            .to_dicts()
        )
        return {
            [(m["player1"]["id"], m["player2"]["id"]) for m in matches]
            + [(m["player2"]["id"], m["player1"]["id"]) for m in matches]
        }

    @property
    def direct_encounter_matrix(self) -> pl.DataFrame:
        return self._get_direct_encounter_matrix()

    @property
    def buchholz_scores(self) -> pl.DataFrame:
        return self._get_buchholz_scores()

    @property
    def stats(self) -> pl.DataFrame:
        return self._get_stats()

    def _get_wins(self, player_id: str, round: str | None = None) -> int:
        if round is None:
            round = self.rounds_completed
        return self._get_stats(round).filter(pl.col("player_id") == player_id)[
            0, "wins"
        ]

    def _get_buchholz_score(self, player_id: str, round: str | None = None) -> int:
        if round is None:
            round = self.rounds_completed
        return self._get_buchholz_scores(round).filter(pl.col("player_id") == player_id)[
            0, "buchholz_score"
        ]

    def _get_set_difference(self, player_id: str, round: int | None = None) -> int:
        if round is None:
            round = self.rounds_completed
        return self._get_stats(round).filter(pl.col("player_id") == player_id)[
            0, "set_difference"
        ]

    def _get_ball_difference(self, player_id: str, round: int | None = None) -> int:
        if round is None:
            round = self.rounds_completed
        return self._get_stats(round).filter(pl.col("player_id") == player_id)[
            0, "ball_difference"
        ]

    def _get_direct_match_wins(
        self, player_id: str, tied_player_ids: List[str], round: int | None = None
    ) -> int:
        if round is None:
            round = self.rounds_completed

        return (
            self.matches_df.filter(pl.col("round") <= round)
            .filter(pl.col("is_completed"))
            .filter(
                (pl.col("player1").struct["id"] == player_id)
                | (pl.col("player2").struct["id"] == player_id)
            )
            .filter(
                pl.col("player1").struct["id"].isin(tied_player_ids)
                | pl.col("player2").struct["id"].isin(tied_player_ids)
            )
            .filter(pl.col("winner") == player_id)
        ).shape[0]

    def _get_ranking(self, round: int | None = None) -> List[Player]:
        raise NotImplementedError

    @property
    def played_matches(self) -> Set[Tuple[str, str]]:
        return self._get_played_matches()

    @property
    def ranking(self) -> List[Player]:
        return self._get_ranking()

    def gen_matches(self) -> List[Match]:
        raise NotImplementedError


class SwissSystemGroup(BaseGroup):
    def __init__(self, players: List[Player], name: str, date: dt.date):
        super().__init__(players, name)
        self.date = date

    def gen_first_round(self):
        top_half = self.players[: len(self.players) // 2]
        bottom_half = self.players[len(self.players) // 2:]
        top_half.sort(key=lambda p: p.score, reverse=True)
        random.shuffle(bottom_half)

        self.round += 1

        for p1, p2 in zip(top_half, bottom_half):
            self.matches.append(Match(p1, p2, self.round))

    def gen_next_round(self) -> List[Match]:
        sorted_players = self.players[:]
        sorted_players.sort(key=lambda p: self.wins(p.id), reverse=True)

        matches = []
        n = len(sorted_players)

        # Add a dummy player if the number of players is odd
        if n % 2 == 1:
            sorted_players.append(None)

        while len(sorted_players) > 1:
            p1 = sorted_players.pop(0)
            p2 = None
            for i, potential_opponent in enumerate(sorted_players):
                if (
                    potential_opponent
                    and (p1.id, potential_opponent.id) not in self.played_matches
                    and (p1.id, potential_opponent.id) not in self.excluded_matches
                ):
                    p2 = sorted_players.pop(i)
                    break
            if p2:
                matches.append(Match(p1, p2))
            elif p1:  # If p2 is None, p1 gets a bye
                matches.append(Match(p1, None))

        self.matches.extend(matches)
        self.round += 1

    def gen_matches(self) -> List[Match]:
        if self.round == 0:
            self.gen_first_round()
        else:
            self.gen_next_round()

    def _get_ranking(self, round: int | None = None) -> List[Player]:
        if round is None:
            round = self.rounds_completed

        def sort_key(player: Player) -> tuple:
            wins = self._get_wins(player.id, round)
            buchholz = self._get_buchholz_scores(player.id, round)
            set_diff = self._get_set_difference(player.id, round)
            ball_diff = self._get_ball_difference(player.id, round)
            player_score = player.id  # Using player ID as score (smaller is better)

            return (wins, buchholz, set_diff, -player_score, ball_diff)

        # First sort by primary criteria
        players = self.players[:]
        players.sort(key=sort_key, reverse=True)

        # Handle tied players
        i = 0
        while i < len(players):
            # Find players with same wins and buchholz
            tied_start = i
            while (
                i + 1 < len(players)
                and self._get_wins(players[i].id, round)
                == self._get_wins(players[i + 1].id, round)
                and self._get_buchholz_scores(players[i].id, round)
                == self._get_buchholz_scores(players[i + 1].id, round)
            ):
                i += 1

            # If we found tied players
            if i > tied_start:
                tied_players = players[tied_start:i + 1]
                # Sort tied players by direct matches if possible
                all_played = all(
                    any(
                        m.involves_players(p1, p2)
                        for m in self._get_matches_until_round(round)
                        if m.is_complete()
                    )
                    for p1 in tied_players
                    for p2 in tied_players
                    if p1 != p2
                )

                if all_played:
                    # Sort by number of direct match wins
                    tied_players.sort(
                        key=lambda p: self._get_direct_match_wins(
                            p, tied_players, round
                        ),
                        reverse=True,
                    )
                    players[tied_start:i + 1] = tied_players

            i += 1

        return players

    # def get_rankings(self) -> List[Player]:
    #     """Get the ranking of players in the group using the Swiss system.

    #     Order:
    #     1. Number of wins
    #     2. Buchholz score
    #     3. Direct encounters (if no circular dependency)
    #     4. Set difference (all matches)
    #     5. Ball difference (all matches)
    #     """

    #     def buchholz_score(player: Player) -> int:
    #         score = 0
    #         for match in self.matches:
    #             if match.player1 == player:
    #                 score += self.results[match.player2.id].wins
    #             elif match.player2 == player:
    #                 score += self.results[match.player1.id].wins
    #         return score

    #     def direct_encounter_matrix(players: List[Player]) -> Dict[str, Dict[str, int]]:
    #         """Returns matrix of direct encounter results between players"""
    #         matrix = {p.id: {op.id: 0 for op in players} for p in players}
    #         for match in self.matches:
    #             if match.player1 in players and match.player2 in players:
    #                 matrix[match.winner.id][match.loser.id] = 1
    #         return matrix

    #     def has_circular_dependency(players: List[Player]) -> bool:
    #         matrix = direct_encounter_matrix(players)
    #         for p1 in players:
    #             for p2 in players:
    #                 for p3 in players:
    #                     if (
    #                         matrix[p1.id][p2.id]
    #                         and matrix[p2.id][p3.id]
    #                         and matrix[p3.id][p1.id]
    #                     ):
    #                         return True
    #         return False

    #     # First sort by wins and Buchholz
    #     players = self.players[:]
    #     players.sort(
    #         key=lambda p: (self.results[p.id].wins, buchholz_score(p)), reverse=True
    #     )

    #     # Group players with same wins and Buchholz
    #     ranking = []
    #     i = 0
    #     while i < len(players):
    #         group_start = i
    #         wins = self.results[players[i].id].wins
    #         buch = buchholz_score(players[i])

    #         while (
    #             i < len(players)
    #             and self.results[players[i].id].wins == wins
    #             and buchholz_score(players[i]) == buch
    #         ):
    #             i += 1

    #         group = players[group_start:i]
    #         if len(group) > 2 and has_circular_dependency(group):
    #             # Sort group by overall set/ball difference
    #             group.sort(
    #                 key=lambda p: (
    #                     self.results[p.id].sets_won - self.results[p.id].sets_lost,
    #                     self.results[p.id].balls_won - self.results[p.id].balls_lost,
    #                 ),
    #                 reverse=True,
    #             )

    #         ranking.extend(group)
    #     self.ranking[self.round] = ranking
    #     return ranking

    # def _get_rankings_classic(self) -> List[Player]:
    #     """
    #     Get the ranking of players in the group.

    #     The ranking is based on the number of wins, sets won and lost.
    #     If two players have the same number of wins, the player with the most
    #     sets won is ranked higher. If the number of sets won is the same, the
    #     player with the highest difference between sets won and sets lost is
    #     ranked higher. If all these values are the same, the direct match result
    #     is used to determine the ranking. If there is no direct match result, or
    #     if the direct match was a draw, or if there is a group of players with
    #     the same ranking values, and the direct match result is not enough to
    #     determine the ranking, the balls won and lost are used to determine.
    #     """

    #     def get_ranking_key(player: Player):
    #         r = self.results[player.id]
    #         return (r.wins, r.sets_won, r.sets_won - r.sets_lost)

    #     def compare_group(players: List[Player]):
    #         direct_wins = {p.id: 0 for p in players}
    #         for match in self.matches:
    #             if match.player1 in players and match.player2 in players:
    #                 direct_wins[match.winner.id] += 1

    #         def _get_ranking_key(player: Player):
    #             return (direct_wins[player.id], get_ranking_key(player))

    #         return sorted(players, key=_get_ranking_key, reverse=True)

    #     return sorted(self.players, key=get_ranking_key, reverse=True)

    # def _get_rankings_swiss(self) -> List[Player]:
    #     """
    #     Get the ranking of players in the group using the Swiss system.

    #     Order:
    #     1. Number of wins
    #     2. Buchholz score
    #     3. Direct encounters (if no circular dependency)
    #     4. Set difference (all matches)
    #     5. Ball difference (all matches)
    #     """

    #     def buchholz_score(player: Player) -> int:
    #         score = 0
    #         for match in self.matches:
    #             if match.player1 == player:
    #                 score += self.results[match.player2.id].wins
    #             elif match.player2 == player:
    #                 score += self.results[match.player1.id].wins
    #         return score

    #     def direct_encounter_matrix(players: List[Player]) -> Dict[str, Dict[str, int]]:
    #         """Returns matrix of direct encounter results between players"""
    #         matrix = {p.id: {op.id: 0 for op in players} for p in players}
    #         for match in self.matches:
    #             if match.player1 in players and match.player2 in players:
    #                 matrix[match.winner.id][match.loser.id] = 1
    #         return matrix

    #     def has_circular_dependency(players: List[Player]) -> bool:
    #         matrix = direct_encounter_matrix(players)
    #         for p1 in players:
    #             for p2 in players:
    #                 for p3 in players:
    #                     if (
    #                         matrix[p1.id][p2.id]
    #                         and matrix[p2.id][p3.id]
    #                         and matrix[p3.id][p1.id]
    #                     ):
    #                         return True
    #         return False

    #     # First sort by wins and Buchholz
    #     players = self.players[:]
    #     players.sort(
    #         key=lambda p: (self.results[p.id].wins, buchholz_score(p)), reverse=True
    #     )

    #     # Group players with same wins and Buchholz
    #     ranking = []
    #     i = 0
    #     while i < len(players):
    #         group_start = i
    #         wins = self.results[players[i].id].wins
    #         buch = buchholz_score(players[i])

    #         while (
    #             i < len(players)
    #             and self.results[players[i].id].wins == wins
    #             and buchholz_score(players[i]) == buch
    #         ):
    #             i += 1

    #         group = players[group_start:i]
    #         if len(group) > 2 and has_circular_dependency(group):
    #             # Sort group by overall set/ball difference
    #             group.sort(
    #                 key=lambda p: (
    #                     self.results[p.id].sets_won - self.results[p.id].sets_lost,
    #                     self.results[p.id].balls_won - self.results[p.id].balls_lost,
    #                 ),
    #                 reverse=True,
    #             )

    #         ranking.extend(group)
    #     self.ranking[self.round] = ranking
    #     return ranking

    # def _generate_berger_table_matches(self) -> List[Match]:
    #     """
    #     Generate matches using the Berger Table system.

    #     The Berger Table is a method used to schedule round-robin tournaments.
    #     It ensures that each player plays against every other player exactly once.
    #     """
    #     n = len(self.players)
    #     rounds = []
    #     players = self.players[:]
    #     if n % 2 == 1:
    #         players.append(None)  # Add a dummy player for odd number of players

    #     for round in range(n - 1):
    #         round_matches = []
    #         for i in range(n // 2):
    #             p1 = players[i]
    #             p2 = players[n - 1 - i]
    #             if p1 and p2:
    #                 round_matches.append(Match(p1, p2))
    #         players.insert(1, players.pop())  # Rotate players
    #         rounds.append(round_matches)
    #         self.round += 1

    #     self.matches = [match for round in rounds for match in round]
    #     return self.matches

    # def _generate_round_robin_matches(self) -> List[Match]:
    #     """
    #     Generate matches using the round-robin system.

    #     In a round-robin tournament, each player plays against every other player in the group.
    #     """
    #     matches = []
    #     for i, p1 in enumerate(self.players):
    #         for p2 in self.players[i + 1 :]:
    #             matches.append(Match(p1, p2))
    #     self.matches = matches
    #     return matches

    # def _generate_swiss_system_matches(self) -> List[Match]:
    #     """
    #     Generate matches using the Swiss system.

    #     In the Swiss system, players are paired based on their current scores,
    #     with the goal of matching players with similar performance.
    #     """
    #     players = self.players[:]
    #     random.shuffle(players)
    #     sorted_players = sorted(
    #         players, key=lambda p: self.results[p.id].wins, reverse=True
    #     )
    #     matches = []
    #     n = len(sorted_players)

    #     # Add a dummy player if the number of players is odd
    #     if n % 2 == 1:
    #         sorted_players.append(None)

    #     while len(sorted_players) > 1:
    #         p1 = sorted_players.pop(0)
    #         p2 = None
    #         for i, potential_opponent in enumerate(sorted_players):
    #             if (
    #                 potential_opponent
    #                 and (p1.id, potential_opponent.id) not in self.played_matches
    #             ):
    #                 p2 = sorted_players.pop(i)
    #                 break
    #         if p2:
    #             matches.append(Match(p1, p2))
    #         elif p1:  # If p2 is None, p1 gets a bye
    #             matches.append(Match(p1, None))

    #     self.matches.extend(matches)
    #     self.round += 1
    #     return matches
