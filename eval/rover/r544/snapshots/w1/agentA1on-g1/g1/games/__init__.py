"""Multi-game Python package.

Each game module exposes a pure function:

    solve(text: str) -> str

where ``text`` is the complete stdin payload for that game and the return
value is the exact stdout payload (no trailing newline).

Run a game with::

    python3 -m games <game_id>

with ``<game_id>`` one of ``life`` / ``sub`` / ``nim`` / ``wythoff``.
"""

__all__ = ["life", "sub", "nim", "wythoff"]
