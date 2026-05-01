"""
main.py
=======
Entry point for the Settlers of Catan game.

Run:
    python main.py
"""

import sys
import os

# Ensure project root is on the Python path regardless of where the script
# is executed from.  This makes all package imports work consistently.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main() -> None:
    """Launch the game window."""
    # Initialise the SQLite history table (safe to call even if it exists)
    from data.database import init_db
    init_db()

    # Create and run the GUI (blocks until window is closed)
    from gui.main_window import MainWindow
    MainWindow()


if __name__ == "__main__":
    main()
