"""
board_view.py
=============
Renders the Catan board on a Tkinter Canvas.

Responsibilities
----------------
- Draw all 19 hex tiles with terrain colour.
- Overlay number tokens.
- Draw roads (lines), settlements (squares), cities (diamonds).
- Highlight the tile holding the robber.
- Handle click events and translate pixel → vertex/tile IDs.
- Expose callbacks for the controls layer:
    on_vertex_click(vertex_id)
    on_tile_click(tile_id)
    on_edge_click(edge)
"""

from __future__ import annotations
import math
import tkinter as tk
from typing import Callable, Dict, List, Optional, Tuple

from game.board  import Board, Tile
from game.player import Player
from utils.helpers import hex_corners
from utils.constants import TILE_COLORS, HEX_SIZE, CANVAS_WIDTH, CANVAS_HEIGHT


class BoardView(tk.Canvas):
    """
    Tkinter Canvas subclass that draws and redraws the board.

    Parameters
    ----------
    parent          : tk widget
    board           : Board   The live board object (read-only).
    on_vertex_click : callable(vertex_id)
    on_tile_click   : callable(tile_id)
    """

    VERTEX_RADIUS = 10
    ROAD_WIDTH    = 5

    def __init__(
        self,
        parent,
        board: Board,
        on_vertex_click: Optional[Callable[[int], None]] = None,
        on_tile_click:   Optional[Callable[[int], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg="#1a6b8a",   # ocean blue background
            highlightthickness=0,
            **kwargs,
        )
        self.board            = board
        self._on_vertex_click = on_vertex_click
        self._on_tile_click   = on_tile_click

        # Pre-compute vertex pixel positions
        self._vertex_pixels: Dict[int, Tuple[float, float]] = {}
        for vid, vdata in board.vertices.items():
            px, py = vdata["pixel"]
            self._vertex_pixels[vid] = (float(px), float(py))

        self.bind("<Button-1>", self._handle_click)
        self.draw_board()

    # ------------------------------------------------------------------
    # Main draw
    # ------------------------------------------------------------------

    def draw_board(self) -> None:
        """Full redraw of the board."""
        self.delete("all")
        self._draw_tiles()
        self._draw_roads()
        self._draw_settlements()

    # ------------------------------------------------------------------
    # Tile drawing
    # ------------------------------------------------------------------

    def _draw_tiles(self) -> None:
        for tile in self.board.tiles:
            self._draw_tile(tile)

    def _draw_tile(self, tile: Tile) -> None:
        cx, cy = tile.pixel_x, tile.pixel_y
        corners = hex_corners(cx, cy, HEX_SIZE)
        flat    = [coord for pt in corners for coord in pt]

        # Fill colour
        fill = tile.color
        if tile.has_robber:
            fill = "#222222"   # dark overlay for robber

        outline = "#0d3b5e"  # dark navy border

        self.create_polygon(flat, fill=fill, outline=outline, width=2,
                             tags=("tile", f"tile_{tile.tile_id}"))

        # Tile type label (small)
        self.create_text(cx, cy - 18, text=tile.tile_type.capitalize(),
                         font=("Helvetica", 7), fill="white",
                         tags="tile_label")

        # Number token circle
        if tile.number is not None:
            token_color = "#cc0000" if tile.number in (6, 8) else "#f5f0e0"
            self.create_oval(cx - 16, cy - 4, cx + 16, cy + 28,
                             fill=token_color, outline="#888",
                             tags="token")
            self.create_text(cx, cy + 12, text=str(tile.number),
                             font=("Helvetica", 12, "bold"),
                             fill="black" if tile.number not in (6, 8) else "white",
                             tags="token_text")

        # Robber marker
        if tile.has_robber:
            self.create_text(cx, cy + 14, text="🦹", font=("Helvetica", 18),
                             tags="robber")

    # ------------------------------------------------------------------
    # Roads
    # ------------------------------------------------------------------

    def _draw_roads(self) -> None:
        for edge, edata in self.board.edges.items():
            owner: Optional[Player] = edata["owner"]
            if owner is None:
                continue
            v1, v2 = edge
            x1, y1 = self._vertex_pixels[v1]
            x2, y2 = self._vertex_pixels[v2]
            self.create_line(x1, y1, x2, y2,
                             fill=owner.color, width=self.ROAD_WIDTH,
                             capstyle=tk.ROUND, tags="road")

    # ------------------------------------------------------------------
    # Settlements & cities
    # ------------------------------------------------------------------

    def _draw_settlements(self) -> None:
        for vid, vdata in self.board.vertices.items():
            owner     = vdata["owner"]
            structure = vdata["structure"]
            if owner is None:
                continue
            px, py = self._vertex_pixels[vid]
            if structure == "settlement":
                self._draw_settlement_icon(px, py, owner.color)
            elif structure == "city":
                self._draw_city_icon(px, py, owner.color)

    def _draw_settlement_icon(self, x: float, y: float, color: str) -> None:
        r = self.VERTEX_RADIUS
        self.create_rectangle(x - r, y - r, x + r, y + r,
                              fill=color, outline="white", width=2,
                              tags="settlement")

    def _draw_city_icon(self, x: float, y: float, color: str) -> None:
        r = self.VERTEX_RADIUS + 4
        # Diamond shape
        pts = [x, y - r, x + r, y, x, y + r, x - r, y]
        self.create_polygon(pts, fill=color, outline="white", width=2,
                            tags="city")

    # ------------------------------------------------------------------
    # Click handling
    # ------------------------------------------------------------------

    def _handle_click(self, event: tk.Event) -> None:
        cx, cy = event.x, event.y

        # Check vertex proximity first
        best_vid  = None
        best_dist = float("inf")
        for vid, (vx, vy) in self._vertex_pixels.items():
            dist = math.hypot(cx - vx, cy - vy)
            if dist < best_dist:
                best_dist = dist
                best_vid  = vid

        if best_dist <= self.VERTEX_RADIUS * 2.5 and self._on_vertex_click:
            self._on_vertex_click(best_vid)
            return

        # Check tile proximity
        best_tid  = None
        best_dist = float("inf")
        for tile in self.board.tiles:
            dist = math.hypot(cx - tile.pixel_x, cy - tile.pixel_y)
            if dist < best_dist:
                best_dist = dist
                best_tid  = tile.tile_id

        if best_dist <= HEX_SIZE and self._on_tile_click:
            self._on_tile_click(best_tid)

    # ------------------------------------------------------------------
    # Helpers for controls layer
    # ------------------------------------------------------------------

    def highlight_vertex(self, vertex_id: int, color: str = "yellow") -> None:
        """Draw a temporary highlight circle around a vertex."""
        px, py = self._vertex_pixels[vertex_id]
        r = self.VERTEX_RADIUS + 5
        self.create_oval(px - r, py - r, px + r, py + r,
                         outline=color, width=3, tags="highlight")

    def clear_highlights(self) -> None:
        self.delete("highlight")
