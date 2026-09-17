"""games: a small multi-file game package (standard library only).

Modules:
    life     - Conway's Game of Life, k generations
    sub      - subtraction game, win/lose and minimal winning take
    nim      - multi-pile Nim, minimal-index winning move
    wythoff  - Wythoff's game, lexicographically smallest winning move

Every game module exposes a pure function::

    solve(text: str) -> str

where *text* is the complete stdin text for that game and the return value is
the complete stdout text (no trailing newline).
"""

__all__ = ["life", "sub", "nim", "wythoff"]
