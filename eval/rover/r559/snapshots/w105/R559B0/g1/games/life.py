"""Conway's Game of Life: evolve k generations."""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = map(int, lines[0].split())
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + r].strip()] for r in range(h)]
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
                    nxt[r][c] = 1 if n in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if n == 3 else 0
        grid = nxt
    return "\n".join("".join('#' if v else '.' for v in row) for row in grid)
