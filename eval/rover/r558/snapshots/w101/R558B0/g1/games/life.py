"""Conway's Game of Life: evolve H x W grid k generations.

Input text format:
  line 1: H W k
  next H lines: W chars each, '.' (dead) or '#' (alive)
Output: grid after k generations, H lines of W chars.
Cells outside the grid are always dead. Updates are simultaneous.
"""


def solve(text: str) -> str:
    lines = text.split("\n")
    first = lines[0].split()
    h, w, k = int(first[0]), int(first[1]), int(first[2])
    grid = [[1 if c == "#" else 0 for c in lines[1 + r]] for r in range(h)]

    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                n = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w:
                            n += grid[rr][cc]
                if grid[r][c]:
                    nxt[r][c] = 1 if (n == 2 or n == 3) else 0
                else:
                    nxt[r][c] = 1 if n == 3 else 0
        grid = nxt

    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
