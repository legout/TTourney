from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class TournamentDB(Base):
    __tablename__ = "tournaments"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    date = Column(Date, nullable=False)


class PlayerDB(Base):
    __tablename__ = "players"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    age = Column(Integer)
    gender = Column(String)
    club = Column(String)
    tournament_id = Column(String, ForeignKey("tournaments.id"))

class GroupDB(Base):
    __tablename__ = "groups"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    tournament_id = Column(String, ForeignKey("tournaments.id"))
    players = relationship("PlayerDB", backref="group", lazy="dynamic")


class MatchDB(Base):
    __tablename__ = "matches"
    id = Column(String, primary_key=True)
    tournament_id = Column(String, ForeignKey("tournaments.id"))
    player1_id = Column(String, ForeignKey("players.id"))
    player2_id = Column(String, ForeignKey("players.id"))
    sets = Column(JSON)
    winner_id = Column(String, ForeignKey("players.id"))
    is_knockout = Column(Boolean, default=False)
    group_name = Column(String, nullable=True)
