from datetime import date
import random
from ttourney.models.tournament import Tournament
from ttourney.models.player import Player

def simulate_tournament():
    # Create tournament
    tournament = Tournament("Summer Championship 2023", date(2023, 7, 1))

    # Create 12 players with different skill levels
    names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", 
             "Grace", "Henry", "Ivy", "Jack", "Kelly", "Luis"]
    
    # Create players with scores between 1000-2000
    players = [
        Player(name=name, score=random.randint(1000, 2000))
        for name in names
    ]

    # Add players to tournament
    for player in players:
        tournament.add_player(player)

    # Create 3 groups with 4 players each
    tournament.create_groups(players_per_group=4)

    # Print initial groups
    print("\nInitial Groups:")
    for group in tournament.groups:
        print(f"\n{group.name}:")
        for player in group.players:
            print(f"  {player.name} (Score: {player.score})")

    # Simulate group stage
    print("\nSimulating group stage...")
    tournament.simulate()

    # Print group results
    print("\nGroup Results:")
    for group in tournament.groups:
        print(f"\n{group.name}:")
        rankings = group.get_rankings()
        for i, player in enumerate(rankings, 1):
            stats = group.results[player.id]
            print(f"  {i}. {player.name}: {stats['wins']} wins, {stats['sets']} sets")

    # Setup and simulate knockout stage (top 2 from each group)
    print("\nSetting up knockout stage...")
    tournament.setup_knockout_stage(players_per_group=2)

    # Print knockout results
    print("\nKnockout Stage Results:")
    for i, match in enumerate(tournament.knockout_matches, 1):
        if match.winner:
            sets_str = ", ".join([f"{s[0]}-{s[1]}" for s in match.sets])
            print(f"Match {i}: {match.player1.name} vs {match.player2.name}")
            print(f"Winner: {match.winner.name} ({sets_str})")

if __name__ == "__main__":
    simulate_tournament()
