"""
helpers.py
==========
Generic utility functions used across multiple modules.
"""

import math
import random
from typing import List, Tuple


def hex_to_pixel(col: int, row: int, size: int, origin_x: int, origin_y: int) -> Tuple[float, float]:
    """
    Convert axial (col, row) board coordinates to pixel (x, y) for drawing.
    Uses a flat-top hexagonal grid with offset rows.

    :param col:      Column index within the row.
    :param row:      Row index (0 = topmost row).
    :param size:     Hex 'radius' in pixels (centre → corner).
    :param origin_x: Canvas x offset.
    :param origin_y: Canvas y offset.
    :return:         (x, y) pixel centre of the hex.
    """
    from utils.constants import BOARD_ROWS

    # Horizontal spacing between hex centres
    horiz = math.sqrt(3) * size
    # Vertical spacing
    vert  = 1.5 * size

    # How wide is this row?
    row_width = BOARD_ROWS[row]
    # Total board width in cols (widest row = 5)
    max_width = max(BOARD_ROWS)

    # Centre the row
    x_offset = (max_width - row_width) / 2.0 * horiz

    x = origin_x + x_offset + col * horiz
    y = origin_y + row * vert
    return x, y


def hex_corners(cx: float, cy: float, size: int) -> List[Tuple[float, float]]:
    """
    Return the 6 corner coordinates of a flat-top hexagon centred at (cx, cy).
    """
    corners = []
    for i in range(6):
        angle_deg = 60 * i - 30   # flat-top: start at -30°
        angle_rad = math.radians(angle_deg)
        corners.append((cx + size * math.cos(angle_rad),
                         cy + size * math.sin(angle_rad)))
    return corners


def roll_two_dice() -> Tuple[int, int]:
    """Roll two standard six-sided dice and return both values."""
    return random.randint(1, 6), random.randint(1, 6)


def resources_to_str(resources: dict) -> str:
    """Return a human-readable summary of a resource dict."""
    parts = [f"{v} {k}" for k, v in resources.items() if v > 0]
    return ", ".join(parts) if parts else "nothing"


def can_afford(player_resources: dict, cost: dict) -> bool:
    """Return True if player_resources covers every entry in cost."""
    for resource, amount in cost.items():
        if player_resources.get(resource, 0) < amount:
            return False
    return True


def subtract_resources(player_resources: dict, cost: dict) -> None:
    """Subtract cost from player_resources **in place**. Assumes can_afford() was checked."""
    for resource, amount in cost.items():
        player_resources[resource] -= amount


def add_resources(player_resources: dict, gains: dict) -> None:
    """Add gains to player_resources **in place**."""
    for resource, amount in gains.items():
        player_resources[resource] = player_resources.get(resource, 0) + amount


def validate_player_count(n: int) -> None:
    """Raise ValueError if player count is out of range."""
    if not (2 <= n <= 4):
        raise ValueError(f"Player count must be between 2 and 4, got {n}.")
