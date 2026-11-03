"""
main.py - application entry point.

Author : KABWE KENNEDY

Run from the project root with the virtual environment active:
    python python/main.py
"""

from gui import App
from visualiser import attach


def main() -> None:
    app = App()
    attach(app)             # connect the phasor and flux tabs
    app.mainloop()


if __name__ == "__main__":
    main()