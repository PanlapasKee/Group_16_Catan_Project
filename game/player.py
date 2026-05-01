"""
player.py
=========
Defines the Player class that tracks resources, buildings, and victory points.
"""

from __future__ import annotations
from typing import List, Dict
from utils.constants import RESOURCES, BUILDING_COSTS, VICTORY_POINTS, PLAYER_COLORS
from utils.helpers import can_afford, subtract_resources, add_resources


class Player:
    """
    Represents one Catan player.

    Attributes
    ----------
    name        : str
    color       : str      Hex color string for GUI rendering.
    resources   : dict     {resource: count}
    settlements : list     List of vertex ids where settlements stand.
    cities      : list     List of vertex ids upgraded to cities.
    roads       : list     List of edge ids occupied by roads.
    vp          : int      Current victory-point total.
    """

    def __init__(self, name: str, player_index: int) -> None:
        self.name: str = name
        self.color: str = PLAYER_COLORS[player_index % len(PLAYER_COLORS)]

        # Start with zero of every resource
        self.resources: Dict[str, int] = {r: 0 for r in RESOURCES}

        # Structures placed on the board (stored as node/edge IDs)
        self.settlements: List[int] = []
        self.cities:      List[int] = []
        self.roads:       List[tuple] = []

        # Limits (standard Catan)
        self._max_roads       = 15
        self._max_settlements =  5
        self._max_cities      =  4

    # ------------------------------------------------------------------
    # Resource helpers
    # ------------------------------------------------------------------

    def receive_resources(self, gains: Dict[str, int]) -> None:
        """Add resources to this player's stockpile."""
        add_resources(self.resources, gains)

    def spend_resources(self, cost: Dict[str, int]) -> None:
        """
        Deduct cost from the player's resources.
        :raises ValueError: if player cannot afford the cost.
        """
        if not can_afford(self.resources, cost):
            raise ValueError(
                f"{self.name} cannot afford this action "
                f"(needs {cost}, has {self.resources})."
            )
        subtract_resources(self.resources, cost)

    def can_afford(self, cost: Dict[str, int]) -> bool:
        """Return True if the player has enough resources."""
        return can_afford(self.resources, cost)

    def total_resources(self) -> int:
        """Total number of resource cards in hand."""
        return sum(self.resources.values())

    # ------------------------------------------------------------------
    # Building helpers
    # ------------------------------------------------------------------

    def build_road(self, edge: tuple) -> None:
        """
        Record a new road.
        :raises ValueError: if road limit reached or edge already used.
        """
        if len(self.roads) >= self._max_roads:
            raise ValueError(f"{self.name} has no roads left to build.")
        if edge in self.roads:
            raise ValueError(f"Road already exists on edge {edge}.")
        self.roads.append(edge)

    def build_settlement(self, vertex: int) -> None:
        """
        Record a new settlement.
        :raises ValueError: if settlement limit reached or vertex occupied.
        """
        if len(self.settlements) >= self._max_settlements:
            raise ValueError(f"{self.name} has no settlements left to build.")
        if vertex in self.settlements:
            raise ValueError(f"Vertex {vertex} already has a settlement.")
        self.settlements.append(vertex)

    def upgrade_to_city(self, vertex: int) -> None:
        """
        Upgrade an existing settlement to a city.
        :raises ValueError: if no settlement at vertex or city limit reached.
        """
        if vertex not in self.settlements:
            raise ValueError(f"{self.name} has no settlement at vertex {vertex}.")
        if len(self.cities) >= self._max_cities:
            raise ValueError(f"{self.name} has no cities left to build.")
        self.settlements.remove(vertex)
        self.cities.append(vertex)

    # ------------------------------------------------------------------
    # Victory points
    # ------------------------------------------------------------------

    @property
    def vp(self) -> int:
        """Calculate current victory points from structures."""
        return (len(self.settlements) * VICTORY_POINTS["settlement"] +
                len(self.cities)      * VICTORY_POINTS["city"])

    # ------------------------------------------------------------------
    # Serialisation helpers (for save/load)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "color":       self.color,
            "resources":   self.resources,
            "settlements": self.settlements,
            "cities":      self.cities,
            "roads":       [list(e) for e in self.roads],
            "vp":          self.vp,
        }

    @classmethod
    def from_dict(cls, data: dict, player_index: int) -> "Player":
        p = cls(data["name"], player_index)
        p.color       = data["color"]
        p.resources   = data["resources"]
        p.settlements = data["settlements"]
        p.cities      = data["cities"]
        p.roads       = [tuple(e) for e in data["roads"]]
        return p

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (f"Player({self.name!r}, vp={self.vp}, "
                f"resources={self.resources})")
