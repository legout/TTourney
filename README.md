# TTourney - Table Tennis Tournament Manager

A Python library for managing table tennis tournaments with support for various tournament formats and match systems.

## Features

- Multiple tournament formats:
  - Swiss System
  - Round Robin (Berger Table)
  - Single Elimination with qualification rounds
  - Double Elimination (planned)

- Comprehensive player management with:
  - Player rankings
  - Match history
  - Statistics tracking
  - Buchholz scoring for Swiss system

- Flexible match recording:
  - Set-by-set scoring
  - Automatic winner determination
  - Match status tracking

- Tournament organization:
  - Group stage management
  - Knockout stage progression
  - Player seeding
  - Automatic match generation

## Installation

```bash
pip install ttourney
```

## Quick Start

```python
from ttourney.models import Tournament, Player
from datetime import date

# Create a tournament
tournament = Tournament("City Championships 2023", date.today())

# Add players
tournament.add_player(Player("John", "Doe", score=1200))
tournament.add_player(Player("Jane", "Smith", score=1150))
# ... add more players

# Create groups (e.g., 4 players per group)
tournament.create_groups(players_per_group=4)

# Setup knockout stage (e.g., top 2 from each group advance)
tournament.setup_knockout_stage(players_per_group=2)

# For testing/demo purposes, simulate the tournament
tournament.simulate()
```

## Tournament Formats

### Swiss System
- Players meet opponents with similar scores
- Suitable for large tournaments with limited time
- Uses Buchholz scoring for tiebreaks

### Round Robin (Berger Table)
- Every player plays against every other player
- Fair but time-consuming
- Perfect for small groups or leagues

### Single Elimination
- Players are eliminated after one loss
- Optional qualification rounds
- Fastest format to determine a winner

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.