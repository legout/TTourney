from datetime import date
from typing import List
import random

from ..models.player import Player
from ..models.group import (
    SwissSystemGroup, 
    RoundRobinGroup, 
    BergerTableGroup,
    SingleEliminationGroup
)


def generate_sample_players(n: int = 8) -> List[Player]:
    """Generate n sample players with random scores."""
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eve", "Frank",
                  "George", "Helen", "Ian", "Julia", "Kevin", "Laura", "Mike", "Nina"]
    last_names = ["Smith", "Jones", "Brown", "Wilson", "Taylor", "Davis", "Miller",
                 "Moore", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin"]
    clubs = ["TTC Red Star", "SV Blue Eagles", "Green Dragons", "Yellow Knights"]
    
    players = []
    for i in range(n):
        player = Player(
            first_name=random.choice(first_names),
            last_name=random.choice(last_names),
            score=random.randint(1000, 2000),
            club=random.choice(clubs),
            age=random.randint(18, 45)
        )
        players.append(player)
    return players

def simulate_set(player1_score, player2_score):
    advantage_factor = 0.01 * (player1_score - player2_score) / 100
    point_advantage = round((player1_score - player2_score) / 200)
    points1 = point_advantage
    points2 = 0
    while True:
        # Simulate each point with slight advantage to higher-rated player
        if random.random() < 0.5 + advantage_factor:
            points1 += 1
        else:
            points2 += 1
            
        # Check win conditions
        if points1 >= 11 and points1 >= points2 + 2:
            return points1, points2
        elif points2 >= 11 and points2 >= points1 + 2:
            return points1, points2

def simulate_match(player1, player2):
    sets_won =[0, 0]
    sets = []
    while max(sets_won) < 3:
        set_ = simulate_set(player1.score, player2.score)
        if set_[0] > set_[1]:
            sets_won[0] += 1
        else:
            sets_won[1] += 1
        sets.append(set_)
    return sets

def simulate_swiss_tournament(n_players: int = 8, n_rounds: int = 3):
    """Simulate a Swiss System tournament."""
    players = generate_sample_players(n_players)
    group = SwissSystemGroup(players, "Swiss Example", date.today())
    
    print(f"\nSimulating Swiss System Tournament with {n_players} players")
    print("Initial Rankings:")
    for p in sorted(players, key=lambda x: x.score, reverse=True):
        print(f"  {p}")
    
    # Generate and simulate rounds
    for round_num in range(n_rounds):
        group._gen_matches()
        current_round = group.rounds[-1]
        print(f"\nRound {round_num + 1} Matches:")
        for match in current_round.matches:
            # Simulate match result
            # a player wins a set if they score 11 points first and have at least 2 points more than the opponent.
            # a player wins the match if they win 3 sets.
            # Try to simulate a realistic match by giving the player with the higher score a slight advantage.
            sets = simulate_match(match.player1, match.player2)
            match.set_sets(sets)
            print(f"  {match}")
    
    print("\nFinal Rankings:")
    for p in group.ranking:
        stats = group.stats.filter(pl.col("player_id") == p.id).to_dicts()[0]
        print(f"  {p.name}: {stats['wins']} wins, {stats['sets_won']}-{stats['sets_lost']} sets")


def simulate_round_robin(n_players: int = 6):
    """Simulate a Round Robin tournament."""
    players = generate_sample_players(n_players)
    group = RoundRobinGroup(players, "Round Robin Example", date.today())
    
    print(f"\nSimulating Round Robin Tournament with {n_players} players")
    print("Initial Rankings:")
    for p in sorted(players, key=lambda x: x.score, reverse=True):
        print(f"  {p}")
    
    group._gen_matches()
    for round in group.rounds:
        print(f"\n{round.name} Matches:")
        for match in round.matches:
            # Simulate match result
            sets = [(random.randint(5, 11), random.randint(0, 9)) for _ in range(3)]
            match.set_sets(sets)
            print(f"  {match}")
    
    print("\nFinal Rankings:")
    for p in group.ranking:
        stats = group.stats.filter(pl.col("player_id") == p.id).to_dicts()[0]
        print(f"  {p.name}: {stats['wins']} wins, {stats['sets_won']}-{stats['sets_lost']} sets")


def simulate_berger_table(n_players: int = 6):
    """Simulate a Berger Table tournament."""
    players = generate_sample_players(n_players)
    group = BergerTableGroup(players, "Berger Table Example", date.today())
    
    print(f"\nSimulating Berger Table Tournament with {n_players} players")
    print("Initial Rankings:")
    for p in sorted(players, key=lambda x: x.score, reverse=True):
        print(f"  {p}")
    
    group._gen_matches()
    for round in group.rounds:
        print(f"\n{round.name} Matches:")
        for match in round.matches:
            # Simulate match result
            sets = [(random.randint(5, 11), random.randint(0, 9)) for _ in range(3)]
            match.set_sets(sets)
            print(f"  {match}")
    
    print("\nFinal Rankings:")
    for p in group.ranking:
        stats = group.stats.filter(pl.col("player_id") == p.id).to_dicts()[0]
        print(f"  {p.name}: {stats['wins']} wins, {stats['sets_won']}-{stats['sets_lost']} sets")


def simulate_single_elimination(n_players: int = 8):
    """Simulate a Single Elimination tournament."""
    players = generate_sample_players(n_players)
    group = SingleEliminationGroup(players, "Single Elimination Example", date.today())
    
    print(f"\nSimulating Single Elimination Tournament with {n_players} players")
    print("Initial Rankings:")
    for p in sorted(players, key=lambda x: x.score, reverse=True):
        print(f"  {p}")
    
    group._gen_matches()
    for round in group.rounds:
        print(f"\n{round.name} ({round.stage}) Matches:")
        for match in round.matches:
            # Simulate match result
            sets = [(random.randint(5, 11), random.randint(0, 9)) for _ in range(3)]
            match.set_sets(sets)
            print(f"  {match}")
    
    print("\nFinal Rankings:")
    for p in group.ranking:
        print(f"  {p}")


if __name__ == "__main__":
    # Run all simulations
    simulate_swiss_tournament()
    simulate_round_robin()
    simulate_berger_table()
    simulate_single_elimination()
