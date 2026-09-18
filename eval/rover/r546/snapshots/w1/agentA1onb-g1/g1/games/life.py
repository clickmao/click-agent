"""Game ``life``: Conway's Game of Life, H-step evolution.

stdin:
    line 1:         H W k        (1<=H,W<=20 ; 0<=k<=20)
    next H lines:   W chars each, '.' = dead, '#' = alive
stdout:
    grid after k generations (k=0 -> initial), H lines of W chars, no trailing NL.

Rules: synchronous 8-neighbour update; outside the grid counts as dead.
  alive with 2 or 3 neighbours survives, otherwise dies;
  dead with exactly 3 neighbours becomes alive.
"""

from __future__ import annotations


def _step(grid: list[str], h: int, w: int) -> list[str]:
    """Advance the grid by one generation (synchronous update)."""
    out: list[str] = []
    for r in range(h):
        row_chars: list[str] = []
        for c in range(w):
            n = 0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and grid[rr][cc] == '#':
                        n += 1
            alive = grid[r][c] == '#'
            if alive:
                row_chars.append('#' if n in (2, 3) else '.')
            else:
                row_chars.append('#' if n == 3 else '.')
        out.append(''.join(row_chars))
    return out


def solve(text: str) -> str:
    lines = text.split('\n')
    h, w, k = (int(x) for x in lines[0].split())
    grid = [lines[i + 1].strip() for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(grid)
