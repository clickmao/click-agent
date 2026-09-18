"""Multi-file game package.

Each game module exports a pure function ``solve(text: str) -> str`` that maps
the complete stdin text to the exact stdout text (no trailing newline).
"""

__all__ = ["life", "sub", "nim", "wythoff"]
