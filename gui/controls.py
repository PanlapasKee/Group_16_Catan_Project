"""
controls.py
===========
Right-side panel containing:
  - Current player indicator
  - Resource display
  - Action buttons (Roll, Build Road, Build Settlement, Build City,
    Trade with Bank, End Turn, Save, Quit)
  - Game log
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Callable, Optional, List

from utils.constants import RESOURCES, RESOURCE_EMOJI, BUILDING_COSTS


class ControlPanel(tk.Frame):
    """
    Right-side control panel.

    Callbacks wired by main_window:
      on_roll()
      on_build_road()
      on_build_settlement()
      on_build_city()
      on_trade()
      on_end_turn()
      on_save()
      on_quit()
    """

    # Palette
    BG          = "#0d2137"
    PANEL_BG    = "#132d4a"
    TEXT_COLOR  = "#e0f0ff"
    ACCENT      = "#f4a261"
    BUTTON_BG   = "#1e4068"
    BUTTON_FG   = "#ffffff"
    BUTTON_ACTIVE_BG = "#2a5a8e"
    DANGER_BG   = "#8b1a1a"
    SUCCESS_BG  = "#1a6b3a"

    def __init__(self, parent, **callbacks) -> None:
        super().__init__(parent, bg=self.BG, width=360)
        self.pack_propagate(False)

        # Store callbacks
        self._cb = callbacks

        # ---- Title -------------------------------------------------------
        tk.Label(
            self, text="⚓ CATAN", font=("Georgia", 20, "bold"),
            bg=self.BG, fg=self.ACCENT
        ).pack(pady=(16, 4))

        # ---- Current player card -----------------------------------------
        self._player_frame = tk.Frame(self, bg=self.PANEL_BG,
                                      relief="flat", bd=0)
        self._player_frame.pack(fill="x", padx=16, pady=(4, 8))

        self._player_label = tk.Label(
            self._player_frame,
            text="Player: —",
            font=("Helvetica", 13, "bold"),
            bg=self.PANEL_BG, fg=self.TEXT_COLOR, anchor="w"
        )
        self._player_label.pack(padx=10, pady=(8, 2), fill="x")

        self._phase_label = tk.Label(
            self._player_frame,
            text="Phase: —",
            font=("Helvetica", 9),
            bg=self.PANEL_BG, fg="#8ab8d8", anchor="w"
        )
        self._phase_label.pack(padx=10, pady=(0, 4), fill="x")

        self._vp_label = tk.Label(
            self._player_frame,
            text="Victory Points: 0",
            font=("Helvetica", 10, "bold"),
            bg=self.PANEL_BG, fg=self.ACCENT, anchor="w"
        )
        self._vp_label.pack(padx=10, pady=(0, 8), fill="x")

        # ---- Resources ---------------------------------------------------
        tk.Label(
            self, text="RESOURCES", font=("Helvetica", 9, "bold"),
            bg=self.BG, fg="#6a9bbf"
        ).pack(anchor="w", padx=18, pady=(4, 0))

        self._res_frame = tk.Frame(self, bg=self.PANEL_BG)
        self._res_frame.pack(fill="x", padx=16, pady=(2, 8))

        self._res_labels: dict = {}
        for i, res in enumerate(RESOURCES):
            row_f = tk.Frame(self._res_frame, bg=self.PANEL_BG)
            row_f.pack(fill="x", padx=8, pady=1)
            emoji = RESOURCE_EMOJI.get(res, "")
            tk.Label(
                row_f, text=f"{emoji} {res.capitalize()}",
                font=("Helvetica", 10), bg=self.PANEL_BG,
                fg=self.TEXT_COLOR, width=16, anchor="w"
            ).pack(side="left")
            val = tk.Label(
                row_f, text="0",
                font=("Helvetica", 10, "bold"),
                bg=self.PANEL_BG, fg=self.ACCENT, width=3, anchor="e"
            )
            val.pack(side="right")
            self._res_labels[res] = val

        # ---- Action Buttons ----------------------------------------------
        tk.Label(
            self, text="ACTIONS", font=("Helvetica", 9, "bold"),
            bg=self.BG, fg="#6a9bbf"
        ).pack(anchor="w", padx=18, pady=(4, 0))

        btn_frame = tk.Frame(self, bg=self.BG)
        btn_frame.pack(fill="x", padx=16, pady=(2, 8))

        buttons = [
            ("🎲 Roll Dice",           "on_roll",              self.BUTTON_BG),
            ("🛣  Build Road",          "on_build_road",         self.BUTTON_BG),
            ("🏠 Build Settlement",    "on_build_settlement",   self.BUTTON_BG),
            ("🏙  Build City",          "on_build_city",         self.BUTTON_BG),
            ("🔄 Trade with Bank (4:1)","on_trade",             self.BUTTON_BG),
            ("✅ End Turn",             "on_end_turn",           self.SUCCESS_BG),
        ]
        self._action_buttons: dict = {}
        for text, cb_key, bg in buttons:
            cmd = self._cb.get(cb_key, lambda: None)
            btn = tk.Button(
                btn_frame, text=text,
                font=("Helvetica", 10), relief="flat",
                bg=bg, fg=self.BUTTON_FG,
                activebackground=self.BUTTON_ACTIVE_BG,
                activeforeground=self.BUTTON_FG,
                cursor="hand2", padx=8, pady=5,
                command=cmd,
            )
            btn.pack(fill="x", pady=2)
            self._action_buttons[cb_key] = btn

        # ---- Separator ---------------------------------------------------
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=16, pady=6)

        # ---- Save / Quit -------------------------------------------------
        util_frame = tk.Frame(self, bg=self.BG)
        util_frame.pack(fill="x", padx=16)
        for text, cb_key, bg in [
            ("💾 Save Game", "on_save",  self.BUTTON_BG),
            ("❌ Quit",       "on_quit",  self.DANGER_BG),
        ]:
            cmd = self._cb.get(cb_key, lambda: None)
            tk.Button(
                util_frame, text=text,
                font=("Helvetica", 10), relief="flat",
                bg=bg, fg=self.BUTTON_FG,
                activebackground=self.BUTTON_ACTIVE_BG,
                cursor="hand2", padx=8, pady=5,
                command=cmd,
            ).pack(side="left", fill="x", expand=True, padx=(0, 4))

        # ---- Game log ----------------------------------------------------
        tk.Label(
            self, text="GAME LOG", font=("Helvetica", 9, "bold"),
            bg=self.BG, fg="#6a9bbf"
        ).pack(anchor="w", padx=18, pady=(10, 0))

        log_frame = tk.Frame(self, bg=self.PANEL_BG)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(2, 16))

        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side="right", fill="y")

        self._log_text = tk.Text(
            log_frame, wrap="word",
            bg=self.PANEL_BG, fg="#b0ccdf",
            font=("Courier", 8), relief="flat",
            yscrollcommand=scrollbar.set,
            state="disabled",
        )
        self._log_text.pack(fill="both", expand=True)
        scrollbar.config(command=self._log_text.yview)

    # ------------------------------------------------------------------
    # Public update methods (called by main_window after engine actions)
    # ------------------------------------------------------------------

    def update_player_info(
        self,
        name: str,
        color: str,
        vp: int,
        resources: dict,
        phase: str,
    ) -> None:
        """Refresh the current player card and resource display."""
        self._player_label.config(text=f"👤 {name}", fg=color)
        self._phase_label.config(text=f"Phase: {phase.replace('_', ' ').title()}")
        self._vp_label.config(text=f"🏆 Victory Points: {vp}")

        for res in RESOURCES:
            count = resources.get(res, 0)
            self._res_labels[res].config(text=str(count))

    def append_log(self, message: str) -> None:
        """Add a line to the scrolling game log."""
        self._log_text.config(state="normal")
        self._log_text.insert("end", f"{message}\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def set_log(self, lines: List[str]) -> None:
        """Replace the entire log contents."""
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        for line in lines:
            self._log_text.insert("end", f"{line}\n")
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def set_buttons_state(self, enabled: bool) -> None:
        """Enable or disable all action buttons."""
        state = "normal" if enabled else "disabled"
        for btn in self._action_buttons.values():
            btn.config(state=state)
