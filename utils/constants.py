"""
constants.py
============
Central location for all game-wide constants.
Keeping magic numbers/strings here makes it easy to tweak rules
without hunting through multiple files.
"""

# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
RESOURCES = ["wood", "brick", "sheep", "wheat", "ore"]

RESOURCE_COLORS = {
    "wood":   "#2d6a4f",   # dark green
    "brick":  "#b5451b",   # burnt orange-red
    "sheep":  "#95d5b2",   # light green
    "wheat":  "#f4a261",   # golden
    "ore":    "#6c757d",   # steel grey
    "desert": "#e9c46a",   # sandy
}

# Friendly display names
RESOURCE_EMOJI = {
    "wood":   "🌲",
    "brick":  "🧱",
    "sheep":  "🐑",
    "wheat":  "🌾",
    "ore":    "⛏️",
}

# ---------------------------------------------------------------------------
# Tile types and their resource yields
# ---------------------------------------------------------------------------
TILE_TYPES = ["forest", "hills", "pasture", "fields", "mountains", "desert"]

TILE_RESOURCE_MAP = {
    "forest":    "wood",
    "hills":     "brick",
    "pasture":   "sheep",
    "fields":    "wheat",
    "mountains": "ore",
    "desert":    None,
}

TILE_COLORS = {
    "forest":    "#2d6a4f",
    "hills":     "#b5451b",
    "pasture":   "#95d5b2",
    "fields":    "#f4a261",
    "mountains": "#6c757d",
    "desert":    "#e9c46a",
}

# Standard Catan tile distribution (19 tiles total)
TILE_DISTRIBUTION = [
    "forest", "forest", "forest", "forest",
    "hills",  "hills",  "hills",
    "pasture","pasture","pasture","pasture",
    "fields", "fields", "fields", "fields",
    "mountains","mountains","mountains",
    "desert",
]

# Standard number token distribution (excludes 7; desert gets no token)
NUMBER_TOKENS = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

# ---------------------------------------------------------------------------
# Building costs
# ---------------------------------------------------------------------------
BUILDING_COSTS = {
    "road":       {"wood": 1, "brick": 1},
    "settlement": {"wood": 1, "brick": 1, "sheep": 1, "wheat": 1},
    "city":       {"wheat": 2, "ore": 3},
    "dev_card":   {"sheep": 1, "wheat": 1, "ore": 1},
}

# Victory points awarded per structure
VICTORY_POINTS = {
    "settlement": 1,
    "city":       2,
}

# ---------------------------------------------------------------------------
# Win condition
# ---------------------------------------------------------------------------
WINNING_VP = 10

# ---------------------------------------------------------------------------
# Board geometry  (axial hex coordinates for a standard Catan board)
# ---------------------------------------------------------------------------
# The standard board has a hex-grid layout with 19 tiles.
# We use offset-row coordinates (col, row) for simplicity.
# Rows (top to bottom): 3, 4, 5, 4, 3 tiles.
BOARD_ROWS = [3, 4, 5, 4, 3]

# ---------------------------------------------------------------------------
# Robber / dice
# ---------------------------------------------------------------------------
ROBBER_NUMBER = 7

# ---------------------------------------------------------------------------
# Player colours (up to 4 players)
# ---------------------------------------------------------------------------
PLAYER_COLORS = ["#e63946", "#457b9d", "#2a9d8f", "#e9c46a"]

# ---------------------------------------------------------------------------
# Database / persistence
# ---------------------------------------------------------------------------
SAVE_FILE = "catan_save.json"
DB_FILE   = "catan_history.db"

# ---------------------------------------------------------------------------
# GUI sizing
# ---------------------------------------------------------------------------
HEX_SIZE       = 60      # pixels from centre to corner
WINDOW_WIDTH   = 1100
WINDOW_HEIGHT  = 780
CANVAS_WIDTH   = 700
CANVAS_HEIGHT  = 680
