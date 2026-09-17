"""Multi-file game package (Conway's Life, subtraction game, Nim, Wythoff).

Each game module exposes a pure function ``solve(text: str) -> str`` where
``text`` is the complete stdin payload and the return value is the exact
stdout payload (no trailing newline).  The CLI entry point lives in
``games/__main__.py`` and is invoked as ``python3 -m games <game_id>``.
"""
