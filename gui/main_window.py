"""
main_window.py
==============
Top-level Tkinter window.  Wires together:
  - Start screen (player setup)
  - BoardView  (canvas)
  - ControlPanel (sidebar)
  - GameEngine  (logic)
  - database layer (save / load / history)

Data flow
---------
User click → ControlPanel callback → GameEngine method
→ result dict → GUI refresh (board redraw + control panel update + log)
"""

from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from typing import Optional, List, Tuple

from game.game_engine import GameEngine, GamePhase
from gui.board_view   import BoardView
from gui.controls     import ControlPanel
from data             import save_game, load_game, record_game, fetch_history
from data.models      import GameRecord
from utils.constants  import WINDOW_WIDTH, WINDOW_HEIGHT, BUILDING_COSTS, RESOURCES


class MainWindow:
    """
    Application root window.

    Creates the start screen first; once players are configured it
    transitions to the main game layout.
    """

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Settlers of Catan")
        self.root.geometry("1600x900")
        self.root.resizable(True, True)
        self.root.configure(bg="#0d2137")

        self.engine:       Optional[GameEngine] = None
        self.board_view:   Optional[BoardView]  = None
        self.ctrl_panel:   Optional[ControlPanel] = None

        # Build mode state
        self._build_mode:     Optional[str] = None   # "road"|"settlement"|"city"|"robber"
        self._pending_vertex: Optional[int] = None
        self._pending_edge:   Optional[Tuple[int,int]] = None

        self._turn_count = 0

        self._show_start_screen()
        self.root.mainloop()
        self._click_locked = False

    # ==================================================================
    # Start Screen
    # ==================================================================

    def _show_start_screen(self) -> None:
        """Render the player-setup / start screen."""
        for w in self.root.winfo_children():
            w.destroy()

        frame = tk.Frame(self.root, bg="#0d2137")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            frame, text="⚓  SETTLERS OF CATAN",
            font=("Georgia", 28, "bold"),
            bg="#0d2137", fg="#f4a261"
        ).pack(pady=(0, 6))

        tk.Label(
            frame, text="A Python Board Game",
            font=("Helvetica", 11),
            bg="#0d2137", fg="#8ab8d8"
        ).pack(pady=(0, 24))

        # Player count
        tk.Label(
            frame, text="Number of players:",
            font=("Helvetica", 11),
            bg="#0d2137", fg="#e0f0ff"
        ).pack()

        self._num_players_var = tk.IntVar(value=3)
        spin = tk.Spinbox(
            frame, from_=2, to=4,
            textvariable=self._num_players_var,
            font=("Helvetica", 13), width=4,
            justify="center",
        )
        spin.pack(pady=(4, 16))

        # Player name entries
        tk.Label(
            frame, text="Player names:",
            font=("Helvetica", 11),
            bg="#0d2137", fg="#e0f0ff"
        ).pack()

        self._name_vars = []
        defaults = ["Alice", "Bob", "Carol", "Dave"]
        for i, default in enumerate(defaults):
            row = tk.Frame(frame, bg="#0d2137")
            row.pack(fill="x", pady=2)
            tk.Label(
                row, text=f"Player {i+1}:", width=10,
                font=("Helvetica", 10),
                bg="#0d2137", fg="#8ab8d8"
            ).pack(side="left")
            var = tk.StringVar(value=default)
            self._name_vars.append(var)
            tk.Entry(row, textvariable=var,
                     font=("Helvetica", 10), width=18).pack(side="left")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=16)

        # History / Load buttons
        btn_row = tk.Frame(frame, bg="#0d2137")
        btn_row.pack(pady=(0, 12))

        # Check for saved game
        saved = load_game()
        if saved:
            tk.Button(
                btn_row, text="▶ Continue Saved Game",
                font=("Helvetica", 11, "bold"),
                bg="#1a6b3a", fg="white", relief="flat",
                padx=12, pady=8, cursor="hand2",
                command=self._load_and_continue,
            ).pack(side="left", padx=6)

        tk.Button(
            btn_row, text="🆕 New Game",
            font=("Helvetica", 11, "bold"),
            bg="#f4a261", fg="#0d2137", relief="flat",
            padx=12, pady=8, cursor="hand2",
            command=self._start_new_game,
        ).pack(side="left", padx=6)

        tk.Button(
            btn_row, text="📊 History",
            font=("Helvetica", 11),
            bg="#1e4068", fg="white", relief="flat",
            padx=10, pady=8, cursor="hand2",
            command=self._show_history,
        ).pack(side="left", padx=6)

    # ==================================================================
    # Game startup helpers
    # ==================================================================

    def _start_new_game(self) -> None:
        n     = self._num_players_var.get()
        names = [self._name_vars[i].get().strip() or f"Player {i+1}"
                 for i in range(n)]
        self.engine      = GameEngine(names)
        self._turn_count = 0
        self._build_game_ui()
        self._refresh_ui()
        self._update_log()

    def _load_and_continue(self) -> None:
        """Load the JSON save file and rebuild engine state from it."""
        data = load_game()
        if not data:
            messagebox.showerror("Load Error", "No save file found.")
            return
        try:
            player_names = [p["name"] for p in data["players"]]
            self.engine  = GameEngine(player_names)
            # Restore player data
            for i, p_data in enumerate(data["players"]):
                from game.player import Player
                self.engine.players[i] = Player.from_dict(p_data, i)
            # Restore phase
            self.engine.phase = GamePhase[data.get("phase", "ROLL_DICE")]
            self.engine.current_player_index = data.get("current_player_index", 0)
            self.engine.log = data.get("log", [])
            self._build_game_ui()
            self._refresh_ui()
            self._update_log()
            self._log("Saved game loaded ✔")
        except Exception as exc:
            messagebox.showerror("Load Error", f"Could not load game:\n{exc}")

    # ==================================================================
    # Main game UI layout
    # ==================================================================

    def _build_game_ui(self) -> None:
        """Replace start screen with the main game layout."""
        for w in self.root.winfo_children():
            w.destroy()

        main_frame = tk.Frame(self.root, bg="#0d2137")
        main_frame.pack(fill="both", expand=True)

        # Board canvas (left)
        board_frame = tk.Frame(main_frame, bg="#0d2137")
        board_frame.pack(side="left", fill="both", expand=True)

        self.board_view = BoardView(
            board_frame,
            self.engine.board,
            on_vertex_click = self._on_vertex_click,
            on_tile_click   = self._on_tile_click,
        )
        self.board_view.pack(padx=10, pady=10)

        # Build-mode instruction label
        self._instruction_var = tk.StringVar(value="")
        tk.Label(
            board_frame,
            textvariable=self._instruction_var,
            font=("Helvetica", 10, "italic"),
            bg="#0d2137", fg="#f4a261"
        ).pack()

        # Control panel (right)
        self.ctrl_panel = ControlPanel(
            main_frame,
            on_roll             = self._action_roll,
            on_build_road       = self._action_build_road,
            on_build_settlement = self._action_build_settlement,
            on_build_city       = self._action_build_city,
            on_trade            = self._action_trade,
            on_end_turn         = self._action_end_turn,
            on_save             = self._action_save,
            on_quit             = self._action_quit,
        )
        self.ctrl_panel.pack(side="right", fill="y")

    # ==================================================================
    # Canvas click handlers
    # ==================================================================

    def _on_vertex_click(self, vertex_id: int) -> None:
        """Handle a click on (or near) a board vertex."""

        # ----------------------------
        # NORMAL BUILD MODE
        # ----------------------------
        if self._build_mode == "settlement":
            self._do_build_settlement(vertex_id)
            return

        elif self._build_mode == "city":
            self._do_build_city(vertex_id)
            return

        elif self._build_mode == "road":
            self._select_road_endpoint(vertex_id)
            return

        # ----------------------------
        # SETUP PHASE (🔥 FIX อยู่ตรงนี้)
        # ----------------------------
        if self.engine.phase in (
            GamePhase.SETUP_SETTLEMENT_1,
            GamePhase.SETUP_SETTLEMENT_2
        ):
            # 🔥 เช็คว่า engine กำลังรออะไร
            if self.engine._setup_expecting == "settlement":
                result = self.engine.setup_place_settlement(vertex_id)
                self._handle_result(result)

            elif self.engine._setup_expecting == "road":
                # ใช้ระบบเลือก 2 จุดเหมือน build road ปกติ
                self._select_road_endpoint(vertex_id)

        return
    
    def _on_tile_click(self, tile_id: int) -> None:
        """Handle a click on a board tile (used for robber)."""
        if self._build_mode == "robber" or self.engine.phase == GamePhase.ROBBER:
            result = self.engine.move_robber(tile_id)
            self._build_mode = None
            self._instruction_var.set("")
            self._handle_result(result)

        # Setup road: click two vertices (handled via vertex clicks above)

    # ------------------------------------------------------------------
    # Road placement: two vertex clicks define an edge
    # ------------------------------------------------------------------

    def _select_road_endpoint(self, vertex_id: int) -> None:
        if self._pending_vertex is None:
            self._pending_vertex = vertex_id
            self.board_view.highlight_vertex(vertex_id)
            self._instruction_var.set(
                f"Road start: vertex {vertex_id}. Click second vertex."
            )
        else:
            v1 = self._pending_vertex
            v2 = vertex_id
            edge = (min(v1, v2), max(v1, v2))
            self._pending_vertex = None
            self.board_view.clear_highlights()
            self._instruction_var.set("")

            phase = self.engine.phase
            if phase in (GamePhase.SETUP_SETTLEMENT_1,
                          GamePhase.SETUP_SETTLEMENT_2):
                result = self.engine.setup_place_road(edge)
            else:
                result = self.engine.build_road(edge)
            self._build_mode = None
            self._handle_result(result)
        if v1 == v2:
            return

    # ==================================================================
    # Action callbacks (wired to ControlPanel buttons)
    # ==================================================================

    def _action_roll(self) -> None:
        result = self.engine.roll_dice()
        if result["ok"] and result.get("robber"):
            self._build_mode = "robber"
            self._instruction_var.set("⚠ Roll = 7! Click a tile to move the robber.")
        self._handle_result(result)

    def _action_build_road(self) -> None:
        if not self.engine.current_player.can_afford(BUILDING_COSTS["road"]):
            messagebox.showinfo("Cannot Build", "Not enough resources for a road.")
            return
        self._build_mode = "road"
        self._pending_vertex = None
        self._instruction_var.set("🛣  Click the first vertex of your road.")

    def _action_build_settlement(self) -> None:
        if not self.engine.current_player.can_afford(BUILDING_COSTS["settlement"]):
            messagebox.showinfo("Cannot Build", "Not enough resources for a settlement.")
            return
        self._build_mode = "settlement"
        self._instruction_var.set("🏠 Click a vertex to place your settlement.")

    def _do_build_settlement(self, vertex_id: int) -> None:
        result = self.engine.build_settlement(vertex_id)
        self._build_mode = None
        self._instruction_var.set("")
        self._handle_result(result)
        if result.get("winner"):
            self._handle_winner(result["winner"])

    def _action_build_city(self) -> None:
        if not self.engine.current_player.can_afford(BUILDING_COSTS["city"]):
            messagebox.showinfo("Cannot Build", "Not enough resources for a city.")
            return
        self._build_mode = "city"
        self._instruction_var.set("🏙  Click one of your settlements to upgrade.")

    def _do_build_city(self, vertex_id: int) -> None:
        result = self.engine.build_city(vertex_id)
        self._build_mode = None
        self._instruction_var.set("")
        self._handle_result(result)
        if result.get("winner"):
            self._handle_winner(result["winner"])

    def _action_trade(self) -> None:
        """Prompt user for trade resource and desired resource."""
        player = self.engine.current_player
        give = simpledialog.askstring(
            "Trade with Bank",
            f"Give 4 of which resource?\n{RESOURCES}\n\nYour resources: {player.resources}",
            parent=self.root,
        )
        if not give:
            return
        give = give.strip().lower()
        if give not in RESOURCES:
            messagebox.showerror("Trade Error", f"'{give}' is not a valid resource.")
            return

        want = simpledialog.askstring(
            "Trade with Bank",
            f"Receive 1 of which resource? (not {give})",
            parent=self.root,
        )
        if not want:
            return
        want = want.strip().lower()
        if want not in RESOURCES:
            messagebox.showerror("Trade Error", f"'{want}' is not a valid resource.")
            return

        result = self.engine.trade_with_bank(give, want)
        self._handle_result(result)

    def _action_end_turn(self) -> None:
        result = self.engine.end_turn()
        self._build_mode    = None
        self._pending_vertex = None
        self._instruction_var.set("")
        self._turn_count   += 1
        self._handle_result(result)

    def _action_save(self) -> None:
        ok = save_game(self.engine.to_dict())
        if ok:
            messagebox.showinfo("Saved", "Game saved successfully!")
        else:
            messagebox.showerror("Save Error", "Could not save the game.")

    def _action_quit(self) -> None:
        if messagebox.askyesno("Quit", "Save before quitting?"):
            save_game(self.engine.to_dict())
        self.root.destroy()

    # ==================================================================
    # Result handling
    # ==================================================================

    def _handle_result(self, result: dict) -> None:
        """Called after every engine action; refreshes the UI."""
        msg = result.get("message", "")
        if msg:
            self._log(msg)

        if not result.get("ok"):
            messagebox.showwarning("Action Failed", msg)

        self._refresh_ui()
        self._update_log()

    def _handle_winner(self, winner) -> None:
        """Show winner dialog and record the game."""
        self.engine.phase = GamePhase.GAME_OVER
        self.ctrl_panel.set_buttons_state(False)

        record = GameRecord.create_new(
            self.engine.players,
            winner.name,
            self._turn_count,
            self.engine.log,
        )
        record_game(record)

        messagebox.showinfo(
            "🏆 We Have a Winner!",
            f"Congratulations {winner.name}!\n"
            f"You reached {winner.vp} Victory Points and won the game!\n\n"
            f"Turns played: {self._turn_count}",
        )
        # Return to start screen
        self._show_start_screen()

    # ==================================================================
    # UI refresh helpers
    # ==================================================================

    def _refresh_ui(self) -> None:
        """Redraw board and update control panel to reflect current state."""
        if self.board_view:
            self.board_view.draw_board()

        if self.ctrl_panel and self.engine:
            p = self.engine.current_player
            self.ctrl_panel.update_player_info(
                name      = p.name,
                color     = p.color,
                vp        = p.vp,
                resources = p.resources,
                phase     = self.engine.phase.name,
            )

    def _update_log(self) -> None:
        if self.ctrl_panel and self.engine:
            self.ctrl_panel.set_log(self.engine.log[-60:])

    def _log(self, msg: str) -> None:
        if self.engine:
            self.engine._log(msg)
        if self.ctrl_panel:
            self.ctrl_panel.append_log(msg)

    # ==================================================================
    # History screen
    # ==================================================================

    def _show_history(self) -> None:
        records = fetch_history(20)
        win = tk.Toplevel(self.root)
        win.title("Game History")
        win.geometry("500x380")
        win.configure(bg="#0d2137")

        tk.Label(
            win, text="📊 Past Games",
            font=("Georgia", 14, "bold"),
            bg="#0d2137", fg="#f4a261"
        ).pack(pady=(12, 6))

        if not records:
            tk.Label(
                win, text="No games recorded yet.",
                font=("Helvetica", 11),
                bg="#0d2137", fg="#8ab8d8"
            ).pack(pady=20)
            return

        cols = ("Date", "Winner", "Turns", "Players")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=12)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=110, anchor="center")
        tree.pack(fill="both", expand=True, padx=16, pady=8)

        for rec in records:
            players_str = ", ".join(p.name for p in rec.players)
            tree.insert("", "end", values=(
                rec.timestamp[:16],
                rec.winner,
                rec.turn_count,
                players_str,
            ))
