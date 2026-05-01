# ⚓ Settlers of Catan – Python Edition

A fully playable, modular Python implementation of the classic board game
**Settlers of Catan**, built with Tkinter and SQLite.

---

## 📋 Table of Contents

1. [Project Description](#project-description)
2. [Features](#features)
3. [Project Structure](#project-structure)
4. [Installation](#installation)
5. [How to Run](#how-to-run)
6. [Gameplay Guide](#gameplay-guide)
7. [Architecture Overview](#architecture-overview)
8. [Data Flow](#data-flow)
9. [Save & Load](#save--load)

---

## Project Description

This project replicates the core gameplay loop of Settlers of Catan:

- Randomised 19-hex board generated fresh each game
- Dice rolling with resource distribution
- Settlement, city, and road placement
- 4:1 bank trading
- Robber mechanics (activated on a roll of 7)
- 10-Victory-Point win condition
- Save / Load via JSON
- Game history recorded in SQLite

The project is written in pure Python (no third-party runtime dependencies)
using an object-oriented, modular architecture.

---

## Features

| Feature | Details |
|---|---|
| Board | 19 randomised hex tiles, 54 vertices, standard number tokens |
| Resources | Wood, Brick, Sheep, Wheat, Ore |
| Buildings | Roads, Settlements, Cities |
| Trading | Bank 4:1 trade |
| Robber | Auto-activates on roll of 7; player moves it |
| Persistence | JSON quick-save + SQLite history |
| GUI | Tkinter canvas with clickable board, sidebar controls, game log |
| Players | 2–4 players, configurable names |

---

## Project Structure

```
catan_game/
│
├── main.py                 Entry point
├── requirements.txt        Dependencies (stdlib only)
├── README.md
│
├── game/
│   ├── __init__.py
│   ├── board.py            Board, Tile classes; hex graph
│   ├── player.py           Player class; resource tracking
│   ├── game_engine.py      Turn logic, rules, win detection
│   └── dice.py             Dice rolling
│
├── gui/
│   ├── __init__.py
│   ├── main_window.py      Root window; screen routing
│   ├── board_view.py       Canvas hex renderer
│   └── controls.py         Sidebar panel; buttons; log
│
├── data/
│   ├── __init__.py
│   ├── database.py         JSON save/load; SQLite history
│   └── models.py           GameRecord, PlayerRecord dataclasses
│
├── utils/
│   ├── __init__.py
│   ├── constants.py        All game constants
│   └── helpers.py          Shared utility functions
│
└── assets/
    ├── images/             (placeholder – extend for custom graphics)
    └── sounds/             (placeholder – extend for sound effects)
```

---

## Installation

### Prerequisites

- Python 3.9 or higher
- `tkinter` (bundled with Python on Windows/macOS; on Linux: `sudo apt install python3-tk`)

### Step-by-step

```bash
# 1. Clone or download the project
git clone <repo-url>
cd catan_game

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 4. Install requirements (none required beyond stdlib, but good practice)
pip install -r requirements.txt

# 5. Run the game
python main.py
```

---

## How to Run

```bash
python main.py
```

That's it. A GUI window opens immediately.

---

## Gameplay Guide

### Start Screen

1. Select the number of players (2–4).
2. Enter player names.
3. Click **New Game** (or **Continue Saved Game** if a save exists).

### Setup Phase

Each player places **two settlements** and **two roads** in turn order
(first round forward, second round in reverse — standard Catan rules).

- Click a **vertex** (corner) on the board to place a settlement.
- Click two **vertices** connected by an edge to place a road.

The second settlement grants starting resources from adjacent tiles.

### Main Turn

1. **Roll Dice** – distributes resources to all players with adjacent structures.
2. If you rolled **7** – the robber activates; click any tile to move it.
3. **Build / Trade** (any order, any number of times):
   - 🛣 Build Road (1 Wood + 1 Brick) → click two adjacent vertices
   - 🏠 Build Settlement (1 Wood + 1 Brick + 1 Sheep + 1 Wheat) → click vertex
   - 🏙 Build City (2 Wheat + 3 Ore) → click one of your settlements
   - 🔄 Trade with Bank (4 of one resource → 1 of any other)
4. Click **End Turn**.

### Winning

The first player to reach **10 Victory Points** wins:
- Settlement = 1 VP
- City = 2 VP

---

## Architecture Overview

### `game/game_engine.py` — GameEngine

The central state machine.  All game rules live here.
Uses a `GamePhase` enum to enforce legal actions per phase.

### `game/board.py` — Board & Tile

Board constructs the 19-tile hex graph, assigns pixel coordinates,
and shares vertices/edges between adjacent tiles.

### `game/player.py` — Player

Owns resources, structure lists, and VP calculation.

### `gui/main_window.py` — MainWindow

Manages screen transitions (start → game → game over).
Wires engine callbacks to GUI events.

### `data/database.py` — Persistence

- `save_game()` / `load_game()` → JSON file
- `record_game()` / `fetch_history()` → SQLite

---

## Data Flow

```
User clicks board/button
        │
        ▼
  MainWindow / BoardView  (gui layer)
        │
        ▼
  GameEngine method       (game layer)
        │  returns result dict {ok, message, ...}
        ▼
  Board / Player mutated  (game layer)
        │
        ├─► save_game() if requested  (data layer)
        │
        ▼
  _refresh_ui()           (gui layer)
        │
        ├─► BoardView.draw_board()
        └─► ControlPanel.update_player_info()
```

---

## Save & Load

- **Save**: click 💾 Save Game at any time → writes `catan_save.json` next to `main.py`.
- **Load**: restart the game; **Continue Saved Game** button appears automatically.
- **History**: every finished game is appended to `catan_history.db` (SQLite).
  View past games from the start screen → 📊 History.
