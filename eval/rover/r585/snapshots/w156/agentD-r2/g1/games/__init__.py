"""games: multi-file game package (Conway Life, subtraction game, Nim, Wythoff).

Each game module exposes a pure function solve(text: str) -> str that takes the
complete stdin text and returns the exact stdout text (no trailing newline).
The CLI entry point is games.__main__, invoked as `python3 -m games <game_id>`.
"""
