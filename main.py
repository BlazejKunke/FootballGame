#!/usr/bin/env python3
"""
European Football - 2D Top-Down Soccer Game
Entry point for the game.

Controls:
    Arrow Keys: Move the selected player
    Space: Shoot (hold to charge power)
    S: Pass to nearest teammate
    Tab: Switch player
    R: Reset/Restart
    K: Celebrate
    Esc: Quit
"""

import sys


def main():
    """Main entry point."""
    try:
        from src.game import Game
    except ImportError as e:
        print(f"Error importing game module: {e}")
        print("\nMake sure you have installed the required dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    # Create and run game
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
