"""Multi-file game package: life / sub / nim / wythoff.

Each game module exports ``solve(text: str) -> str`` -- a pure function that
takes the complete stdin text of one test case and returns the exact stdout
text (without a trailing newline).

Entry point: ``python3 -m games <game_id>``
"""
