"""Conway's Game of Life.

stdin: first line "H W k" (1<=H,W<=20, 0<=k<=20), then H lines of W chars from {'.', '#'}.
Output: grid after k generations, H lines of W chars, no trailing newline.
"""


def solve(text: str) -> str:
    lines = text.splitlines()
    h, w, k = (int(v) for v in lines[0].split())
    grid = [[1 if ch == '#' else 0 for ch in lines[1 + i]] for i in range(h)]
    for _ in range(k):
        nxt = [[0] * w for _ in range(h)]
        for r in range(h):
            for c in range(w):
                nb = 0
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        if dr == 0 and dc == 0:
                            continue
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < h and 0 <= cc < w and grid[rr][cc]:
                            nb += 1
                if grid[r][c]:
                    nxt[r][c] = 1 if nb in (2, 3) else 0
                else:
                    nxt[r][c] = 1 if nb == 3 else 0
        grid = nxt
    return "\n".join("".join('#' if v else '.' for v in row) for row in grid)
