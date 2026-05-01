"""
game_engine.py
==============
Core game-loop controller.  Orchestrates:
  - Turn order
  - Dice rolling → resource distribution
  - Building validation and placement
  - Trading (bank 4:1)
  - Robber activation
  - Win-condition check

Data flow
---------
  GUI calls engine methods  →  engine mutates Board / Player state
  →  engine returns result dict  →  GUI re-renders
"""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum, auto

from game.board  import Board
from game.player import Player
from game.dice   import Dice
from utils.constants import (
    BUILDING_COSTS, WINNING_VP, ROBBER_NUMBER, RESOURCES
)


# ---------------------------------------------------------------------------
# Game phase enum
# ---------------------------------------------------------------------------

class GamePhase(Enum):
    SETUP_SETTLEMENT_1 = auto()   # Each player places 1st settlement + road
    SETUP_SETTLEMENT_2 = auto()   # Each player places 2nd settlement + road
    ROLL_DICE          = auto()   # Active player must roll
    ROBBER             = auto()   # Active player must move robber (rolled 7)
    ACTIONS            = auto()   # Build, trade, end turn
    GAME_OVER          = auto()


# ---------------------------------------------------------------------------
# GameEngine
# ---------------------------------------------------------------------------

class GameEngine:
    """
    Manages the full game lifecycle.

    Parameters
    ----------
    player_names : list[str]   2–4 player names.

    Key public methods
    ------------------
    start_game()
    roll_dice()      → dict with roll result + resources gained
    build(action, vertex/edge, player)
    trade_with_bank(player, give_resource, want_resource)
    move_robber(tile_id)
    end_turn()
    check_winner()   → Player | None
    """

    def __init__(self, player_names: List[str]) -> None:
        from utils.helpers import validate_player_count
        validate_player_count(len(player_names))

        self.board:   Board  = Board()
        self.players: List[Player] = [
            Player(name, i) for i, name in enumerate(player_names)
        ]
        self.dice:    Dice   = Dice()

        self.current_player_index: int       = 0
        self.phase:                GamePhase = GamePhase.SETUP_SETTLEMENT_1
        self.winner:               Optional[Player] = None

        # Setup phase tracking
        self._setup_turn_order: List[int] = []
        self._setup_index:      int       = 0
        self._setup_expecting:  str       = "settlement"  # "settlement" or "road"
        self._setup_last_vertex: Optional[int] = None

        self.log: List[str] = []   # human-readable event log
        self._init_setup_order()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _init_setup_order(self) -> None:
        """
        Standard Catan setup order: 0,1,2,3,3,2,1,0 for 4 players.
        Each player places settlement then immediately a road.
        """
        n = len(self.players)
        fwd  = list(range(n))
        back = list(reversed(range(n)))
        self._setup_turn_order = fwd + back
        self._setup_index = 0
        self.current_player_index = self._setup_turn_order[0]

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    # ------------------------------------------------------------------
    # Start game (after setup is complete)
    # ------------------------------------------------------------------

    def start_game(self) -> None:
        """Call after setup phase; sets phase to ROLL_DICE."""
        self.current_player_index = 0
        self.phase = GamePhase.ROLL_DICE
        self._log(f"Game started! {self.current_player.name} goes first.")

    # ------------------------------------------------------------------
    # Setup placement
    # ------------------------------------------------------------------

    def setup_place_settlement(self, vertex_id: int) -> Dict[str, Any]:

        if self.phase not in (
            GamePhase.SETUP_SETTLEMENT_1,
            GamePhase.SETUP_SETTLEMENT_2
        ):
            return self._err("Not in setup phase.")

        # 🔥 กัน state พัง
        if self._setup_expecting != "settlement":
            return self._err("Expecting a road placement, not a settlement.")

        # 🔥 กันวางซ้ำ vertex เดิม
        if not self.board.is_vertex_free(vertex_id):
            return self._err("Vertex already occupied.")

        player = self.current_player

        try:
            self.board.place_settlement(vertex_id, player, initial_phase=True)
            player.build_settlement(vertex_id)
        except ValueError as e:
            return self._err(str(e))

        # 🔥 ต้อง set ก่อน log
        self._setup_last_vertex = vertex_id
        self._setup_expecting = "road"

        if self.phase == GamePhase.SETUP_SETTLEMENT_2:
            self._grant_setup_resources(player, vertex_id)

        msg = f"{player.name} placed a settlement at vertex {vertex_id}."
        self._log(msg)

        return {"ok": True, "message": msg}

    def setup_place_road(self, edge: Tuple[int, int]) -> Dict[str, Any]:
        """Place a free road adjacent to the last settlement during setup."""
        if self._setup_expecting != "road":
            return self._err("Expecting a settlement, not a road.")

        player = self.current_player
        # Road must be adjacent to last settlement
        v1, v2 = edge
        last   = self._setup_last_vertex
        if last not in (v1, v2):
            return self._err("Road must connect to your new settlement.")

        try:
            self.board.place_road(edge, player)
            player.build_road(edge)
        except ValueError as e:
            return self._err(str(e))

        msg = f"{player.name} placed a road on edge {edge}."
        self._log(msg)
        self._setup_expecting = "settlement"
        self._advance_setup()
        return {"ok": True, "message": msg}

    def _grant_setup_resources(self, player: Player, vertex_id: int) -> None:
        """In 2nd setup round, player receives 1 of each resource from adjacent tiles."""
        for tile in self.board.tiles:
            if vertex_id in tile.vertices and tile.resource:
                player.receive_resources({tile.resource: 1})
                self._log(f"  → {player.name} receives 1 {tile.resource}.")

    def _advance_setup(self) -> None:
        """Move to the next player in setup order, or finish setup."""
        self._setup_index += 1
        n = len(self.players)

        if self._setup_index < n:
            # Still in first round
            self.current_player_index = self._setup_turn_order[self._setup_index]
        elif self._setup_index == n:
            # Begin second round
            self.phase = GamePhase.SETUP_SETTLEMENT_2
            self.current_player_index = self._setup_turn_order[self._setup_index]
        elif self._setup_index < 2 * n:
            self.current_player_index = self._setup_turn_order[self._setup_index]
        else:
            # Setup complete
            self.start_game()

    # ------------------------------------------------------------------
    # Dice rolling
    # ------------------------------------------------------------------

    def roll_dice(self) -> Dict[str, Any]:
        """
        Roll the dice, distribute resources (or activate robber).
        :return: dict with roll total, gains per player, robber flag.
        """
        if self.phase != GamePhase.ROLL_DICE:
            return self._err(f"Cannot roll in phase {self.phase.name}.")

        total = self.dice.roll()
        self._log(f"{self.current_player.name} rolled {self.dice}.")

        result: Dict[str, Any] = {
            "ok":     True,
            "roll":   total,
            "dice":   self.dice.last_roll,
            "gains":  {},
            "robber": False,
            "message": str(self.dice),
        }

        if total == ROBBER_NUMBER:
            result["robber"] = True
            result["message"] += " — Robber activated!"
            self._apply_robber_discard()
            self.phase = GamePhase.ROBBER
            self._log("Robber activated — move it to a new tile.")
        else:
            gains = self._distribute_resources(total)
            result["gains"] = gains
            self.phase = GamePhase.ACTIONS

        return result

    def _distribute_resources(self, roll: int) -> Dict[str, Dict[str, int]]:
        """Award resources to all players with settlements/cities on matching tiles."""
        gains: Dict[str, Dict[str, int]] = {}
        for tile in self.board.get_tiles_for_roll(roll):
            if tile.has_robber or not tile.resource:
                continue
            for vid in tile.vertices:
                v = self.board.vertices[vid]
                owner = v["owner"]
                if owner is None:
                    continue
                amount = 2 if v["structure"] == "city" else 1
                owner.receive_resources({tile.resource: amount})
                gains.setdefault(owner.name, {})
                gains[owner.name][tile.resource] = (
                    gains[owner.name].get(tile.resource, 0) + amount
                )
                self._log(f"  {owner.name} receives {amount} {tile.resource}.")
        return gains

    def _apply_robber_discard(self) -> None:
        """Players with >7 cards must discard half (rounded down)."""
        for player in self.players:
            total = player.total_resources()
            if total > 7:
                discard = total // 2
                # Auto-discard: remove resources proportionally (simplified)
                removed = 0
                for r in RESOURCES:
                    while player.resources[r] > 0 and removed < discard:
                        player.resources[r] -= 1
                        removed += 1
                self._log(f"  {player.name} discarded {discard} cards.")

    # ------------------------------------------------------------------
    # Robber movement
    # ------------------------------------------------------------------

    def move_robber(self, tile_id: int) -> Dict[str, Any]:
        """Move robber to a different tile."""
        if self.phase != GamePhase.ROBBER:
            return self._err("Cannot move robber now.")
        current = self.board.robber_tile()
        if current and current.tile_id == tile_id:
            return self._err("Robber must move to a different tile.")

        self.board.move_robber(tile_id)
        self.phase = GamePhase.ACTIONS
        msg = f"{self.current_player.name} moved the robber to tile {tile_id}."
        self._log(msg)
        return {"ok": True, "message": msg}

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build_road(self, edge: Tuple[int, int]) -> Dict[str, Any]:
        """Spend resources and place a road."""
        if self.phase != GamePhase.ACTIONS:
            return self._err("Can only build during your turn (Actions phase).")
        player = self.current_player
        cost   = BUILDING_COSTS["road"]
        try:
            player.spend_resources(cost)
            self.board.place_road(edge, player)
            player.build_road(edge)
        except ValueError as e:
            return self._err(str(e))
        msg = f"{player.name} built a road on {edge}."
        self._log(msg)
        return {"ok": True, "message": msg}

    def build_settlement(self, vertex_id: int) -> Dict[str, Any]:
        """Spend resources and place a settlement."""
        if self.phase != GamePhase.ACTIONS:
            return self._err("Can only build during your turn (Actions phase).")
        player = self.current_player
        cost   = BUILDING_COSTS["settlement"]
        try:
            player.spend_resources(cost)
            self.board.place_settlement(vertex_id, player)
            player.build_settlement(vertex_id)
        except ValueError as e:
            return self._err(str(e))
        msg = f"{player.name} built a settlement at vertex {vertex_id}."
        self._log(msg)
        winner = self.check_winner()
        return {"ok": True, "message": msg, "winner": winner}

    def build_city(self, vertex_id: int) -> Dict[str, Any]:
        """Spend resources and upgrade a settlement to a city."""
        if self.phase != GamePhase.ACTIONS:
            return self._err("Can only build during your turn (Actions phase).")
        player = self.current_player
        cost   = BUILDING_COSTS["city"]
        try:
            player.spend_resources(cost)
            self.board.upgrade_to_city(vertex_id, player)
            player.upgrade_to_city(vertex_id)
        except ValueError as e:
            return self._err(str(e))
        msg = f"{player.name} upgraded to a city at vertex {vertex_id}."
        self._log(msg)
        winner = self.check_winner()
        return {"ok": True, "message": msg, "winner": winner}

    # ------------------------------------------------------------------
    # Trading (bank 4:1)
    # ------------------------------------------------------------------

    def trade_with_bank(
        self, give_resource: str, want_resource: str, ratio: int = 4
    ) -> Dict[str, Any]:
        """
        Trade `ratio` of give_resource for 1 of want_resource with the bank.
        Standard ratio is 4:1; harbours would lower this (not implemented here).
        """
        if self.phase != GamePhase.ACTIONS:
            return self._err("Can only trade during your turn.")
        player = self.current_player
        if give_resource == want_resource:
            return self._err("Cannot trade a resource for itself.")
        if player.resources.get(give_resource, 0) < ratio:
            return self._err(
                f"{player.name} needs {ratio} {give_resource} to trade (has "
                f"{player.resources.get(give_resource, 0)})."
            )
        player.resources[give_resource] -= ratio
        player.receive_resources({want_resource: 1})
        msg = f"{player.name} traded {ratio} {give_resource} → 1 {want_resource}."
        self._log(msg)
        return {"ok": True, "message": msg}

    # ------------------------------------------------------------------
    # End turn
    # ------------------------------------------------------------------

    def end_turn(self) -> Dict[str, Any]:
        """Advance to the next player's turn."""
        if self.phase not in (GamePhase.ACTIONS,):
            return self._err(
                f"Cannot end turn during phase {self.phase.name}."
            )
        self.current_player_index = (
            (self.current_player_index + 1) % len(self.players)
        )
        self.phase = GamePhase.ROLL_DICE
        msg = f"It's now {self.current_player.name}'s turn."
        self._log(msg)
        return {"ok": True, "message": msg}

    # ------------------------------------------------------------------
    # Win condition
    # ------------------------------------------------------------------

    def check_winner(self) -> Optional[Player]:
        """Return the winning player if any, else None."""
        for player in self.players:
            if player.vp >= WINNING_VP:
                self.winner = player
                self.phase  = GamePhase.GAME_OVER
                self._log(f"🏆 {player.name} wins with {player.vp} VP!")
                return player
        return None

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise engine state for save/load."""
        return {
            "players":               [p.to_dict() for p in self.players],
            "current_player_index":  self.current_player_index,
            "phase":                 self.phase.name,
            "log":                   self.log[-50:],   # keep last 50 entries
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        self.log.append(message)
        # Keep log bounded
        if len(self.log) > 200:
            self.log = self.log[-200:]

    @staticmethod
    def _err(message: str) -> Dict[str, Any]:
        return {"ok": False, "message": message}
