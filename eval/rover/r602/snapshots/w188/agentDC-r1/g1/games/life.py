"""Conway's Game of Life: H x W grid, k generations.

stdin format:
  first line: H W k
  next H lines: W chars each, '.' (dead) or '#' (alive)
Rules: 8-neighbourhood, simultaneous update, outside = dead.
  alive with 2 or 3 neighbours survives, else dies
  dead with exactly 3 neighbours becomes alive
Output: grid after k generations, H lines of W chars.
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = []
    for r in range(h):
        row = lines[1 + r] if 1 + r < len(lines) else ""
        row = row.ljust(w, ".")[:w]
        grid.append([c == "#" for c in row])

    for _ in range(k):
        nxt = [[False] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            n += 1
                if grid[r][c]:
                    nxt[r][c] = n == 2 or n == 3
                else:
                    nxt[r][c] = n == 3
        grid = nxt

    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
