"""
models.py
=========
Lightweight dataclasses used for persistence.
These are intentionally separate from the live game objects so that
the save format stays stable even if game classes evolve.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
import datetime


@dataclass
class PlayerRecord:
    """Snapshot of a single player at game end."""
    name:        str
    color:       str
    vp:          int
    resources:   Dict[str, int] = field(default_factory=dict)
    settlements: List[int]      = field(default_factory=list)
    cities:      List[int]      = field(default_factory=list)
    roads:       List[List]     = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PlayerRecord":
        return cls(**d)


@dataclass
class GameRecord:
    """Complete record of one finished (or saved) game."""
    game_id:      str
    timestamp:    str
    players:      List[PlayerRecord] = field(default_factory=list)
    winner:       str                = ""
    turn_count:   int                = 0
    log_excerpt:  List[str]          = field(default_factory=list)

    @classmethod
    def create_new(cls, players, winner_name: str,
                   turn_count: int, log: List[str]) -> "GameRecord":
        import uuid
        return cls(
            game_id     = str(uuid.uuid4())[:8],
            timestamp   = datetime.datetime.now().isoformat(timespec="seconds"),
            players     = [
                PlayerRecord(
                    name        = p.name,
                    color       = p.color,
                    vp          = p.vp,
                    resources   = dict(p.resources),
                    settlements = list(p.settlements),
                    cities      = list(p.cities),
                    roads       = [list(e) for e in p.roads],
                )
                for p in players
            ],
            winner      = winner_name,
            turn_count  = turn_count,
            log_excerpt = log[-20:],
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GameRecord":
        players = [PlayerRecord.from_dict(p) for p in d.pop("players", [])]
        record  = cls(**d)
        record.players = players
        return record
