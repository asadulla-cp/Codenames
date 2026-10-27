#!/usr/bin/env python3
"""
Codenames — terminal game
Run:  python3 main.py
"""

import sys
import os

# Ensure the codenames directory is on the path
sys.path.insert(0, os.path.dirname(__file__))

from game import Game


def main():
    try:
        g = Game()
        g.run()
    except KeyboardInterrupt:
        print("\n\n  Game interrupted. Goodbye!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
