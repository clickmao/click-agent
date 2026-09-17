"""Conway's Game of Life: advance the grid k generations.

Input format:
    H W k           (1 <= H,W <= 20 ; 0 <= k <= 20)
    H lines of W chars, only '.' (dead) and '#' (alive)

Rule: all cells update simultaneously on the 8-neighbourhood; anything
outside the grid is treated as dead.  A live cell survives with 2 or 3
live neighbours, otherwise it dies; a dead cell becomes alive with exactly
3 live neighbours.

Output: the grid after k generations, H lines of W chars.
"""


def _step(grid, h, w):
    """Return the grid one generation later (simultaneous update)."""
    nxt = []
    for r in range(h):
        row = grid[r]
        out = []
        for c in range(w):
            # Count live neighbours among the 8 surrounding cells.
            n = 0
            for dr in (-1, 0, 1):
                rr = r + dr
                if rr < 0 or rr >= h:
                    continue
                nrow = grid[rr]
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    cc = c + dc
                    if cc < 0 or cc >= w:
                        continue
                    if nrow[cc] == '#':
                        n += 1
            alive = row[c] == '#'
            if alive:
                out.append('#' if (n == 2 or n == 3) else '.')
            else:
                out.append('#' if n == 3 else '.')
        nxt.append(''.join(out))
    return nxt


def solve(text: str) -> str:
    lines = text.split('\n')
    # Drop a single trailing empty line produced by a final newline.
    if lines and lines[-1] == '':
        lines.pop()
    if not lines:
        return ''
    h, w, k = (int(x) for x in lines[0].split())
    grid = [list(lines[1 + i]) for i in range(h)]
    for _ in range(k):
        grid = _step(grid, h, w)
    return '\n'.join(''.join(row) for row in grid)
