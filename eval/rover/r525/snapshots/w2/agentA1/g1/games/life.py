"""Conway's Game of Life: evolve the grid k generations and return it as text.

solve(text) is pure: text is the complete stdin, the return value is the
complete stdout (no trailing newline).
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    if not lines:
        return ""

    h, w, k = (int(x) for x in lines[0].split())

    # Parse the initial grid; tolerate short rows by treating missing cells dead.
    grid = [[False] * w for _ in range(h)]
    for r in range(h):
        row = lines[r + 1] if r + 1 < len(lines) else ""
        for c in range(w):
            grid[r][c] = c < len(row) and row[c] == "#"

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
                # Simultaneous update: outside the grid counts as dead.
                nxt[r][c] = (grid[r][c] and n in (2, 3)) or ((not grid[r][c]) and n == 3)
        grid = nxt

    return "\n".join("".join("#" if cell else "." for cell in row) for row in grid)
