import datetime as dt
import random
from typing import List, Set, Tuple

import pandas as pd
import polars as pl

from .match import Match
from .player import Player
from .round import Round


class BaseGroup:
    def __init__(self, players: List[Player], name: str):
        self.name = name
        self.players = players
        self.players.sort(key=lambda p: p.score, reverse=True)
        self.rounds: List[Round] = []
        #self.ranking: List[Player] = self.players[:]
        self.excluded_matches: Set[Tuple[str, str]] = set()
        self._stats = {}
        self._buchholz_scores = {}
        self._direct_encounter_matrix = {}

    @property
    def matches(self) -> List[Match]:
        return [m for r in self.rounds for m in r.matches]

    @property
    def current_round_number(self) -> int:
        return len(self.rounds)

    @property
    def matches_df(self) -> pd.DataFrame:
        if not self.matches:
            return pl.DataFrame()
        return pl.DataFrame([m.as_dict() for m in self.matches])

    @property
    def rounds_completed(self) -> int:
        return sum(1 for r in self.rounds if r.is_completed)

    def add_round(self, name: str = None, stage: str = None) -> Round:
        round_num = self.current_round_number + 1
        new_round = Round(round_num, [], name, stage)
        self.rounds.append(new_round)
        return new_round

    @property
    def players_df(self) -> pd.DataFrame:
        if len(self.players) == 0:
            return pl.DataFrame()
        return pl.DataFrame([p.as_dict() for p in self.players])

    @property
    def matches_per_round(self) -> int:
        return len(self.players) // 2

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
                    (pl.col("winner") == player.id).cast(pl.Int32).sum().alias("wins"),
                    (pl.col("winner") != player.id)
                    .cast(pl.Int32)
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
        return self._get_buchholz_scores(round).filter(
            pl.col("player_id") == player_id
        )[0, "buchholz_score"]

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

    @property
    def played_matches(self) -> Set[Tuple[str, str]]:
        return self._get_played_matches()

    def _get_ranking(self, round: int | None = None) -> List[Player]:
        raise NotImplementedError

    @property
    def ranking(self) -> List[Player]:
        return self._get_ranking()

    def gen_matches(self) -> List[Match]:
        raise NotImplementedError


class SwissSystemGroup(BaseGroup):
    def __init__(self, players: List[Player], name: str, date: dt.date):
        super().__init__(players, name)
        self.date = date

    def _gen_first_round(self):
        round = self.add_round("First Round")

        top_half = self.players[: len(self.players) // 2]
        bottom_half = self.players[len(self.players) // 2:]
        top_half.sort(key=lambda p: p.score, reverse=True)
        random.shuffle(bottom_half)

        for p1, p2 in zip(top_half, bottom_half):
            round.add_match(Match(p1, p2, round.number))

    def _gen_next_round(self):
        round = self.add_round(f"Round {self.current_round_number}")

        sorted_players = self.players[:]
        sorted_players.sort(key=lambda p: self._get_wins(p.id), reverse=True)

        # Rest of the existing matching logic, but use round.add_match()
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
                round.add_match(Match(p1, p2, round.number))
            elif p1:  # If p2 is None, p1 gets a bye
                round.add_match(Match(p1, None, round.number))

    def _gen_matches(self) -> List[Match]:
        if self.current_round_number == 0:
            self._gen_first_round()
        else:
            self._gen_next_round()

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


class BergerTableGroup(BaseGroup):
    def __init__(self, players: List[Player], name: str, date: dt.date):
        super().__init__(players, name)
        self.date = date

    def _gen_matches(self) -> List[Match]:
        """Generate matches using the Berger Table system.

        The Berger Table is a method used to schedule round-robin tournaments.
        It ensures that each player plays against every other player exactly once.
        """
        n = len(self.players)
        rounds = []
        players = self.players[:]

        # Add a dummy player for odd number of players
        if n % 2 == 1:
            players.append(None)
            n += 1

        # Generate all rounds
        for round_num in range(n - 1):
            round = self.add_round(f"Round {round_num + 1}")

            # Generate matches for this round
            for i in range(n // 2):
                p1 = players[i]
                p2 = players[n - 1 - i]
                if p1 and p2:  # Only create match if both players are real
                    match = Match(p1, p2, round.number, self.date)
                    round.add_match(match)

            # Rotate players for next round: keep first player fixed, rotate others
            players.insert(1, players.pop())
            rounds.append(round)

        # Add all matches to the group
        self.rounds.extend(rounds)
        return self.matches

    def _get_ranking(self, round: int | None = None) -> List[Player]:
        """Same ranking system as Swiss, but Berger Table doesn't need Buchholz scores"""
        if round is None:
            round = self.rounds_completed

        def sort_key(player: Player) -> tuple:
            wins = self._get_wins(player.id, round)
            set_diff = self._get_set_difference(player.id, round)
            ball_diff = self._get_ball_difference(player.id, round)
            player_score = player.id  # Using player ID as score (smaller is better)

            return (wins, set_diff, -player_score, ball_diff)

        # Sort players by primary criteria
        players = self.players[:]
        players.sort(key=sort_key, reverse=True)

        # Handle tied players similar to SwissSystemGroup
        i = 0
        while i < len(players):
            tied_start = i
            while i + 1 < len(players) and self._get_wins(
                players[i].id, round
            ) == self._get_wins(players[i + 1].id, round):
                i += 1

            if i > tied_start:
                tied_players = players[tied_start:i + 1]
                # Sort tied players by direct matches
                tied_players.sort(
                    key=lambda p: self._get_direct_match_wins(
                        p.id, [tp.id for tp in tied_players], round
                    ),
                    reverse=True,
                )
                players[tied_start:i + 1] = tied_players

            i += 1

        return players


class RoundRobinGroup(BaseGroup):
    def __init__(self, players: List[Player], name: str, date: dt.date):
        super().__init__(players, name)
        self.date = date

    def _gen_matches(self) -> List[Match]:
        """Simple round robin where each player plays against every other once"""
        n = len(self.players)
        for i, p1 in enumerate(self.players):
            for j in range(i + 1, n):
                p2 = self.players[j]
                round_num = i + 1  # Simple round assignment
                round = self.add_round(f"Round {round_num}")
                round.add_match(Match(p1, p2, round.number, self.date))
        return self.matches

    def _get_ranking(self, round: int | None = None) -> List[Player]:
        """Same ranking system as BergerTable"""
        if round is None:
            round = self.rounds_completed

        def sort_key(player: Player) -> tuple:
            wins = self._get_wins(player.id, round)
            set_diff = self._get_set_difference(player.id, round)
            ball_diff = self._get_ball_difference(player.id, round)
            player_score = player.id  # Using player ID as score (smaller is better)

            return (wins, set_diff, -player_score, ball_diff)

        # Sort players by primary criteria
        players = self.players[:]
        players.sort(key=sort_key, reverse=True)

        # Handle tied players similar to SwissSystemGroup
        i = 0
        while i < len(players):
            tied_start = i
            while i + 1 < len(players) and self._get_wins(
                players[i].id, round
            ) == self._get_wins(players[i + 1].id, round):
                i += 1

            if i > tied_start:
                tied_players = players[tied_start:i + 1]
                # Sort tied players by direct matches
                tied_players.sort(
                    key=lambda p: self._get_direct_match_wins(
                        p.id, [tp.id for tp in tied_players], round
                    ),
                    reverse=True,
                )
                players[tied_start:i + 1] = tied_players

            i += 1

        return players


class KnockoutGroup(BaseGroup):
    """Base class for knockout tournaments with qualification rounds"""

    def __init__(self, players: List[Player], name: str, date: dt.date):
        super().__init__(players, name)
        self.date = date
        self.stage_names = {
            2: "Final",
            4: "Semi Finals",
            8: "Quarter Finals",
            16: "Round of 16",
            32: "Round of 32",
        }

    def _get_knockout_size(self) -> int:
        """Get nearest power of 2 that fits the tournament"""
        n = len(self.players)
        size = 2
        while size < n:
            size *= 2
        return size // 2  # We want the largest size that's smaller than n

    def _get_qualified_count(self) -> int:
        """Get number of players directly qualifying for main round"""
        knockout_size = self._get_knockout_size()
        return max(0, 2 * knockout_size - len(self.players))

    def _get_qualification_pairs(self) -> List[Tuple[Player, Player]]:
        """Match players for qualification rounds"""
        # knockout_size = self._get_knockout_size()
        qualified_count = self._get_qualified_count()

        # Sort players by score
        sorted_players = sorted(self.players, key=lambda p: p.score, reverse=True)

        # Top players qualify directly
        # qualified = sorted_players[:qualified_count]
        remaining = sorted_players[qualified_count:]

        # Pair remaining players for qualification
        # Higher ranked vs lower ranked
        pairs = []
        n = len(remaining)
        for i in range(n // 2):
            pairs.append((remaining[i], remaining[n - 1 - i]))

        return pairs

    def _assign_stage_name(self, round_size: int) -> str:
        return self.stage_names.get(round_size, f"Round of {round_size}")


class SingleEliminationGroup(KnockoutGroup):
    def _get_seeded_pairs(
        self, players: List[Player], round_size: int
    ) -> List[Tuple[Player, Player]]:
        """Create properly seeded pairs for a knockout round.
        Uses standard tournament seeding to keep top seeds apart until later rounds."""
        if len(players) <= 2:
            return [(players[0], players[1])] if len(players) == 2 else []

        # Create seed positions for perfect bracket
        seeds = list(range(1, round_size + 1))

        # Standard tournament bracket ordering
        ordered_positions = []

        def fill_bracket(start: int, end: int):
            if start == end:
                return
            mid = (start + end) // 2
            ordered_positions.extend([start + 1, end + 1])
            fill_bracket(start, mid - 1)
            fill_bracket(mid, end - 1)

        fill_bracket(0, round_size - 1)

        # Map players to their positions
        seeded_players = sorted(players, key=lambda p: p.score, reverse=True)
        player_map = {pos: player for pos, player in zip(seeds, seeded_players)}

        # Create pairs based on ordered positions
        pairs = []
        for i in range(0, len(ordered_positions), 2):
            if i + 1 < len(ordered_positions):
                p1 = player_map.get(ordered_positions[i])
                p2 = player_map.get(ordered_positions[i + 1])
                if p1 and p2:  # Only create pair if both players exist
                    pairs.append((p1, p2))

        return pairs

    def _gen_matches(self) -> List[Match]:
        if self.rounds:
            return []  # All matches generated at start

        # Qualification round
        qual_pairs = self._get_qualification_pairs()
        if qual_pairs:
            qual_round = self.add_round("Qualification", "Qualification")
            for p1, p2 in qual_pairs:
                qual_round.add_match(Match(p1, p2, qual_round.number))

        # Generate knockout rounds
        knockout_size = self._get_knockout_size()
        current_size = knockout_size

        while current_size >= 2:
            stage_name = self._assign_stage_name(current_size)
            round = self.add_round(stage_name, stage_name)

            pairs = self._get_seeded_pairs(self.players, current_size)
            for p1, p2 in pairs:
                round.add_match(Match(p1, p2, round.number))

            current_size //= 2

    def _get_ranking(self, round: int | None = None) -> List[Player]:
        """Ranking based on stage reached and original seeding"""
        if round is None:
            round = self.rounds_completed

        # Track furthest stage reached by each player
        player_stages = {p.id: ("Not Qualified", -1, p.score) for p in self.players}

        # Order stages by importance
        stage_order = {
            "Final": 6,
            "Semi Finals": 5,
            "Quarter Finals": 4,
            "Round of 16": 3,
            "Round of 32": 2,
            "Qualification": 1,
        }

        for match in self.matches:
            if match.round <= round and match.is_completed:
                stage_value = stage_order.get(match.stage, 0)

                # Winner advances
                if match.winner:
                    current_stage = player_stages[match.winner.id]
                    player_stages[match.winner.id] = (
                        match.stage,
                        stage_value,
                        current_stage[2],
                    )

                # Loser gets eliminated at this stage
                if match.loser:
                    current_stage = player_stages[match.loser.id]
                    player_stages[match.loser.id] = (
                        match.stage,
                        stage_value,
                        current_stage[2],
                    )

        # Sort players by stage reached, then by original score
        players = self.players[:]
        players.sort(key=lambda p: player_stages[p.id], reverse=True)
        return players


class DoubleEliminationGroup(KnockoutGroup):
    def _gen_matches(self) -> List[Match]:
        """Similar to SingleEliminationGroup but with losers bracket"""
        # Implementation similar to SingleEliminationGroup but with additional
        # losers bracket matches. For brevity, I'm leaving this as an exercise
        # as it follows the same pattern but with more complexity.
        raise NotImplementedError("Double elimination not yet implemented")
