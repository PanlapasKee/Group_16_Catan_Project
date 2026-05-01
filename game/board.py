"""
board.py
========
Defines the Board and Tile classes (FIXED VERSION).

Fixes:
- Prevent adjacent settlement placement (distance rule)
- Add road connection validation
- Improve vertex precision handling
"""

from __future__ import annotations
import random
from typing import Dict, List, Optional, Tuple, Set

from utils.constants import (
    BOARD_ROWS, TILE_DISTRIBUTION, NUMBER_TOKENS,
    TILE_RESOURCE_MAP, TILE_COLORS,
)
from utils.helpers import hex_to_pixel, hex_corners


# ---------------------------------------------------------------------------
# Tile
# ---------------------------------------------------------------------------

class Tile:
    def __init__(
        self,
        tile_id:   int,
        tile_type: str,
        resource:  Optional[str],
        number:    Optional[int],
        col:       int,
        row:       int,
    ) -> None:
        self.tile_id    = tile_id
        self.tile_type  = tile_type
        self.resource   = resource
        self.number     = number
        self.col        = col
        self.row        = row

        self.vertices: List[int] = []
        self.edges: List[Tuple[int, int]] = []

        self.pixel_x = 0.0
        self.pixel_y = 0.0

        self.has_robber = (tile_type == "desert")

    @property
    def color(self) -> str:
        return TILE_COLORS.get(self.tile_type, "#cccccc")

    def __repr__(self) -> str:
        return f"Tile(id={self.tile_id}, type={self.tile_type}, number={self.number})"


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------

class Board:

    HEX_SIZE = 60
    ORIGIN_X = 60
    ORIGIN_Y = 50

    def __init__(self) -> None:
        self.tiles: List[Tile] = []
        self.vertices: Dict[int, dict] = {}
        self.edges: Dict[Tuple[int, int], dict] = {}
        self.number_to_tiles: Dict[int, List[Tile]] = {}

        self._build_board()

    # ------------------------------------------------------------------
    # BUILD
    # ------------------------------------------------------------------

    def _build_board(self) -> None:
        tile_types = TILE_DISTRIBUTION[:]
        random.shuffle(tile_types)

        numbers = NUMBER_TOKENS[:]
        random.shuffle(numbers)

        tile_id = 0
        for row_idx, n_cols in enumerate(BOARD_ROWS):
            for col_idx in range(n_cols):

                ttype = tile_types[tile_id]
                resource = TILE_RESOURCE_MAP[ttype]

                number = None if ttype == "desert" else numbers.pop()

                tile = Tile(tile_id, ttype, resource, number, col_idx, row_idx)

                px, py = hex_to_pixel(
                    col_idx, row_idx,
                    self.HEX_SIZE, self.ORIGIN_X, self.ORIGIN_Y
                )
                tile.pixel_x = px
                tile.pixel_y = py

                self.tiles.append(tile)
                tile_id += 1

        self._build_vertex_graph()
        self._index_numbers()

    # ------------------------------------------------------------------

    def _build_vertex_graph(self) -> None:
        pos_to_id: Dict[Tuple[float, float], int] = {}
        next_vid = 0

        for tile in self.tiles:
            corners = hex_corners(tile.pixel_x, tile.pixel_y, self.HEX_SIZE)

            vertex_ids = []
            for cx, cy in corners:
                # 🔥 FIX: better precision
                key = (round(cx, 2), round(cy, 2))

                if key not in pos_to_id:
                    pos_to_id[key] = next_vid
                    self.vertices[next_vid] = {
                        "owner": None,
                        "structure": None,
                        "pixel": key,
                    }
                    next_vid += 1

                vertex_ids.append(pos_to_id[key])

            tile.vertices = vertex_ids

            # edges
            for i in range(6):
                v1 = vertex_ids[i]
                v2 = vertex_ids[(i + 1) % 6]

                edge = (min(v1, v2), max(v1, v2))

                if edge not in self.edges:
                    self.edges[edge] = {"owner": None}

                tile.edges.append(edge)

    # ------------------------------------------------------------------

    def _index_numbers(self) -> None:
        for tile in self.tiles:
            if tile.number is not None:
                self.number_to_tiles.setdefault(tile.number, []).append(tile)

    # ------------------------------------------------------------------
    # 🔥 NEW LOGIC
    # ------------------------------------------------------------------

    def _get_adjacent_vertices(self, vertex_id: int) -> Set[int]:
        adjacent = set()
        for (v1, v2) in self.edges:
            if v1 == vertex_id:
                adjacent.add(v2)
            elif v2 == vertex_id:
                adjacent.add(v1)
        return adjacent

    def _has_adjacent_road(self, vertex_id: int, player) -> bool:
        for (v1, v2), edge_data in self.edges.items():
            if vertex_id in (v1, v2) and edge_data["owner"] is player:
                return True
        return False

    # ------------------------------------------------------------------

    def is_vertex_free(self, vertex_id: int) -> bool:
        # occupied
        if self.vertices[vertex_id]["owner"] is not None:
            return False

        # 🔥 distance rule
        for adj in self._get_adjacent_vertices(vertex_id):
            if self.vertices[adj]["owner"] is not None:
                return False

        return True

    def is_edge_free(self, edge: Tuple[int, int]) -> bool:
        edge = (min(edge), max(edge))
        return self.edges.get(edge, {}).get("owner") is None

    # ------------------------------------------------------------------

    def place_settlement(
        self,
        vertex_id: int,
        player,
        initial_phase: bool = False
    ) -> None:

        if not self.is_vertex_free(vertex_id):
            raise ValueError(f"Invalid settlement placement at {vertex_id}")

        # 🔥 road rule
        if not initial_phase and not self._has_adjacent_road(vertex_id, player):
            raise ValueError("Settlement must connect to your road")

        self.vertices[vertex_id]["owner"] = player
        self.vertices[vertex_id]["structure"] = "settlement"

    def upgrade_to_city(self, vertex_id: int, player) -> None:
        v = self.vertices[vertex_id]

        if v["owner"] is not player or v["structure"] != "settlement":
            raise ValueError("Cannot upgrade to city")

        v["structure"] = "city"

    def place_road(self, edge: Tuple[int, int], player) -> None:
        edge = (min(edge), max(edge))

        if not self.is_edge_free(edge):
            raise ValueError("Road already exists")

        self.edges[edge]["owner"] = player

    # ------------------------------------------------------------------

    def get_tiles_for_roll(self, roll: int) -> List[Tile]:
        return self.number_to_tiles.get(roll, [])

    def get_vertices_for_player(self, player) -> List[int]:
        return [vid for vid, v in self.vertices.items() if v["owner"] is player]

    def move_robber(self, new_tile_id: int) -> None:
        for tile in self.tiles:
            tile.has_robber = (tile.tile_id == new_tile_id)

    def robber_tile(self) -> Optional[Tile]:
        for tile in self.tiles:
            if tile.has_robber:
                return tile
        return None

    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Board(vertices={len(self.vertices)}, edges={len(self.edges)})"