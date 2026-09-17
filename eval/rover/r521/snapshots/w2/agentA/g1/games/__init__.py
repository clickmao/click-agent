"""games: a pure-stdlib multi-game package.

Each game module exports ``solve(text: str) -> str``:
  * text  = the complete stdin payload for that game
  * return= the complete stdout payload (no trailing newline)

Run:  python3 -m games <game_id>   # life | sub | nim | wythoff
"""

GAME_IDS = ("life", "sub", "nim", "wythoff")

__all__ = ["GAME_IDS"]
