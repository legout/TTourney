import marimo

__generated_with = "0.11.4"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    from datetime import date
    from typing import List
    import random

    from ttourney.models.player import Player
    from ttourney.simulation.tournaments import generate_sample_players, simulate_match
    from ttourney.models.group import RoundRobinGroup, BergerTableGroup, SwissSystemGroup
    return (
        BergerTableGroup,
        List,
        Player,
        RoundRobinGroup,
        SwissSystemGroup,
        date,
        generate_sample_players,
        mo,
        random,
        simulate_match,
    )


@app.cell
def _(SwissSystemGroup, date, generate_sample_players):
    players = generate_sample_players(8)
    group_a = SwissSystemGroup(players, "Group A", date.today())
    #group_b = SwissSystemGroup(players[4:], "Group B", date.today())
    return group_a, players


@app.cell
def _(group_a):
    group_a._gen_first_round()
    return


@app.cell
def _(group_a):
    group_a.rounds
    return


@app.cell
def _(group_a, simulate_match):
    round = group_a.rounds[0]
    match_id = []
    sets = []
    for match in round.matches:
        match_id.append(match.id)
        sets.append(simulate_match(match.player1, match.player2))
    round.set_sets(match_id, sets)
    return match, match_id, round, sets


@app.cell
def _(group_a):
    import pyarrow as pa

    self = group_a

    df=pa.Table.from_pylist([{
                "name": self.name,
                "players": [p.as_dict() for p in self.players],
                # "matches": [m.as_dict() for m in self.matches],
                "rounds": [r.as_dict() for r in self.rounds],
            }])
    return df, pa, self


@app.cell
def _(mo):
    _df = mo.sql(
        f"""
        df
        """
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
